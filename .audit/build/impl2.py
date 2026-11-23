# -*- coding: utf-8 -*-
"""Seconde partie des implémentations JS (planning, notifications, sauvegarde)."""

FUNCS2 = {}

FUNCS2["renderScheduleTable"] = r"""
function renderScheduleTable(scheduleData, tbody, sourceSchedule) {
    if (!tbody) return;
    // l'aperçu d'un créneau ne survit pas au redessin de la grille
    hideSlotPeek();
    tbody.innerHTML = "";
    // `sourceSchedule` reste le planning complet : la carte d'un créneau doit
    // montrer tous les cours présents, même quand un filtre en masque une partie.
    const fullSchedule = sourceSchedule || scheduleData;

    TIME_SLOTS.forEach((slot) => {
        const row = document.createElement("tr");

        const timeCell = document.createElement("td");
        timeCell.className =
            "time-slot" + (isFullHourSlot(slot) ? " full-hour" : "");
        timeCell.innerHTML = `<span class="time-slot__label">${escapeHtml(slotStart(slot))}</span>`;
        row.appendChild(timeCell);

        DAYS.forEach((day) => {
            const cell = document.createElement("td");
            const slotData = scheduleData[day] && scheduleData[day][slot];
            const sourceSlotData =
                fullSchedule[day] && fullSchedule[day][slot];

            let cantineInfo = null;
            if (appData.cantineSlots) {
                cantineInfo = appData.cantineSlots.find(
                    (cs) => cs.day === day && cs.slot === slot,
                );
            }

            const forbiddenTeachers = [];
            if (appData.forbiddenSlots) {
                appData.forbiddenSlots.forEach((fs) => {
                    if (fs.day !== day || fs.slot !== slot) return;
                    (fs.teacherIds || []).forEach((teacherId) => {
                        const teacher = appData.teachers.find(
                            (t) => t.id === teacherId,
                        );
                        if (teacher) forbiddenTeachers.push(teacher.name);
                    });
                });
            }

            cell.dataset.day = day;
            cell.dataset.slot = slot;
            cell.tabIndex = 0;
            cell.setAttribute("role", "button");
            cell.className = "slot";

            let ariaLabel = `${day}, ${slot.replace("-", " – ")}`;

            if (slotData) {
                const list = Array.isArray(slotData) ? slotData : [slotData];
                const wrapper = document.createElement("div");
                wrapper.className = "slot__list";
                const names = [];
                const firstSlots = [];
                const continuations = [];
                // Tout ce que la cellule contient, y compris ce que la grille
                // ne peut pas montrer : l'aperçu au survol s'en sert.
                const peekEntries = [];

                list.forEach((item) => {
                    if (!item || !item.courseId) return;
                    const course = appData.courses.find(
                        (c) => c.id === item.courseId,
                    );
                    if (!course) return;

                    const isFirstSlot = !item.slotIndex;
                    const color = getCourseColor(course);
                    const teacherNames = (course.teacherIds || [])
                        .map((id) => {
                            const teacher = appData.teachers.find(
                                (t) => t.id === id,
                            );
                            return teacher ? teacher.name : "";
                        })
                        .filter(Boolean)
                        .join(", ");
                    const room = appData.rooms.find(
                        (r) => r.id === item.roomId,
                    );
                    const classInfo = getClassInfo(course.classId) || "";
                    const halfGroup = appData.halfGroups.find(
                        (hg) => hg.id === course.classId,
                    );

                    const classLabel = halfGroup
                        ? halfGroup.groupName || classInfo
                        : classInfo;
                    peekEntries.push({
                        courseId: course.id,
                        name: course.name,
                        tag: classLabel,
                        teacher: teacherNames,
                        room: room ? room.name : "",
                        color,
                        suite: !isFirstSlot,
                    });

                    if (isFirstSlot) {
                        names.push(course.name);
                        // Une seule ligne par cours : la grille garde des lignes
                        // de hauteur fixe, donc un créneau chargé ne déforme plus
                        // l'axe des heures. Le détail complet s'affiche dans
                        // l'aperçu au survol ; pour un créneau à un seul cours,
                        // l'infobulle native reste le raccourci le plus direct.
                        const element = document.createElement("div");
                        element._detail = [course.name, classLabel, teacherNames, room ? room.name : ""]
                            .filter(Boolean)
                            .join(" · ");
                        element.className = "slot-course";
                        element.style.setProperty("--course-color", color);
                        element.innerHTML = `
                            <span class="slot-course__name">${escapeHtml(course.name)}</span>
                            ${classLabel ? `<span class="slot-course__tag">${escapeHtml(classLabel)}</span>` : ""}`;
                        firstSlots.push(element);
                    } else {
                        const chip = document.createElement("span");
                        chip.className = "slot-cont";
                        chip.style.setProperty("--course-color", color);
                        chip.innerHTML = `<span class="slot-cont__dot" aria-hidden="true"></span><span class="slot-cont__name">${escapeHtml(course.name)}</span>`;
                        continuations.push(chip);
                    }
                });

                // Deux cours tiennent dans une ligne ; au-delà on en montre un
                // et on annonce le reste, pour ne jamais rogner le tableau.
                const MAX_VISIBLE = 2;
                const shown =
                    firstSlots.length > MAX_VISIBLE ? 1 : firstSlots.length;
                if (firstSlots.length === 1) {
                    firstSlots[0].title = firstSlots[0]._detail || "";
                }
                firstSlots.slice(0, shown).forEach((element, rank) => {
                    // le rang décale légèrement la carte : deux cours empilés
                    // se lisent comme deux cartes, pas comme une barre coupée
                    element.style.setProperty("--stack", String(rank));
                    element.dataset.peek = "1";
                    wrapper.appendChild(element);
                });
                if (firstSlots.length > MAX_VISIBLE) {
                    const more = document.createElement("span");
                    more.className = "slot-more";
                    more.textContent = `+${firstSlots.length - shown} autres`;
                    more.dataset.peek = "1";
                    wrapper.appendChild(more);
                }
                if (continuations.length) {
                    const stack = document.createElement("div");
                    stack.className = "slot-cont-list";
                    stack.appendChild(continuations[0]);
                    if (continuations.length > 1) {
                        const rest = document.createElement("span");
                        rest.className = "slot-cont__count";
                        rest.textContent = `+${continuations.length - 1}`;
                        stack.appendChild(rest);
                    }
                    wrapper.appendChild(stack);
                }

                cell.classList.add("slot--course");
                cell._peek = peekEntries;
                cell.appendChild(wrapper);
                ariaLabel += names.length
                    ? `, ${names.join(", ")}`
                    : ", cours";
                ariaLabel += ". Ouvrir le détail du créneau.";
            } else if (cantineInfo) {
                const className = cantineInfo.classId
                    ? getClassInfo(cantineInfo.classId)
                    : "Toutes les classes";
                cell.classList.add("slot--cantine");
                cell.innerHTML = `<div class="slot__list"><span class="slot-badge">${icon("i-utensils")}<span class="slot-badge__text">Cantine · ${escapeHtml(className)}</span></span></div>`;
                ariaLabel += `, cantine (${className})`;
            } else if (forbiddenTeachers.length) {
                cell.classList.add("slot--forbidden");
                cell.innerHTML = `<div class="slot__list"><span class="slot-badge">${icon("i-ban")}<span class="slot-badge__text">Indisponible · ${escapeHtml(forbiddenTeachers.join(", "))}</span></span></div>`;
                ariaLabel += `, plage interdite (${forbiddenTeachers.join(", ")})`;
            } else {
                cell.classList.add("slot--empty");
                cell.innerHTML = `<div class="slot__list"><span class="slot-plus">${icon("i-plus")}Ajouter</span></div>`;
                ariaLabel += ", créneau libre. Ajouter un cours.";
            }

            cell.setAttribute("aria-label", ariaLabel);
            cell.onclick = () =>
                cellClicked(day, slot, sourceSlotData, fullSchedule);
            cell.onkeydown = (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    cellClicked(day, slot, sourceSlotData, fullSchedule);
                }
            };

            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });

    updateHoursStat();
    updateConflictCount();
}
"""

FUNCS2["slotPeekState"] = r"""
function slotPeekState() {
    if (!window.__slotPeek) {
        window.__slotPeek = {
            cell: null,
            timer: 0,
            press: 0,
            suppressClick: false,
        };
    }
    return window.__slotPeek;
}
"""

FUNCS2["ensureSlotPeek"] = r"""
function ensureSlotPeek() {
    let peek = document.getElementById("slot-peek");
    if (peek) return peek;
    peek = document.createElement("div");
    peek.id = "slot-peek";
    peek.className = "slot-peek";
    peek.setAttribute("role", "tooltip");
    peek.setAttribute("aria-hidden", "true");
    peek.hidden = true;
    document.body.appendChild(peek);
    return peek;
}
"""

FUNCS2["slotPeekUseful"] = r"""
function slotPeekUseful(cell) {
    const entries = (cell && cell._peek) || [];
    if (!entries.length) return false;
    // Plusieurs cours, une suite, ou un intitulé rogné : la carte ne dit pas
    // tout, l'aperçu prend le relais.
    if (entries.length > 1) return true;
    if (cell.querySelector(".slot-cont-list")) return true;
    return [
        ...cell.querySelectorAll(
            ".slot-course__name, .slot-course__tag, .slot-cont__name",
        ),
    ].some((node) => node.scrollWidth > node.clientWidth + 1);
}
"""

FUNCS2["slotPeekMarkup"] = r"""
function slotPeekMarkup(cell) {
    const entries = (cell && cell._peek) || [];
    const shown = entries.slice(0, 6);
    const rest = entries.length - shown.length;
    const distinct = new Set(entries.map((entry) => entry.courseId)).size;
    const items = shown
        .map(
            (entry) => `
            <li class="slot-peek__item" style="--course-color:${entry.color}">
                <span class="slot-peek__dot" aria-hidden="true"></span>
                <span class="slot-peek__text">
                    <span class="slot-peek__name">${escapeHtml(entry.name)}${
                        entry.suite
                            ? '<span class="slot-peek__flag">suite</span>'
                            : ""
                    }</span>
                    <span class="slot-peek__meta">${escapeHtml(
                        [entry.tag, entry.teacher, entry.room]
                            .filter(Boolean)
                            .join(" · ") || "Sans professeur ni salle",
                    )}</span>
                </span>
            </li>`,
        )
        .join("");
    const slotLabel = (cell.dataset.slot || "").replace("-", " – ");
    return `
        <div class="slot-peek__head">
            <span class="slot-peek__title">${escapeHtml(cell.dataset.day || "")} · ${escapeHtml(slotLabel)}</span>
            <span class="slot-peek__count">${distinct} cours</span>
        </div>
        <ul class="slot-peek__list">${items}</ul>
        ${
            rest > 0
                ? `<p class="slot-peek__note">+${rest} autre${rest > 1 ? "s" : ""} cours dans ce créneau</p>`
                : ""
        }`;
}
"""

FUNCS2["slotPeekBounds"] = r"""
function slotPeekBounds() {
    // La zone utile exclut la barre d'en-tête collante et la navigation basse.
    const margin = 8;
    let top = margin;
    let bottom = window.innerHeight - margin;
    const bar = document.querySelector(".app-bar");
    if (bar) {
        const rect = bar.getBoundingClientRect();
        if (rect.height > 0 && rect.bottom > top) top = rect.bottom + 6;
    }
    const nav = document.querySelector(".bottom-nav");
    if (nav) {
        const rect = nav.getBoundingClientRect();
        if (rect.height > 0 && rect.top < bottom) bottom = rect.top - margin;
    }
    return {
        top,
        bottom: Math.max(top + 80, bottom),
        left: margin,
        right: window.innerWidth - margin,
    };
}
"""

FUNCS2["showSlotPeek"] = r"""
function showSlotPeek(cell, anchor) {
    if (!cell || !slotPeekUseful(cell)) return;
    if (document.querySelector(".sheet.active")) return;
    const state = slotPeekState();
    const peek = ensureSlotPeek();
    peek.innerHTML = slotPeekMarkup(cell);
    peek.hidden = false;
    peek.setAttribute("aria-hidden", "false");
    state.cell = cell;

    // Sous la cellule (ou sous le doigt au tactile), basculé au-dessus quand le
    // bas de l'écran est proche, et toujours dans la zone utile.
    const rect = cell.getBoundingClientRect();
    const box = peek.getBoundingClientRect();
    const bounds = slotPeekBounds();
    let left = rect.left;
    let top = rect.bottom + 6;
    if (anchor && Number.isFinite(anchor.x) && Number.isFinite(anchor.y)) {
        // Au doigt : au-dessus du point touché pour ne pas le masquer.
        left = anchor.x - box.width / 2;
        top = anchor.y - box.height - 14;
        if (top < bounds.top) top = anchor.y + 16;
    } else if (top + box.height > bounds.bottom) {
        top = rect.top - box.height - 6;
    }
    if (left + box.width > bounds.right) left = bounds.right - box.width;
    if (left < bounds.left) left = bounds.left;
    if (top + box.height > bounds.bottom) top = bounds.bottom - box.height;
    if (top < bounds.top) top = bounds.top;
    peek.style.left = `${Math.round(left)}px`;
    peek.style.top = `${Math.round(top)}px`;
}
"""

FUNCS2["hideSlotPeek"] = r"""
function hideSlotPeek() {
    const state = slotPeekState();
    clearTimeout(state.timer);
    state.timer = 0;
    state.cell = null;
    const peek = document.getElementById("slot-peek");
    if (!peek) return;
    peek.hidden = true;
    peek.setAttribute("aria-hidden", "true");
}
"""

FUNCS2["initSlotPeek"] = r"""
function initSlotPeek() {
    const state = slotPeekState();

    const arm = (cell, delay, anchor) => {
        clearTimeout(state.timer);
        if (!cell || !slotPeekUseful(cell)) {
            hideSlotPeek();
            return;
        }
        state.timer = setTimeout(() => showSlotPeek(cell, anchor), delay);
    };

    const cellOf = (event) =>
        event.target && event.target.closest
            ? event.target.closest("td.slot--course")
            : null;

    // Souris : survol franc, sans clignotement quand le pointeur reste dedans.
    document.addEventListener("pointerover", (event) => {
        if (event.pointerType && event.pointerType !== "mouse") return;
        const cell = cellOf(event);
        if (!cell) return;
        if (event.relatedTarget && cell.contains(event.relatedTarget)) return;
        arm(cell, 140);
    });

    document.addEventListener("pointerout", (event) => {
        const cell = cellOf(event);
        if (!cell) return;
        if (event.relatedTarget && cell.contains(event.relatedTarget)) return;
        if (state.press) return;
        clearTimeout(state.timer);
        state.timer = 0;
        if (state.cell === cell) hideSlotPeek();
    });

    // Clavier : le focus montre la même information.
    document.addEventListener("focusin", (event) => {
        const cell = cellOf(event);
        if (cell) arm(cell, 0);
    });

    document.addEventListener("focusout", (event) => {
        const cell = cellOf(event);
        if (cell && state.cell === cell) hideSlotPeek();
    });

    // Tactile : appui sur le compteur « +N », ou appui long sur le créneau.
    document.addEventListener("pointerdown", (event) => {
        if (event.pointerType !== "touch" && event.pointerType !== "pen") return;
        const cell = cellOf(event);
        if (!cell) return;
        const badge =
            event.target.closest &&
            event.target.closest(".slot-more, .slot-cont__count");
        if (badge) {
            state.suppressClick = true;
            arm(cell, 0, { x: event.clientX, y: event.clientY });
            window.setTimeout(() => {
                state.suppressClick = false;
            }, 800);
            return;
        }
        clearTimeout(state.press);
        const point = { x: event.clientX, y: event.clientY };
        state.press = window.setTimeout(() => {
            state.press = 0;
            state.suppressClick = true;
            arm(cell, 0, point);
            window.setTimeout(() => {
                state.suppressClick = false;
            }, 800);
        }, 450);
    });

    ["pointerup", "pointercancel"].forEach((type) => {
        document.addEventListener(
            type,
            () => {
                if (!state.press) return;
                clearTimeout(state.press);
                state.press = 0;
            },
            true,
        );
    });

    // Le clic déclenché par un appui long n'ouvre pas la fiche : on l'avale.
    document.addEventListener(
        "click",
        (event) => {
            if (state.suppressClick) {
                state.suppressClick = false;
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            if (state.cell) hideSlotPeek();
        },
        true,
    );

    window.addEventListener("scroll", hideSlotPeek, true);
    window.addEventListener("resize", hideSlotPeek);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") hideSlotPeek();
    });
}
"""

FUNCS2["repairScheduleSelection"] = r"""
function repairScheduleSelection() {
    // La ressource affichée peut disparaître (suppression, import) : on repasse
    // alors sur la première ressource de la même vue au lieu de laisser une
    // grille vide dont plus rien ne correspond.
    if (window.__repairingSelection) return false;
    const selection = currentSelectedItem || {};
    const type = selection.type;
    if (!type || type === "all") return false;
    const entries = scheduleTypeEntries(type);
    if (!entries.length) return false;
    if (selection.id && entries.some((entry) => entry.value === selection.id)) {
        return false;
    }
    window.__repairingSelection = true;
    updateScheduleTypeSelector();
    window.__repairingSelection = false;
    return true;
}
"""

FUNCS2["updateScheduleDisplay"] = r"""
function updateScheduleDisplay() {
    if (repairScheduleSelection()) return;
    const currentSchedule = getCurrentSchedule();

    const tbody = document.getElementById("schedule-body");
    if (tbody) {
        tbody.innerHTML = "";
        renderScheduleTable(
            filterScheduleBySelection(currentSchedule),
            tbody,
            currentSchedule,
        );
    }

    const tbodyA = document.getElementById("schedule-body-a");
    if (tbodyA) {
        tbodyA.innerHTML = "";
        renderScheduleTable(
            filterScheduleBySelection(appData.scheduleA),
            tbodyA,
            appData.scheduleA,
        );
    }

    const tbodyB = document.getElementById("schedule-body-b");
    if (tbodyB) {
        tbodyB.innerHTML = "";
        renderScheduleTable(
            filterScheduleBySelection(appData.scheduleB),
            tbodyB,
            appData.scheduleB,
        );
    }

    document.querySelectorAll(".timetable").forEach((table) => {
        table.dataset.dayFocus = String(currentDayIndex);
    });

    updateDayTabs();
    updateLegend();
    updateScheduleCallout();
    updateFilterChip();
}
"""

FUNCS2["getCurrentFilterFn"] = r"""
function getCurrentFilterFn() {
    const selection = currentSelectedItem || { type: "all", id: "" };
    const type = selection.type || "all";
    // Anciennes variables de filtre conservées pour compatibilité.
    const legacy = {
        teacher: currentFilterTeacher,
        class: currentFilterClass,
        room: currentFilterRoom,
    };
    const id = selection.id || legacy[type] || "";

    if (type === "all") return null;
    // Aucune ressource de ce type : la grille reste vide plutôt que de
    // retomber sur une vue globale qui n'existe plus.
    if (!id) return () => false;

    if (type === "teacher") {
        return (slotData, course) =>
            (course.teacherIds || []).includes(id);
    }

    if (type === "class") {
        return (slotData, course) =>
            isClassOrGroupMatching(course.classId, id);
    }

    if (type === "room") {
        return (slotData, course) =>
            (slotData.roomId || course.roomId) === id;
    }

    return null;
}
"""

FUNCS2["isClassOrGroupMatching"] = r"""
function isClassOrGroupMatching(classId, targetId) {
    if (!classId || !targetId) return false;
    if (classId === targetId) return true;

    // Chaque identifiant est ramené aux classes qu'il couvre : une classe,
    // les classes d'un groupe, ou la classe parente d'un demi-groupe. Filtrer
    // « 1 G1 » montre donc aussi ses demi-groupes, et filtrer « Terminales »
    // montre les cours de toutes ses classes.
    const classesOf = (id) => {
        const group = (appData.classGroups || []).find((cg) => cg.id === id);
        if (group) return group.classIds || [];
        const halfGroup = (appData.halfGroups || []).find((hg) => hg.id === id);
        if (halfGroup) return [halfGroup.classId];
        return [id];
    };

    const courseClasses = classesOf(classId);
    const targetClasses = classesOf(targetId);
    return courseClasses.some((id) => targetClasses.includes(id));
}
"""

FUNCS2["filterScheduleBySelection"] = r"""
function filterScheduleBySelection(schedule) {
    if (!schedule) return {};
    const filterFn = getCurrentFilterFn();
    if (!filterFn) return schedule;

    const filteredSchedule = {};
    DAYS.forEach((day) => {
        filteredSchedule[day] = {};
        TIME_SLOTS.forEach((slot) => {
            const slotData = schedule[day] && schedule[day][slot];
            if (!slotData) return;

            // On filtre à l'intérieur du créneau : un cours retenu ne doit pas
            // ramener avec lui les cours des autres professeurs.
            const matches = (Array.isArray(slotData) ? slotData : [slotData])
                .filter((placement) => {
                    if (!placement || !placement.courseId) return false;
                    const course = appData.courses.find(
                        (c) => c.id === placement.courseId,
                    );
                    return course ? filterFn(placement, course) : false;
                });

            if (!matches.length) return;
            filteredSchedule[day][slot] =
                matches.length === 1 ? matches[0] : matches;
        });
    });
    return filteredSchedule;
}
"""

FUNCS2["countVisibleCourses"] = r"""
function countVisibleCourses() {
    let count = 0;
    const schedules =
        currentWeekView === "both"
            ? [appData.scheduleA, appData.scheduleB]
            : [getCurrentSchedule()];

    schedules.forEach((schedule) => {
        const filtered = filterScheduleBySelection(schedule);
        DAYS.forEach((day) => {
            TIME_SLOTS.forEach((slot) => {
                const value = filtered[day] && filtered[day][slot];
                if (!value) return;
                (Array.isArray(value) ? value : [value]).forEach((placement) => {
                    if (placement && placement.courseId && !placement.slotIndex) {
                        count += 1;
                    }
                });
            });
        });
    });
    return count;
}
"""

FUNCS2["currentSelectionName"] = r"""
function currentSelectionName() {
    const selection = currentSelectedItem || {};
    if (selection.type === "teacher") {
        const teacher = appData.teachers.find((t) => t.id === selection.id);
        if (teacher) return teacher.name;
    }
    if (selection.type === "class") {
        const label = getClassInfo(selection.id);
        if (label) return label;
    }
    if (selection.type === "room") {
        const room = appData.rooms.find((r) => r.id === selection.id);
        if (room) return room.name;
    }
    const select = document.getElementById("schedule-item-selector");
    if (select && select.selectedOptions && select.selectedOptions[0]) {
        return select.selectedOptions[0].textContent.trim();
    }
    return "";
}
"""

FUNCS2["updateConflictCount"] = r"""
function updateConflictCount() {
    const filterFn = getCurrentFilterFn();
    const situations = new Set();
    const schedules =
        currentWeekView === "both"
            ? [appData.scheduleA, appData.scheduleB]
            : [getCurrentSchedule()];
    const inFilter = (slotData, course) =>
        !filterFn || filterFn(slotData, course);

    schedules.forEach((schedule, weekIndex) => {
        if (!schedule) return;
        DAYS.forEach((day) => {
            const daySchedule = schedule[day];
            if (!daySchedule) return;

            TIME_SLOTS.forEach((slot) => {
                const value = daySchedule[slot];
                if (!value) return;

                const placements = (Array.isArray(value) ? value : [value])
                    .map((slotData) => {
                        const course = appData.courses.find(
                            (c) => c.id === slotData.courseId,
                        );
                        return course ? { course, slotData } : null;
                    })
                    .filter(Boolean);

                for (let i = 0; i < placements.length; i += 1) {
                    for (let j = i + 1; j < placements.length; j += 1) {
                        const first = placements[i];
                        const second = placements[j];
                        const teacherClash = (first.course.teacherIds || []).some(
                            (id) => (second.course.teacherIds || []).includes(id),
                        );
                        const roomClash =
                            first.slotData.roomId &&
                            first.slotData.roomId === second.slotData.roomId;
                        const classClash = hasClassGroupConflict(
                            first.course.classId,
                            second.course.classId,
                        );
                        if (!(teacherClash || roomClash || classClash)) continue;
                        // Un filtre actif ne compte que les conflits qui
                        // touchent la ressource affichée.
                        if (
                            !inFilter(first.slotData, first.course) &&
                            !inFilter(second.slotData, second.course)
                        ) {
                            continue;
                        }
                        const ids = [first.course.id, second.course.id].sort();
                        situations.add(
                            `pair|${weekIndex}|${day}|${ids.join("|")}`,
                        );
                    }
                }

                placements.forEach(({ course, slotData }) => {
                    if (!inFilter(slotData, course)) return;
                    if (
                        (appData.forbiddenSlots || []).some(
                            (fs) =>
                                fs.day === day &&
                                fs.slot === slot &&
                                (fs.teacherIds || []).some((id) =>
                                    (course.teacherIds || []).includes(id),
                                ),
                        )
                    ) {
                        situations.add(
                            `forbidden|${weekIndex}|${day}|${slot}|${course.id}`,
                        );
                    }
                    if (
                        (appData.cantineSlots || []).some(
                            (cs) =>
                                cs.day === day &&
                                cs.slot === slot &&
                                (!cs.classId ||
                                    hasClassGroupConflict(
                                        cs.classId,
                                        course.classId,
                                    )),
                        )
                    ) {
                        situations.add(
                            `cantine|${weekIndex}|${day}|${slot}|${course.id}`,
                        );
                    }
                });
            });
        });
    });

    const conflicts = situations.size;
    const counter = document.getElementById("conflicts");
    if (counter) counter.textContent = conflicts;
    const card = document.getElementById("stat-conflicts");
    if (card) {
        card.classList.toggle("conflict", conflicts > 0);
        const label = card.querySelector(".label");
        if (label) label.textContent = conflicts > 1 ? "Conflits" : "Conflit";
    }
}
"""

FUNCS2["computeScheduleStats"] = r"""
function computeScheduleStats(schedules) {
    // Un cours peut être placé plusieurs fois dans la semaine (fréquence) :
    // chaque placement compte, seul le premier créneau d'une séquence porte
    // les heures. On identifie donc un placement par semaine + jour + créneau.
    const filterFn = getCurrentFilterFn();
    const seen = new Set();
    let hours = 0;
    let courses = 0;

    (schedules || []).forEach((schedule, weekIndex) => {
        if (!schedule) return;
        DAYS.forEach((day) => {
            if (!schedule[day]) return;
            TIME_SLOTS.forEach((slot) => {
                const value = schedule[day][slot];
                if (!value) return;
                (Array.isArray(value) ? value : [value]).forEach((slotData) => {
                    if (!slotData || !slotData.courseId) return;
                    if (slotData.slotIndex) return;
                    const course = appData.courses.find(
                        (c) => c.id === slotData.courseId,
                    );
                    if (!course) return;
                    if (filterFn && !filterFn(slotData, course)) return;

                    const key = `${weekIndex}|${day}|${slot}|${slotData.courseId}`;
                    if (seen.has(key)) return;
                    seen.add(key);
                    hours += slotsToDuration(course.duration || SLOTS_PER_HOUR);
                    courses += 1;
                });
            });
        });
    });

    return { hours, courses };
}
"""

FUNCS2["updateHoursStat"] = r"""
function updateHoursStat() {
    const hoursStat = document.getElementById("stat-hours");
    if (!hoursStat) return;

    const isRoomView =
        currentViewMode === "room" ||
        currentFilterRoom ||
        (currentSelectedItem && currentSelectedItem.type === "room");

    const schedules =
        currentWeekView === "both"
            ? [appData.scheduleA, appData.scheduleB]
            : [getCurrentSchedule()];
    const stats = computeScheduleStats(schedules);

    const totalCourses = document.getElementById("total-courses");
    if (totalCourses) totalCourses.textContent = stats.courses;
    const totalHours = document.getElementById("total-hours");
    if (totalHours) totalHours.textContent = stats.hours;

    // Vue par salle : les heures ne veulent plus dire grand-chose.
    if (isRoomView) {
        hoursStat.hidden = true;
        return;
    }

    hoursStat.hidden = false;
    const hoursLabel = hoursStat.querySelector(".label");
    if (hoursLabel) hoursLabel.textContent = "Heures effectuées";
    hoursStat.classList.remove("conflict");
}
"""

FUNCS2["showNotification"] = r"""
function showNotification(msg, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const iconId =
        type === "error"
            ? "i-alert"
            : type === "warning"
              ? "i-alert"
              : type === "info"
                ? "i-alert"
                : "i-check";

    const toast = document.createElement("div");
    toast.className = `toast toast--${type === "success" ? "success" : type}`;
    toast.innerHTML = `${icon(iconId)}<span class="toast__text"></span>`;
    toast.querySelector(".toast__text").textContent = String(msg);
    container.appendChild(toast);

    while (container.children.length > 3) {
        container.removeChild(container.firstElementChild);
    }

    window.setTimeout(() => {
        toast.classList.add("toast--out");
        window.setTimeout(() => toast.remove(), 240);
    }, 3600);
}
"""

FUNCS2["clearSchedule"] = r"""
function clearSchedule() {
    showConfirm(
        "Effacer le planning ?",
        "Les cours placés dans les semaines A et B seront retirés. Le catalogue des cours est conservé.",
        () => {
            initializeEmptySchedule();
            updateScheduleDisplay();
            saveData();
            showNotification("Planning effacé");
        },
        "Effacer le planning",
    );
}
"""

FUNCS2["confirmReset"] = r"""
function confirmReset() {
    showConfirm(
        "Réinitialiser toutes les données ?",
        "Les professeurs, salles, classes, cours et plannings enregistrés dans ce navigateur seront définitivement supprimés.",
        resetAllData,
        "Tout supprimer",
    );
}
"""

FUNCS2["deleteSavedSchedule"] = r"""
function deleteSavedSchedule(id) {
    showConfirm(
        "Supprimer cette sauvegarde ?",
        "L'emploi du temps enregistré dans ce navigateur sera supprimé. Cette action est irréversible.",
        async () => {
            try {
                await deleteScheduleFromDB(id);
                await updateSavedSchedulesList();
                showNotification("Sauvegarde supprimée");
            } catch (error) {
                console.error("Erreur:", error);
                showNotification("Suppression impossible", "error");
            }
        },
        "Supprimer",
    );
}
"""

FUNCS2["handleFileSelect"] = r"""
function handleFileSelect(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const nameLabel = document.getElementById("import-file-name");
    if (nameLabel) {
        nameLabel.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} Ko`;
    }

    const reader = new FileReader();
    reader.onload = function (loadEvent) {
        const text = loadEvent.target.result;
        const textarea = document.getElementById("export-textarea");
        if (textarea) textarea.value = text;
        try {
            JSON.parse(text);
            showNotification("Fichier prêt à importer");
        } catch (error) {
            showNotification("Ce fichier JSON est invalide", "error");
        }
    };
    reader.readAsText(file);
}
"""

FUNCS2["importData"] = r"""
function importData() {
    const data = document.getElementById("export-textarea").value.trim();
    if (!data) {
        showNotification("Sélectionnez un fichier ou collez des données", "error");
        return;
    }

    let imported;
    try {
        imported = JSON.parse(data);
    } catch (error) {
        showNotification("JSON invalide", "error");
        return;
    }

    if (!imported.teachers || !imported.rooms || !imported.classes) {
        showNotification("Format invalide : ressources manquantes", "error");
        return;
    }

    if (imported.courses) {
        imported.courses.forEach((course) => {
            if (course.teacherId && !course.teacherIds) {
                course.teacherIds = [course.teacherId];
                delete course.teacherId;
            }
        });
    }

    showConfirm(
        "Remplacer les données actuelles ?",
        "Les ressources, cours et plannings actuels seront remplacés par le contenu du fichier importé.",
        () => {
            appData = imported;
            if (
                !appData.schedule ||
                Object.keys(appData.schedule).length === 0
            ) {
                initializeEmptySchedule();
            }
            if (!Array.isArray(appData.openTeacherAccordions)) {
                appData.openTeacherAccordions = [];
            }
            updateAllUI();
            updateScheduleTypeSelector();
            saveData();
            showNotification("Données importées");
            document.getElementById("export-textarea").value = "";
            document.getElementById("import-file").value = "";
            const nameLabel = document.getElementById("import-file-name");
            if (nameLabel) nameLabel.textContent = "Aucun fichier sélectionné.";
        },
        "Importer",
    );
}
"""

FUNCS2["updateAllResourceLists"] = r"""
function updateAllResourceLists() {
    updateTeacherList();
    updateRoomList();
    updateClassList();
    updateHalfGroupList();
    updateClassGroupList();
    updateClassGroupSelector();
    updateCourseForm();
    updateResourceSummary();
    updateSelectedForbiddenTeachersDisplay();
    updateSelectedTeachersDisplay();
}
"""

FUNCS2["closeModal"] = r"""
function closeModal() {
    closeSheet("edit-modal");
    currentEditItem = null;
}
"""

FUNCS2["closeConfirmModal"] = r"""
function closeConfirmModal() {
    closeSheet("confirm-modal");
    confirmAction = null;
}
"""


FUNCS2["showCourseDetails"] = r"""
function showCourseDetails(day, slot, cd) {
    const courseDataList = Array.isArray(cd) ? cd : [cd];
    let html = "";

    courseDataList.forEach((slotData) => {
        const course = appData.courses.find((c) => c.id === slotData.courseId);
        if (!course) return;
        const teachers = (course.teacherIds || [])
            .map((id) => appData.teachers.find((t) => t.id === id))
            .filter(Boolean);
        const room = appData.rooms.find((r) => r.id === slotData.roomId);
        const classInfo = getClassInfo(course.classId) || "—";
        const color = getCourseColor(course);
        const partLabel = slotData.slotIndex
            ? ` · partie ${slotData.slotIndex + 1}`
            : "";

        html += `<article class="detail" style="--course-color:${color}">
            <header class="detail__head">
                <h4 class="detail__title">${escapeHtml(course.name)}</h4>
                <span class="badge">${escapeHtml(formatCourseDuration(course))}${escapeHtml(partLabel)}</span>
            </header>
            <dl class="detail__grid">
                <div><dt>${icon("i-users")}Professeurs</dt><dd>${teachers.length ? escapeHtml(teachers.map((t) => t.name).join(", ")) : "Aucun"}</dd></div>
                <div><dt>${icon("i-cap")}Classe</dt><dd>${escapeHtml(classInfo)}</dd></div>
                <div><dt>${icon("i-door")}Salle</dt><dd>${room ? escapeHtml(room.name) : "Aucune"}</dd></div>
                <div><dt>${icon("i-clock")}Créneau</dt><dd>${escapeHtml(day)} · ${escapeHtml(slot)}</dd></div>
            </dl>
        </article>`;
    });

    const body = document.getElementById("modal-body");
    if (body) {
        body.innerHTML =
            html ||
            `<p class="empty__text">Ce créneau ne contient plus de cours.</p>`;
        if (courseDataList.length > 1) {
            body.innerHTML += `<div class="sheet__actions">
                <button class="btn btn--danger btn--block" type="button" onclick="removeSpecificCourseFromSlot('${day}', '${slot}')">${icon("i-trash")}<span>Supprimer tous les cours du créneau</span></button>
            </div>`;
        }
    }

    document.getElementById("modal-title").textContent =
        courseDataList.length > 1 ? "Cours du créneau" : "Détails du cours";
    openSheet("edit-modal");
    const confirmButton = document.getElementById("modal-confirm");
    if (confirmButton) confirmButton.style.display = "none";
}
"""

FUNCS2["showCourseDetailsWithAddOption"] = r"""
function showCourseDetailsWithAddOption(day, slot, cd) {
    const courseDataList = Array.isArray(cd) ? cd : [cd];
    const firstCourseData = courseDataList[0];
    const course = appData.courses.find(
        (c) => c.id === firstCourseData.courseId,
    );

    if (!course) {
        showCourseDetails(day, slot, cd);
        return;
    }

    const teachers = (course.teacherIds || [])
        .map((id) => appData.teachers.find((t) => t.id === id))
        .filter(Boolean);
    const room = appData.rooms.find((r) => r.id === firstCourseData.roomId);
    const classInfo = getClassInfo(course.classId) || "—";
    const color = getCourseColor(course);

    const body = document.getElementById("modal-body");
    if (body) {
        body.innerHTML = `<article class="detail" style="--course-color:${color}">
            <header class="detail__head">
                <h4 class="detail__title">${escapeHtml(course.name)}</h4>
                <span class="badge">${escapeHtml(formatCourseDuration(course))}</span>
            </header>
            <dl class="detail__grid">
                <div><dt>${icon("i-users")}Professeurs</dt><dd>${teachers.length ? escapeHtml(teachers.map((t) => t.name).join(", ")) : "Aucun"}</dd></div>
                <div><dt>${icon("i-cap")}Classe</dt><dd>${escapeHtml(classInfo)}</dd></div>
                <div><dt>${icon("i-door")}Salle</dt><dd>${room ? escapeHtml(room.name) : "Aucune"}</dd></div>
                <div><dt>${icon("i-clock")}Créneau</dt><dd>${escapeHtml(day)} · ${escapeHtml(slot)}</dd></div>
            </dl>
        </article>
        <div class="sheet__actions">
            <button class="btn btn--primary btn--block" type="button" onclick="showAddCourseToSlot('${day}', '${slot}')">${icon("i-plus")}<span>Ajouter un autre cours</span></button>
        </div>`;
    }

    document.getElementById("modal-title").textContent = "Détails du cours";
    openSheet("edit-modal");
    const confirmButton = document.getElementById("modal-confirm");
    if (confirmButton) confirmButton.style.display = "none";
}
"""

FUNCS2["calculateActualHoursFromSchedule"] = r"""
function calculateActualHoursFromSchedule() {
    // Les heures attendues portent sur les deux semaines : on compte donc,
    // pour chaque cours, la semaine qui le concerne (A, B ou la mieux remplie
    // pour un cours commun aux deux). Sinon la comparaison était faussée par
    // les cours propres à la semaine B.
    let totalHours = 0;
    appData.courses.forEach((course) => {
        const duration = course.duration || SLOTS_PER_HOUR;
        const expectedSlots = duration * (course.frequency || 1);
        const weeks =
            course.weekType === "B"
                ? ["B"]
                : course.weekType === "A"
                  ? ["A"]
                  : ["A", "B"];
        let best = 0;
        weeks.forEach((week) => {
            const schedule =
                week === "A" ? appData.scheduleA : appData.scheduleB;
            let count = 0;
            DAYS.forEach((day) => {
                const daySchedule = schedule[day] || {};
                TIME_SLOTS.forEach((slot) => {
                    const value = daySchedule[slot];
                    if (!value) return;
                    const placements = Array.isArray(value) ? value : [value];
                    placements.forEach((slotData) => {
                        if (slotData && slotData.courseId === course.id) {
                            count += 1;
                        }
                    });
                });
            });
            if (count > best) best = count;
        });
        totalHours += slotsToDuration(Math.min(best, expectedSlots));
    });
    return totalHours;
}
"""

FUNCS2["createDefaultData"] = r"""
function createDefaultData() {
    // Aucune donnée n'est livrée avec l'application : l'établissement démarre
    // vide et se remplit au fil des saisies de l'utilisateur.
    appData = {
        teachers: [],
        rooms: [],
        classes: [],
        halfGroups: [],
        classGroups: [],
        courses: [],
        forbiddenSlots: [], // [{teacherIds: [], day, slot}]
        cantineSlots: [], // [{classId: null or id, day, slot}]
        lastSave: null,
        schemaVersion: 2,
    };
    initializeEmptySchedule();
}
"""

FUNCS2["hasAnyData"] = r"""
function hasAnyData() {
    // Une sauvegarde vide n'apporte rien : on évite d'écrire dans le stockage
    // tant que l'utilisateur n'a rien saisi.
    return Boolean(
        appData.teachers.length ||
            appData.rooms.length ||
            appData.classes.length ||
            appData.courses.length ||
            appData.halfGroups.length ||
            appData.classGroups.length ||
            (appData.forbiddenSlots || []).length ||
            (appData.cantineSlots || []).length,
    ) || countPlacedCourses() > 0;
}
"""

FUNCS2["autoSave"] = r"""
function autoSave() {
    if (generationRunning) return;
    if (!hasAnyData()) return;
    saveData();
}
"""

FUNCS2["isPristineLegacyDemo"] = r"""
function isPristineLegacyDemo(data) {
    // Les versions précédentes livraient un jeu de démonstration (ids t1…t15,
    // r1…r16, c1…c8). On ne l'efface que s'il n'a jamais été retouché : un
    // utilisateur qui a saisi ses propres ressources conserve ses données.
    if (!data) return false;

    const hasIds = (list, prefix, count) =>
        Array.isArray(list) &&
        list.length === count &&
        list.every((item, index) => item && item.id === prefix + (index + 1));

    const isEmptySchedule = (schedule) =>
        !schedule ||
        Object.keys(schedule).length === 0 ||
        Object.values(schedule).every((day) =>
            Object.values(day || {}).every((cell) => !cell),
        );

    return (
        hasIds(data.teachers, "t", 15) &&
        hasIds(data.rooms, "r", 16) &&
        hasIds(data.classes, "c", 8) &&
        (data.courses || []).length === 0 &&
        (data.forbiddenSlots || []).length === 0 &&
        (data.cantineSlots || []).length === 0 &&
        isEmptySchedule(data.scheduleA) &&
        isEmptySchedule(data.scheduleB)
    );
}
"""

FUNCS2["isRoomFreeForCourse"] = r"""
function isRoomFreeForCourse(
    roomId,
    day,
    startSlotIndex,
    duration,
    schedule,
) {
    // Une salle est libre sur une durée si aucun cours ne l'occupe, sur le
    // jour cible, pour chacun des créneaux couverts. Les créneaux peuvent
    // contenir plusieurs cours (tableau) : on les inspecte tous.
    if (!roomId) return true;
    const sched = schedule || appData.schedule;
    const daySchedule = sched && sched[day];
    if (!daySchedule) return true;
    for (let i = 0; i < duration; i += 1) {
        const slot = TIME_SLOTS[startSlotIndex + i];
        if (!slot) return false;
        const content = daySchedule[slot];
        if (!content) continue;
        const placements = Array.isArray(content) ? content : [content];
        if (
            placements.some(
                (placement) => placement && placement.roomId === roomId,
            )
        ) {
            return false;
        }
    }
    return true;
}
"""

FUNCS2["resolveRoomForPlacement"] = r"""
function resolveRoomForPlacement(
    course,
    schedule,
    day,
    startSlotIndex,
    duration,
    preferredRoomId,
) {
    const span = duration || (course && course.duration) || SLOTS_PER_HOUR;
    const sched = schedule || appData.schedule;
    const cls =
        appData.classes.find((c) => c.id === course.classId) ||
        appData.halfGroups.find((h) => h.id === course.classId);
    const needed = cls ? cls.students : 0;

    // Une salle ne peut pas accueillir deux classes en même temps : la salle
    // souhaitée (celle du cours, sinon celle héritée du planning parent) n'est
    // retenue que si elle est libre sur toute la durée. Sinon on cherche une
    // autre salle adaptée, au lieu de superposer deux cours.
    const candidates = [];
    [course && course.roomId, preferredRoomId].forEach((roomId) => {
        if (roomId && !candidates.includes(roomId)) candidates.push(roomId);
    });
    for (const roomId of candidates) {
        const room = appData.rooms.find((r) => r.id === roomId);
        if (!room) continue;
        // Une salle choisie explicitement pour le cours est respectée même si
        // sa capacité est inférieure à l'effectif : c'est un choix de
        // l'utilisateur. La capacité ne filtre que les salles automatiques.
        const explicit = Boolean(course && course.roomId === roomId);
        if (!explicit && room.capacity < needed) continue;
        if (isRoomFreeForCourse(roomId, day, startSlotIndex, span, sched)) {
            return roomId;
        }
    }
    return findSuitableRoomForDuration(course, sched, day, startSlotIndex, span);
}
"""

FUNCS2["findSuitableRoomForDuration"] = r"""
function findSuitableRoomForDuration(
    course,
    schedule,
    day,
    startSlotIndex,
    duration,
) {
    const span = duration || (course && course.duration) || SLOTS_PER_HOUR;
    const sched = schedule || appData.schedule;
    const cls =
        appData.classes.find((c) => c.id === course.classId) ||
        appData.halfGroups.find((h) => h.id === course.classId);
    const needed = cls ? cls.students : 0;

    // Essayer la salle préférée du cours d'abord
    if (course.roomId) {
        const r = appData.rooms.find((x) => x.id === course.roomId);
        if (
            r &&
            r.capacity >= needed &&
            isRoomFreeForCourse(r.id, day, startSlotIndex, span, sched)
        ) {
            return r.id;
        }
    }

    // Sinon la plus petite salle libre qui accueille l'effectif : les grandes
    // salles (gymnase, amphithéâtre) restent disponibles pour les cours qui en
    // ont besoin.
    const suitable = appData.rooms
        .filter(
            (r) =>
                r.capacity >= needed &&
                isRoomFreeForCourse(r.id, day, startSlotIndex, span, sched),
        )
        .sort((a, b) => a.capacity - b.capacity);
    return suitable.length ? suitable[0].id : null;
}
"""

ONLOAD = r"""
window.onload = function () {
    loadData();
    updateAllUI();
    updateStorageInfo();
    updateScheduleTypeSelector();
    initApp();
    setInterval(autoSave, 30000);
};
"""
