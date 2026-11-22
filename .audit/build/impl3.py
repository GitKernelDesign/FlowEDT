# -*- coding: utf-8 -*-
"""Optimiseurs d'emploi du temps : construction gloutonne et recherche locale.

Le planning est traité semaine par semaine (A et B) pour respecter `weekType`.
Chaque "occurrence" (un cours répété `frequency` fois) porte un identifiant
`occId`, ce qui permet de la déplacer sans toucher aux autres cours partageant
le même créneau.
"""

FUNCS3 = {}

FUNCS3["optimizerCoursesForWeek"] = r"""
function optimizerCoursesForWeek(week) {
    return appData.courses.filter((course) => {
        const type = course.weekType || "Toutes";
        if (type === "Toutes" || type === "both") return true;
        return type === week;
    });
}
"""

FUNCS3["createEmptyWeekSchedule"] = r"""
function createEmptyWeekSchedule() {
    const schedule = {};
    DAYS.forEach((day) => {
        schedule[day] = {};
        TIME_SLOTS.forEach((slot) => {
            schedule[day][slot] = null;
        });
    });
    return schedule;
}
"""

FUNCS3["optimizerClassSize"] = r"""
function optimizerClassSize(course) {
    const cls =
        appData.classes.find((c) => c.id === course.classId) ||
        appData.halfGroups.find((h) => h.id === course.classId);
    return cls ? Number(cls.students) || 0 : 0;
}
"""

FUNCS3["optimizerPositions"] = r"""
function optimizerPositions(schedule, course, duration) {
    const positions = [];
    const fixedSlot = course.fixedStartSlot;
    const fixedIndex =
        fixedSlot === null ||
        fixedSlot === undefined ||
        fixedSlot === ""
            ? null
            : parseInt(fixedSlot, 10);
    DAYS.forEach((day) => {
        if (course.fixedDay && course.fixedDay !== day) return;
        for (
            let slotIndex = 0;
            slotIndex <= TIME_SLOTS.length - duration;
            slotIndex += 1
        ) {
            if (
                fixedIndex !== null &&
                !Number.isNaN(fixedIndex) &&
                fixedIndex !== slotIndex
            ) {
                continue;
            }
            let valid = true;
            for (let i = 0; i < duration; i += 1) {
                const slot = TIME_SLOTS[slotIndex + i];
                if (!slot || !canPlaceInSchedule(day, slot, course, schedule)) {
                    valid = false;
                    break;
                }
            }
            if (!valid) continue;
            if (!appData.rooms.length) {
                // Aucune salle déclarée : le cours est placé sans salle.
                positions.push({ day, slotIndex, roomId: null });
                continue;
            }
            const roomId = resolveRoomForPlacement(
                course,
                schedule,
                day,
                slotIndex,
                duration,
                course.roomId,
            );
            if (!roomId) continue;
            positions.push({ day, slotIndex, roomId });
        }
    });
    return positions;
}
"""

FUNCS3["optimizerPlace"] = r"""
function optimizerPlace(schedule, course, day, slotIndex, duration, occId) {
    let roomId = null;
    if (appData.rooms.length) {
        roomId = resolveRoomForPlacement(
            course,
            schedule,
            day,
            slotIndex,
            duration,
            course.roomId,
        );
        if (!roomId) return false;
    }
    for (let i = 0; i < duration; i += 1) {
        const slot = TIME_SLOTS[slotIndex + i];
        if (!slot) return false;
        const data = {
            courseId: course.id,
            roomId,
            duration,
            slotIndex: i,
            occId,
        };
        const cell = schedule[day][slot];
        if (cell === null || cell === undefined) {
            schedule[day][slot] = data;
        } else if (Array.isArray(cell)) {
            cell.push(data);
        } else {
            schedule[day][slot] = [cell, data];
        }
    }
    return true;
}
"""

FUNCS3["optimizerRemove"] = r"""
function optimizerRemove(schedule, occId) {
    DAYS.forEach((day) => {
        TIME_SLOTS.forEach((slot) => {
            const cell = schedule[day][slot];
            if (!cell) return;
            if (Array.isArray(cell)) {
                const kept = cell.filter((sd) => sd && sd.occId !== occId);
                if (kept.length === cell.length) return;
                if (kept.length === 0) schedule[day][slot] = null;
                else if (kept.length === 1) schedule[day][slot] = kept[0];
                else schedule[day][slot] = kept;
            } else if (cell.occId === occId) {
                schedule[day][slot] = null;
            }
        });
    });
}
"""

FUNCS3["optimizerOccurrences"] = r"""
function optimizerOccurrences(courses) {
    const occurrences = [];
    courses.forEach((course) => {
        // Un cours à créneau imposé ne peut être placé qu'une fois, comme le
        // fait déjà la génération automatique.
        const pinned = Boolean(
            course.fixedDay &&
                course.fixedStartSlot !== null &&
                course.fixedStartSlot !== undefined &&
                course.fixedStartSlot !== "",
        );
        const frequency = pinned
            ? 1
            : Math.max(1, parseInt(course.frequency, 10) || 1);
        for (let f = 0; f < frequency; f += 1) {
            occurrences.push({
                id: `${course.id}#${f}`,
                course,
                duration: parseInt(course.duration, 10) || SLOTS_PER_HOUR,
            });
        }
    });
    return occurrences;
}
"""

FUNCS3["evaluateSchedule"] = r"""
function evaluateSchedule(schedule, weights) {
    if (!schedule) return 0;
    const w = Object.assign(
        { teacher: 5, room: 3, class: 2, priority: 4 },
        weights || {},
    );
    const coursesById = new Map(appData.courses.map((c) => [c.id, c]));
    const roomsById = new Map(appData.rooms.map((r) => [r.id, r]));
    const seen = new Set();
    const teacherDays = new Map();
    const classDays = new Map();
    let score = 0;
    let placements = 0;

    const remember = (store, id, day, slotIndex) => {
        if (!id) return;
        if (!store.has(id)) store.set(id, new Map());
        const days = store.get(id);
        if (!days.has(day)) days.set(day, []);
        days.get(day).push(slotIndex);
    };

    DAYS.forEach((day) => {
        const daySchedule = schedule[day] || {};
        TIME_SLOTS.forEach((slot, slotIndex) => {
            const cell = daySchedule[slot];
            if (!cell) return;
            const list = Array.isArray(cell) ? cell : [cell];
            list.forEach((slotData) => {
                if (!slotData || !slotData.courseId) return;
                const key = slotData.occId || `${slotData.courseId}@${day}@${slotIndex}`;
                if (seen.has(key)) return;
                seen.add(key);
                const course = coursesById.get(slotData.courseId);
                if (!course) return;
                placements += 1;
                score += 10;
                score += w.priority * (Number(course.priority) || 1) * 2;
                (course.teacherIds || []).forEach((teacherId) => {
                    remember(teacherDays, teacherId, day, slotIndex);
                });
                remember(classDays, course.classId, day, slotIndex);
                if (course.roomId && slotData.roomId === course.roomId) {
                    score += w.room * 5;
                } else if (slotData.roomId) {
                    const room = roomsById.get(slotData.roomId);
                    const needed = optimizerClassSize(course);
                    if (room && needed && Number(room.capacity) >= needed) {
                        score += w.room;
                    }
                }
            });
        });
    });

    const gapPenalty = (store) => {
        let gaps = 0;
        store.forEach((days) => {
            days.forEach((indexes) => {
                const unique = [...new Set(indexes)].sort((a, b) => a - b);
                for (let i = 1; i < unique.length; i += 1) {
                    gaps += unique[i] - unique[i - 1] - 1;
                }
            });
        });
        return gaps;
    };

    score -= w.teacher * gapPenalty(teacherDays);
    score -= w.class * gapPenalty(classDays);
    return score + placements;
}
"""

FUNCS3["buildGreedyWeek"] = r"""
function buildGreedyWeek(courses, weights) {
    const schedule = createEmptyWeekSchedule();
    const occurrences = optimizerOccurrences(courses).sort(
        (a, b) =>
            (Number(b.course.priority) || 1) - (Number(a.course.priority) || 1) ||
            b.duration - a.duration ||
            (Number(b.course.frequency) || 1) - (Number(a.course.frequency) || 1),
    );
    occurrences.forEach((occurrence) => {
        const { course, duration } = occurrence;
        const positions = optimizerPositions(schedule, course, duration);
        let best = null;
        let bestScore = -Infinity;
        positions.forEach((position) => {
            if (!optimizerPlace(schedule, course, position.day, position.slotIndex, duration, occurrence.id)) {
                return;
            }
            const score = evaluateSchedule(schedule, weights);
            optimizerRemove(schedule, occurrence.id);
            if (score > bestScore) {
                bestScore = score;
                best = position;
            }
        });
        if (best) {
            optimizerPlace(schedule, course, best.day, best.slotIndex, duration, occurrence.id);
        }
    });
    return schedule;
}
"""

FUNCS3["improveWeek"] = r"""
function improveWeek(schedule, courses, weights, maxMoves, onPass) {
    const occurrences = optimizerOccurrences(courses);
    const placements = new Map();
    DAYS.forEach((day) => {
        TIME_SLOTS.forEach((slot) => {
            const cell = schedule[day][slot];
            if (!cell) return;
            (Array.isArray(cell) ? cell : [cell]).forEach((slotData) => {
                if (slotData && slotData.occId) {
                    // Reconstituer le *début* du cours, pas le créneau courant.
                    placements.set(slotData.occId, {
                        day,
                        slotIndex:
                            TIME_SLOTS.indexOf(slot) -
                            (parseInt(slotData.slotIndex, 10) || 0),
                    });
                }
            });
        });
    });

    let score = evaluateSchedule(schedule, weights);
    let iterations = 0;
    let improved = true;

    while (improved && iterations < maxMoves) {
        improved = false;
        const order = occurrences.slice();
        for (let i = order.length - 1; i > 0; i -= 1) {
            const j = Math.floor(Math.random() * (i + 1));
            [order[i], order[j]] = [order[j], order[i]];
        }
        for (const occurrence of order) {
            if (iterations >= maxMoves) break;
            iterations += 1;
            const previous = placements.get(occurrence.id);
            optimizerRemove(schedule, occurrence.id);
            const positions = optimizerPositions(
                schedule,
                occurrence.course,
                occurrence.duration,
            );
            let best = null;
            let bestScore = score;
            positions.forEach((position) => {
                if (!optimizerPlace(schedule, occurrence.course, position.day, position.slotIndex, occurrence.duration, occurrence.id)) {
                    return;
                }
                const candidate = evaluateSchedule(schedule, weights);
                optimizerRemove(schedule, occurrence.id);
                if (candidate > bestScore + 1e-9) {
                    bestScore = candidate;
                    best = position;
                }
            });
            if (best) {
                optimizerPlace(schedule, occurrence.course, best.day, best.slotIndex, occurrence.duration, occurrence.id);
                score = bestScore;
                placements.set(occurrence.id, {
                    day: best.day,
                    slotIndex: best.slotIndex,
                });
                improved = true;
            } else {
                // Aucun déplacement améliorant : on remet le cours à sa place,
                // ou à défaut sur un emplacement resté valide (la place
                // d'origine a pu être prise par un autre cours entre-temps).
                const fallback = previous
                    ? positions.find(
                          (position) =>
                              position.day === previous.day &&
                              position.slotIndex === previous.slotIndex,
                      )
                    : null;
                const target = fallback || positions[0];
                if (target) {
                    optimizerPlace(
                        schedule,
                        occurrence.course,
                        target.day,
                        target.slotIndex,
                        occurrence.duration,
                        occurrence.id,
                    );
                    placements.set(occurrence.id, {
                        day: target.day,
                        slotIndex: target.slotIndex,
                    });
                }
            }
        }
        if (onPass) onPass(iterations, score);
    }
    return { score, iterations };
}
"""

FUNCS3["buildTimetable"] = r"""
function buildTimetable(algo, maxIter, weights) {
    const budget = Math.min(4000, Math.max(40, parseInt(maxIter, 10) || 500));
    const weeks = ["A", "B"];
    const outcome = {
        scheduleA: null,
        scheduleB: null,
        score: 0,
        iterations: 0,
        placed: 0,
        total: 0,
        unplaced: [],
    };

    weeks.forEach((week) => {
        const courses = optimizerCoursesForWeek(week);
        const schedule = buildGreedyWeek(courses, weights);
        const occurrences = optimizerOccurrences(courses);
        outcome.total += occurrences.length;

        if (algo === "local") {
            const result = improveWeek(
                schedule,
                courses,
                weights,
                Math.max(20, Math.floor(budget / 2)),
            );
            outcome.iterations += result.iterations;
        }

        const placedIds = new Set();
        DAYS.forEach((day) => {
            TIME_SLOTS.forEach((slot) => {
                const cell = schedule[day][slot];
                if (!cell) return;
                (Array.isArray(cell) ? cell : [cell]).forEach((slotData) => {
                    if (slotData && slotData.occId) placedIds.add(slotData.occId);
                });
            });
        });
        outcome.placed += placedIds.size;
        occurrences.forEach((occurrence) => {
            if (placedIds.has(occurrence.id)) return;
            outcome.unplaced.push({
                week,
                name: occurrence.course.name,
                className: occurrence.course.classId,
            });
        });

        outcome.score += evaluateSchedule(schedule, weights);
        if (week === "A") outcome.scheduleA = schedule;
        else outcome.scheduleB = schedule;
    });

    return outcome;
}
"""

FUNCS3["generationDefaults"] = r"""
function generationDefaults() {
    return { teacher: 5, room: 3, class: 2, priority: 4 };
}
"""

FUNCS3["loadGenerationWeights"] = r"""
function loadGenerationWeights() {
    let stored = null;
    try {
        stored = JSON.parse(
            window.localStorage.getItem("flowEdtGenerationWeights") || "null",
        );
    } catch (error) {
        stored = null;
    }
    const weights = Object.assign(generationDefaults(), stored || {});
    ["teacher", "room", "class", "priority"].forEach((key) => {
        const input = document.getElementById("generation-weight-" + key);
        if (!input) return;
        input.value = String(weights[key]);
        const output = input.nextElementSibling;
        if (output && output.tagName === "OUTPUT") {
            output.value = String(weights[key]);
        }
    });
    return weights;
}
"""

FUNCS3["readGenerationWeights"] = r"""
function readGenerationWeights() {
    const weights = generationDefaults();
    ["teacher", "room", "class", "priority"].forEach((key) => {
        const input = document.getElementById("generation-weight-" + key);
        if (!input) return;
        const value = parseInt(input.value, 10);
        weights[key] = Number.isNaN(value) ? weights[key] : Math.max(0, Math.min(10, value));
    });
    return weights;
}
"""

FUNCS3["saveGenerationWeights"] = r"""
function saveGenerationWeights(weights) {
    try {
        window.localStorage.setItem(
            "flowEdtGenerationWeights",
            JSON.stringify(weights),
        );
    } catch (error) {
        // stockage indisponible : les réglages restent valables pour la session
    }
}
"""

FUNCS3["setGenerationBusy"] = r"""
function setGenerationBusy(busy) {
    const active = Boolean(busy);
    document.querySelectorAll("[data-generate]").forEach((button) => {
        button.disabled = active;
    });
    const status = document.getElementById("generation-status");
    if (status) status.hidden = !active;
    const runButton = document.getElementById("generation-run");
    if (runButton) runButton.disabled = active;
}
"""

FUNCS3["openGenerationSheet"] = r"""
function openGenerationSheet() {
    if (generationRunning) {
        showNotification("Une génération est déjà en cours", "info");
        return;
    }
    loadGenerationWeights();
    setGenerationBusy(false);
    openSheet("generation-modal");
}
"""

FUNCS3["startGeneration"] = r"""
function startGeneration() {
    if (generationRunning) {
        showNotification("Une génération est déjà en cours", "info");
        return;
    }
    const weights = readGenerationWeights();
    saveGenerationWeights(weights);
    generateBasicSchedule({ weights, deferred: true, closeSheet: true });
}
"""

FUNCS3["generateBasicSchedule"] = r"""
function generateBasicSchedule(options) {
    const settings = options || {};
    // Un seul calcul à la fois : les boutons sont désactivés et ce verrou
    // protège aussi les appels programmatiques.
    if (generationRunning) {
        showNotification("Une génération est déjà en cours", "info");
        return false;
    }
    if (!appData.courses.length) {
        showNotification("Ajoutez d'abord des cours", "error");
        return false;
    }

    const weights = Object.assign(
        generationDefaults(),
        settings.weights || readGenerationWeights(),
    );
    const maxIterations = settings.maxIterations || 5000;
    generationRunning = true;
    setGenerationBusy(true);

    const run = () => {
        try {
            const outcome = buildTimetable("local", maxIterations, weights);
            if (!outcome.placed) {
                showNotification(
                    "Aucun cours n'a pu être placé : vérifiez les salles, les plages interdites et les créneaux imposés.",
                    "error",
                );
                return false;
            }

            appData.scheduleA = outcome.scheduleA || createEmptyWeekSchedule();
            appData.scheduleB = outcome.scheduleB || createEmptyWeekSchedule();
            appData.schedule =
                currentWeekView === "B" ? appData.scheduleB : appData.scheduleA;
            updateScheduleDisplay();
            saveData();

            if (settings.closeSheet) closeSheet("generation-modal");

            const hours = calculateActualHoursFromSchedule();
            if (outcome.unplaced.length) {
                const names = outcome.unplaced
                    .slice(0, 3)
                    .map((item) => `${item.name} (${item.week})`)
                    .join(", ");
                const more =
                    outcome.unplaced.length > 3
                        ? ` et ${outcome.unplaced.length - 3} autre(s)`
                        : "";
                showNotification(
                    `Planning partiel · ${outcome.placed}/${outcome.total} cours placés. Non placés : ${names}${more}.`,
                    "warning",
                );
            } else {
                showNotification(
                    `Planning généré · ${outcome.placed}/${outcome.total} cours · ${hours} h`,
                );
            }
            return true;
        } catch (error) {
            console.error("Erreur de génération:", error);
            showNotification(
                "La génération a échoué, le planning précédent est conservé",
                "error",
            );
            return false;
        } finally {
            generationRunning = false;
            setGenerationBusy(false);
        }
    };

    if (settings.deferred) {
        // Laisse la feuille afficher son indicateur avant le calcul.
        window.setTimeout(run, 120);
        return true;
    }
    return run();
}
"""

