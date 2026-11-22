# -*- coding: utf-8 -*-
"""Nouvelles implémentations JS injectées dans index.html."""

HELPERS = r"""
// ==================== UTILITAIRES UI ====================
const escapeHtml = (value) =>
    String(value == null ? "" : value).replace(
        /[&<>"']/g,
        (c) =>
            ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;",
            })[c],
    );

const initialsOf = (name) =>
    String(name || "?")
        .trim()
        .split(/[\s\-_]+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0])
        .join("")
        .toUpperCase() || "?";

const icon = (id) =>
    `<svg class="icon" aria-hidden="true"><use href="#${id}"/></svg>`;

const emptyStateHtml = (iconId, title, text) => `
    <div class="empty">
        ${icon(iconId)}
        <span class="empty__title">${escapeHtml(title)}</span>
        <span class="empty__text">${escapeHtml(text)}</span>
    </div>`;

function setCount(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function plural(n, singular, pluralForm) {
    return `${n} ${n > 1 ? pluralForm : singular}`;
}

let currentDayIndex = 0;
let lastFocusedElement = null;
"""

FUNCS = {}

# ---------------------------------------------------------------- shell / thème
FUNCS["updateStorageInfo"] = r"""
function updateStorageInfo() {
    const pill = document.getElementById("save-indicator");
    const now = new Date();
    const time = now.toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
    });
    // Rien n'est enregistré tant que l'utilisateur n'a pas de données : la
    // pastille ne doit pas annoncer une sauvegarde qui n'existe pas.
    let stored = null;
    try {
        stored = localStorage.getItem("emploiDuTemps");
    } catch (error) {
        stored = null;
    }
    const hasStoredData = Boolean(stored && stored !== "null");
    const label = hasStoredData ? `Enregistré · ${time}` : "Aucune donnée";
    if (pill) {
        const text = pill.querySelector(".save-pill__text");
        if (text) text.textContent = label;
        const hint = hasStoredData
            ? `Sauvegarde locale à ${time}`
            : "Rien n'est encore enregistré dans ce navigateur";
        pill.title = hint;
        pill.setAttribute("aria-label", hint);
        pill.classList.remove("is-saving");
        pill.classList.toggle("is-idle", !hasStoredData);
    }
    // le menu burger reprend l'état de sauvegarde hors de l'en-tête
    const menuText = document.getElementById("menu-save-text");
    if (menuText) menuText.textContent = label;
}
"""

FUNCS["applyTheme"] = r"""
function applyTheme(theme) {
    const next = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    try {
        localStorage.setItem("flowEdtTheme", next);
    } catch (error) {
        /* stockage indisponible */
    }
    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
        const label =
            next === "dark"
                ? "Passer au thème clair"
                : "Passer au thème sombre";
        toggle.setAttribute("aria-label", label);
        toggle.title = label;
    }
    const switchRow = document.getElementById("theme-switch");
    if (switchRow) {
        switchRow.setAttribute(
            "aria-checked",
            next === "dark" ? "true" : "false",
        );
    }
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", next === "dark" ? "#0c1215" : "#f5f7fa");
}

function toggleTheme() {
    applyTheme(
        document.documentElement.dataset.theme === "dark" ? "light" : "dark",
    );
}

function initTheme() {
    let theme = document.documentElement.dataset.theme;
    if (!theme) {
        try {
            theme = localStorage.getItem("flowEdtTheme");
        } catch (error) {
            theme = null;
        }
    }
    applyTheme(theme === "dark" ? "dark" : "light");
}

function applyDensity(density) {
    const compact = density === "compact";
    document.documentElement.dataset.density = compact ? "compact" : "confort";
    try {
        localStorage.setItem("flowEdtDensity", compact ? "compact" : "confort");
    } catch (error) {
        /* stockage indisponible */
    }
    const label = compact
        ? "Revenir à l'affichage confort"
        : "Affichage compact des tableaux";
    const button = document.getElementById("density-toggle");
    if (button) {
        button.setAttribute("aria-pressed", compact ? "true" : "false");
        button.setAttribute("aria-label", label);
        button.title = label;
    }
    const switchRow = document.getElementById("density-switch");
    if (switchRow) {
        switchRow.setAttribute("aria-checked", compact ? "true" : "false");
    }
}

function toggleDensity() {
    applyDensity(
        document.documentElement.dataset.density === "compact"
            ? "confort"
            : "compact",
    );
}

function initDensity() {
    let density = document.documentElement.dataset.density;
    if (!density) {
        try {
            density = localStorage.getItem("flowEdtDensity");
        } catch (error) {
            density = null;
        }
    }
    applyDensity(density === "compact" ? "compact" : "confort");
}
"""

FUNCS["switchTab"] = r"""
function switchTab(tabName) {
    const panel = document.getElementById(tabName);
    if (!panel) return;

    // expose l'onglet courant au CSS (réglages propres au planning)
    document.documentElement.dataset.tab = tabName;

    saveData();

    document
        .querySelectorAll(".tab-content")
        .forEach((section) =>
            section.classList.toggle("active", section.id === tabName),
        );

    document.querySelectorAll("[data-tab]").forEach((item) => {
        const isActive = item.dataset.tab === tabName;
        item.classList.toggle("is-active", isActive);
        item.classList.toggle("active", isActive);
        if (isActive) item.setAttribute("aria-current", "page");
        else item.removeAttribute("aria-current");
    });

    closeAllPickers();

    if (tabName === "schedule") {
        updateScheduleDisplay();
    } else if (tabName === "courses") {
        updateCourseForm();
        updateCourseList();
    } else if (tabName === "teachers") {
        renderTeacherStudio();
    } else if (tabName === "resources") {
        updateAllResourceLists();
    } else if (tabName === "export") {
        updateSavedSchedulesList();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}
"""

# ---------------------------------------------------------------- sélecteurs
PICKER_HELPERS = r"""
function setPickerOpen(controlId, panelId, open) {
    const control = document.getElementById(controlId);
    const panel = document.getElementById(panelId);
    if (!control || !panel) return;

    document.querySelectorAll(".picker__panel").forEach((other) => {
        if (other !== panel) other.hidden = true;
    });
    document.querySelectorAll(".picker").forEach((other) => {
        if (other !== control) other.setAttribute("aria-expanded", "false");
    });

    panel.hidden = !open;
    control.setAttribute("aria-expanded", open ? "true" : "false");
    panel.classList.remove("picker__panel--up");
    panel.style.maxHeight = "";
    panel.style.bottom = "";

    if (!open) return;

    // Le panneau est ancré au champ (voir .field--picker). On choisit le sens
    // d'ouverture et on borne la hauteur à l'espace réellement disponible,
    // pour qu'il reste toujours entièrement visible, même sur petit mobile.
    const gap = 12;
    const bar = document.querySelector(".app-bar");
    const barBottom = bar ? bar.getBoundingClientRect().bottom : 0;
    const topSafe = barBottom > 0 ? barBottom + 8 : gap;
    // La barre d'onglets du bas est fixe elle aussi.
    const nav = document.querySelector(".bottom-nav");
    const navRect = nav ? nav.getBoundingClientRect() : null;
    const bottomSafe =
        navRect && navRect.height > 0 && navRect.top < window.innerHeight
            ? navRect.top - 8
            : window.innerHeight - gap;

    let rect = control.getBoundingClientRect();
    if (rect.top < topSafe || rect.bottom > window.innerHeight - 8) {
        // "instant" court-circuite le scroll-behavior: smooth du document,
        // sinon la mesure ci-dessous serait prise pendant l'animation.
        control.scrollIntoView({ block: "center", behavior: "instant" });
        rect = control.getBoundingClientRect();
    }

    const wanted = Math.min(panel.scrollHeight, 360);
    const below = bottomSafe - rect.bottom - gap;
    const above = rect.top - topSafe - 6;
    const goUp = below < Math.min(wanted, 220) && above > below;

    panel.classList.toggle("picker__panel--up", goUp);

    // Vers le haut, on recolle le panneau au contrôle : l'ancrage CSS se fait
    // sur le champ, dont la hauteur inclut le libellé.
    const fieldRect = panel.parentElement.getBoundingClientRect();
    panel.style.bottom = goUp
        ? `${Math.round(fieldRect.bottom - rect.top + 6)}px`
        : "";
    panel.style.maxHeight = `${Math.max(160, Math.min(wanted, goUp ? above : below))}px`;
}

function closeAllPickers() {
    document.querySelectorAll(".picker__panel").forEach((panel) => {
        panel.hidden = true;
    });
    document.querySelectorAll(".picker").forEach((control) => {
        control.setAttribute("aria-expanded", "false");
    });
}
"""

FUNCS["toggleTeacherDropdown"] = r"""
function toggleTeacherDropdown() {
    const panel = document.getElementById("teacher-dropdown");
    const willOpen = !panel || panel.hidden;
    if (willOpen) updateTeacherCheckboxes();
    setPickerOpen("teacher-multi-select", "teacher-dropdown", willOpen);
}
"""

FUNCS["closeTeacherDropdown"] = r"""
function closeTeacherDropdown() {
    setPickerOpen("teacher-multi-select", "teacher-dropdown", false);
}
"""

FUNCS["toggleClassDropdown"] = r"""
function toggleClassDropdown() {
    const panel = document.getElementById("class-dropdown");
    const willOpen = !panel || panel.hidden;
    if (willOpen) updateClassCheckboxes();
    setPickerOpen("class-multi-select", "class-dropdown", willOpen);
}
"""

FUNCS["closeClassDropdown"] = r"""
function closeClassDropdown() {
    setPickerOpen("class-multi-select", "class-dropdown", false);
}
"""

FUNCS["toggleForbiddenTeacherDropdown"] = r"""
function toggleForbiddenTeacherDropdown() {
    const panel = document.getElementById("forbidden-teacher-dropdown");
    const willOpen = !panel || panel.hidden;
    if (willOpen) updateForbiddenTeacherCheckboxes();
    setPickerOpen(
        "forbidden-teacher-multi-select",
        "forbidden-teacher-dropdown",
        willOpen,
    );
}
"""

FUNCS["closeForbiddenTeacherDropdown"] = r"""
function closeForbiddenTeacherDropdown() {
    setPickerOpen(
        "forbidden-teacher-multi-select",
        "forbidden-teacher-dropdown",
        false,
    );
}
"""

# ---------------------------------------------------------------- listes
FUNCS["updateResourceSummary"] = r"""
function updateResourceSummary() {
    const aside = document.getElementById("resource-summary");
    if (!aside) return;
    const parts = [
        plural(appData.teachers.length, "professeur", "professeurs"),
        plural(appData.rooms.length, "salle", "salles"),
        plural(appData.classes.length, "classe", "classes"),
    ];
    aside.innerHTML = parts
        .map((part) => `<span class="badge">${escapeHtml(part)}</span>`)
        .join("");
}
"""

FUNCS["updateTeacherList"] = r"""
function updateTeacherList() {
    const list = document.getElementById("teacher-list");
    if (list) {
        list.innerHTML = appData.teachers.length
            ? ""
            : emptyStateHtml(
                  "i-users",
                  "Aucun professeur",
                  "Ajoutez un enseignant pour pouvoir lui confier des cours.",
              );
        appData.teachers.forEach((teacher) => {
            const item = document.createElement("div");
            item.className = "res-item";
            item.innerHTML = `
                <span class="res-item__avatar" aria-hidden="true">${escapeHtml(initialsOf(teacher.name))}</span>
                <span class="res-item__text">
                    <span class="res-item__name">${escapeHtml(teacher.name)}</span>
                </span>
                <span class="res-item__actions">
                    <button class="icon-btn icon-btn--sm" type="button" onclick="editTeacher('${teacher.id}')" aria-label="Modifier ${escapeHtml(teacher.name)}" title="Modifier">${icon("i-pencil")}</button>
                    <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteTeacher('${teacher.id}')" aria-label="Supprimer ${escapeHtml(teacher.name)}" title="Supprimer">${icon("i-trash")}</button>
                </span>`;
            list.appendChild(item);
        });
        setCount("teacher-count", appData.teachers.length);
    }
    updateTeacherCheckboxes();
    updateResourceSummary();
}
"""

FUNCS["updateRoomList"] = r"""
function updateRoomList() {
    const list = document.getElementById("room-list");
    if (!list) return;
    list.innerHTML = appData.rooms.length
        ? ""
        : emptyStateHtml(
              "i-door",
              "Aucune salle",
              "Ajoutez les salles disponibles avec leur capacité.",
          );
    appData.rooms.forEach((room) => {
        const item = document.createElement("div");
        item.className = "res-item";
        item.innerHTML = `
            <span class="res-item__avatar" aria-hidden="true">${escapeHtml(initialsOf(room.name))}</span>
            <span class="res-item__text">
                <span class="res-item__name">${escapeHtml(room.name)}</span>
                <span class="res-item__meta">${plural(room.capacity || 0, "place", "places")}</span>
            </span>
            <span class="res-item__actions">
                <button class="icon-btn icon-btn--sm" type="button" onclick="editRoom('${room.id}')" aria-label="Modifier ${escapeHtml(room.name)}" title="Modifier">${icon("i-pencil")}</button>
                <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteRoom('${room.id}')" aria-label="Supprimer ${escapeHtml(room.name)}" title="Supprimer">${icon("i-trash")}</button>
            </span>`;
        list.appendChild(item);
    });
    setCount("room-count", appData.rooms.length);
    updateResourceSummary();
}
"""

FUNCS["updateClassList"] = r"""
function updateClassList() {
    const list = document.getElementById("class-list");
    if (list) {
        list.innerHTML = appData.classes.length
            ? ""
            : emptyStateHtml(
                  "i-cap",
                  "Aucune classe",
                  "Ajoutez les classes de l'établissement et leur effectif.",
              );
        appData.classes.forEach((cls) => {
            const item = document.createElement("div");
            item.className = "res-item";
            item.innerHTML = `
                <span class="res-item__avatar" aria-hidden="true">${escapeHtml(initialsOf(cls.name))}</span>
                <span class="res-item__text">
                    <span class="res-item__name">${escapeHtml(cls.name)}</span>
                    <span class="res-item__meta">${plural(cls.students || 0, "élève", "élèves")}</span>
                </span>
                <span class="res-item__actions">
                    <button class="icon-btn icon-btn--sm" type="button" onclick="editClass('${cls.id}')" aria-label="Modifier ${escapeHtml(cls.name)}" title="Modifier">${icon("i-pencil")}</button>
                    <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteClass('${cls.id}')" aria-label="Supprimer ${escapeHtml(cls.name)}" title="Supprimer">${icon("i-trash")}</button>
                </span>`;
            list.appendChild(item);
        });
        setCount("class-count", appData.classes.length);

        const select = document.getElementById("class-for-half-group");
        if (select) {
            const currentValue = select.value;
            select.innerHTML =
                '<option value="">Choisir une classe</option>';
            appData.classes.forEach((cls) => {
                const option = document.createElement("option");
                option.value = cls.id;
                option.textContent = cls.name;
                select.appendChild(option);
            });
            if (appData.classes.some((cls) => cls.id === currentValue)) {
                select.value = currentValue;
            }
        }
    }
    updateClassGroupSelector();
    updateResourceSummary();
}
"""

FUNCS["updateHalfGroupList"] = r"""
function updateHalfGroupList() {
    const list = document.getElementById("half-group-list");
    if (!list) return;
    list.innerHTML = appData.halfGroups.length
        ? ""
        : emptyStateHtml(
              "i-half",
              "Aucun demi-groupe",
              "Scindez une classe pour planifier deux groupes en parallèle.",
          );
    appData.halfGroups.forEach((hg) => {
        const classObj = appData.classes.find((c) => c.id === hg.classId);
        const item = document.createElement("div");
        item.className = "res-item";
        item.innerHTML = `
            <span class="res-item__avatar" aria-hidden="true">${escapeHtml(initialsOf(hg.name))}</span>
            <span class="res-item__text">
                <span class="res-item__name">${escapeHtml(hg.name)}</span>
                <span class="res-item__meta">${escapeHtml(classObj ? classObj.name : "Classe inconnue")}</span>
            </span>
            <span class="res-item__actions">
                <button class="icon-btn icon-btn--sm" type="button" onclick="editHalfGroup('${hg.id}')" aria-label="Modifier ${escapeHtml(hg.name)}" title="Modifier">${icon("i-pencil")}</button>
                <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteHalfGroup('${hg.id}')" aria-label="Supprimer ${escapeHtml(hg.name)}" title="Supprimer">${icon("i-trash")}</button>
            </span>`;
        list.appendChild(item);
    });
    setCount("half-group-count", appData.halfGroups.length);
}
"""

FUNCS["updateClassGroupList"] = r"""
function updateClassGroupList() {
    const list = document.getElementById("class-group-list");
    if (!list) return;
    list.innerHTML = appData.classGroups.length
        ? ""
        : emptyStateHtml(
              "i-layers",
              "Aucun groupe de classes",
              "Fusionnez des classes pour leur donner des cours communs.",
          );
    appData.classGroups.forEach((cg) => {
        const classNames = (cg.classIds || [])
            .map((cid) => {
                const cls = appData.classes.find((c) => c.id === cid);
                return cls ? cls.name : cid;
            })
            .join(", ");
        const item = document.createElement("div");
        item.className = "res-item";
        item.innerHTML = `
            <span class="res-item__avatar" aria-hidden="true">${escapeHtml(initialsOf(cg.name))}</span>
            <span class="res-item__text">
                <span class="res-item__name">${escapeHtml(cg.name)}</span>
                <span class="res-item__meta">${escapeHtml(classNames || "Aucune classe")}</span>
            </span>
            <span class="res-item__actions">
                <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteClassGroup('${cg.id}')" aria-label="Supprimer ${escapeHtml(cg.name)}" title="Supprimer">${icon("i-trash")}</button>
            </span>`;
        list.appendChild(item);
    });
    setCount("class-group-count", appData.classGroups.length);
}
"""

FUNCS["updateForbiddenSlotsList"] = r"""
function updateForbiddenSlotsList() {
    const list = document.getElementById("forbidden-slots-list");
    if (!list) return;
    const slots = appData.forbiddenSlots || [];
    list.innerHTML = slots.length
        ? ""
        : emptyStateHtml(
              "i-ban",
              "Aucune plage interdite",
              "Indiquez les créneaux où un professeur n'est jamais disponible.",
          );
    slots.forEach((fs, index) => {
        const teacherNames = (fs.teacherIds || [])
            .map((tid) => {
                const teacher = appData.teachers.find((t) => t.id === tid);
                return teacher ? teacher.name : tid;
            })
            .join(", ");
        const item = document.createElement("div");
        item.className = "res-item";
        item.innerHTML = `
            <span class="res-item__avatar" aria-hidden="true">${icon("i-clock")}</span>
            <span class="res-item__text">
                <span class="res-item__name">${escapeHtml(fs.day)} · ${escapeHtml(fs.slot)}</span>
                <span class="res-item__meta">${escapeHtml(teacherNames || "Professeurs supprimés")}</span>
            </span>
            <span class="res-item__actions">
                <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteForbiddenSlot(${index})" aria-label="Supprimer cette plage" title="Supprimer">${icon("i-trash")}</button>
            </span>`;
        list.appendChild(item);
    });
    setCount("forbidden-count", slots.length);
}
"""

FUNCS["updateCantineSlotsList"] = r"""
function updateCantineSlotsList() {
    const list = document.getElementById("cantine-slots-list");
    if (!list) return;
    const slots = appData.cantineSlots || [];
    list.innerHTML = slots.length
        ? ""
        : emptyStateHtml(
              "i-utensils",
              "Aucun service de cantine",
              "Réservez les créneaux de repas pour éviter d'y placer des cours.",
          );
    slots.forEach((cs, index) => {
        const className = cs.classId
            ? getClassInfo(cs.classId)
            : "Toutes les classes";
        const item = document.createElement("div");
        item.className = "res-item";
        item.innerHTML = `
            <span class="res-item__avatar" aria-hidden="true">${icon("i-utensils")}</span>
            <span class="res-item__text">
                <span class="res-item__name">${escapeHtml(cs.day)} · ${escapeHtml(cs.slot)}</span>
                <span class="res-item__meta">${escapeHtml(className || "Toutes les classes")}</span>
            </span>
            <span class="res-item__actions">
                <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteCantineSlot(${index})" aria-label="Supprimer ce créneau" title="Supprimer">${icon("i-trash")}</button>
            </span>`;
        list.appendChild(item);
    });
    setCount("cantine-count", slots.length);
}
"""

FUNCS["updateSavedSchedulesList"] = r"""
async function updateSavedSchedulesList() {
    const listContainer = document.getElementById("saved-schedules-list");
    if (!listContainer) return;

    try {
        const schedules = await listSavedSchedules();
        listContainer.innerHTML = "";

        if (!schedules.length) {
            listContainer.innerHTML = emptyStateHtml(
                "i-database",
                "Aucune sauvegarde",
                "Nommez votre emploi du temps puis enregistrez-le pour le retrouver plus tard.",
            );
            return;
        }

        schedules.forEach((schedule) => {
            const item = document.createElement("div");
            item.className = "res-item";
            const updated = new Date(schedule.updatedAt);
            const dateLabel = updated.toLocaleString("fr-FR", {
                dateStyle: "short",
                timeStyle: "short",
            });
            item.innerHTML = `
                <span class="res-item__avatar" aria-hidden="true">${icon("i-database")}</span>
                <span class="res-item__text">
                    <span class="res-item__name">${escapeHtml(schedule.name)}</span>
                    <span class="res-item__meta">Modifié le ${escapeHtml(dateLabel)}</span>
                </span>
                <span class="res-item__actions">
                    <button class="icon-btn icon-btn--sm" type="button" onclick="loadFromSlot(${schedule.id})" aria-label="Charger ${escapeHtml(schedule.name)}" title="Charger">${icon("i-upload")}</button>
                    <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteSavedSchedule(${schedule.id})" aria-label="Supprimer ${escapeHtml(schedule.name)}" title="Supprimer">${icon("i-trash")}</button>
                </span>`;
            listContainer.appendChild(item);
        });
    } catch (error) {
        console.error("Erreur:", error);
        listContainer.innerHTML = emptyStateHtml(
            "i-alert",
            "Stockage indisponible",
            "Les sauvegardes locales ne sont pas accessibles dans ce navigateur.",
        );
    }
}
"""

# ---------------------------------------------------------------- cours
FUNCS["updateCourseList"] = r"""
function updateCourseList() {
    const list = document.getElementById("course-list");
    if (!list) return;

    const searchInput = document.getElementById("course-search");
    const term = (searchInput ? searchInput.value : "").trim().toLowerCase();
    const openAccordions = Array.isArray(appData.openTeacherAccordions)
        ? appData.openTeacherAccordions
        : (appData.openTeacherAccordions = []);

    const matches = (course) => {
        if (!term) return true;
        const teacherNames = (course.teacherIds || [])
            .map((id) => {
                const teacher = appData.teachers.find((t) => t.id === id);
                return teacher ? teacher.name : "";
            })
            .join(" ");
        const room = appData.rooms.find((r) => r.id === course.roomId);
        const classInfo = getClassInfo(course.classId) || "";
        return `${course.name} ${teacherNames} ${classInfo} ${room ? room.name : ""}`
            .toLowerCase()
            .includes(term);
    };

    const visibleCourses = appData.courses.filter(matches);
    const coursesByTeacher = {};

    visibleCourses.forEach((course) => {
        (course.teacherIds || []).forEach((teacherId) => {
            const teacher = appData.teachers.find((t) => t.id === teacherId);
            if (!teacher) return;
            if (!coursesByTeacher[teacher.id]) {
                coursesByTeacher[teacher.id] = { teacher, courses: [] };
            }
            coursesByTeacher[teacher.id].courses.push(course);
        });
    });

    list.innerHTML = "";

    if (!visibleCourses.length) {
        list.innerHTML = emptyStateHtml(
            "i-book",
            term ? "Aucun cours trouvé" : "Aucun cours",
            term
                ? "Essayez un autre mot-clé (matière, professeur, classe, salle)."
                : "Créez votre premier cours pour commencer à construire le planning.",
        );
    }

    Object.keys(coursesByTeacher).forEach((teacherId) => {
        const { teacher, courses } = coursesByTeacher[teacherId];
        const isOpen =
            Boolean(term) ||
            openAccordions.includes(teacherId) ||
            (!openAccordions.length &&
                Object.keys(coursesByTeacher)[0] === teacherId);

        const accordion = document.createElement("div");
        accordion.className = "accordion" + (isOpen ? " is-open" : "");

        const header = document.createElement("button");
        header.type = "button";
        header.className = "accordion__head";
        header.dataset.teacherId = teacherId;
        header.setAttribute("aria-expanded", isOpen ? "true" : "false");
        header.innerHTML = `
            <span class="accordion__avatar" aria-hidden="true">${escapeHtml(initialsOf(teacher.name))}</span>
            <span class="accordion__title">${escapeHtml(teacher.name)}</span>
            <span class="accordion__meta">${plural(courses.length, "cours", "cours")}</span>
            ${icon("i-chevron")}
        `;
        header.querySelector(".icon").classList.add("accordion__chevron");
        header.onclick = (event) => {
            event.stopPropagation();
            toggleAccordion(accordion, teacherId);
        };

        const content = document.createElement("div");
        content.className = "accordion__body";

        courses.forEach((course) => {
            const halfGroup = appData.halfGroups.find(
                (x) => x.id === course.classId,
            );
            const cls = halfGroup
                ? null
                : appData.classes.find((x) => x.id === course.classId);
            const classGroup = appData.classGroups.find(
                (x) => x.id === course.classId,
            );
            const room = appData.rooms.find((r) => r.id === course.roomId);
            const classLabel = halfGroup
                ? `${halfGroup.name}`
                : cls
                  ? cls.name
                  : classGroup
                    ? `${classGroup.name} (groupe)`
                    : "Classe non définie";
            const priority = ["Faible", "Moyenne", "Haute"][
                (course.priority || 2) - 1
            ];
            const weekType = course.weekType || "Toutes";
            const weekBadge =
                weekType === "A"
                    ? '<span class="badge badge--a">Semaine A</span>'
                    : weekType === "B"
                      ? '<span class="badge badge--b">Semaine B</span>'
                      : '<span class="badge badge--all">Toutes semaines</span>';

            const card = document.createElement("article");
            card.className = "course-card";
            card.innerHTML = `
                <div class="course-card__top">
                    <h4 class="course-card__name">${escapeHtml(course.name)}</h4>
                    <div class="course-card__actions">
                        <button class="icon-btn icon-btn--sm" type="button" onclick="editCourse('${course.id}')" aria-label="Modifier ${escapeHtml(course.name)}" title="Modifier">${icon("i-pencil")}</button>
                        <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="deleteCourse('${course.id}')" aria-label="Supprimer ${escapeHtml(course.name)}" title="Supprimer">${icon("i-trash")}</button>
                    </div>
                </div>
                <div class="meta">
                    <span class="meta__item">${icon("i-cap")}${escapeHtml(classLabel)}</span>
                    <span class="meta__item">${icon("i-clock")}${escapeHtml(formatCourseDuration(course))}</span>
                    <span class="meta__item">${icon("i-rotate")}${course.frequency || 1}× / sem.</span>
                    <span class="meta__item">${icon("i-door")}${escapeHtml(room ? room.name : "Sans salle")}</span>
                    <span class="badge badge--priority-${(course.priority || 2)}">${escapeHtml(priority)}</span>
                    ${weekBadge}
                </div>`;
            content.appendChild(card);
        });

        accordion.appendChild(header);
        accordion.appendChild(content);
        list.appendChild(accordion);
    });

    const teachersWithoutCourses = appData.teachers.filter(
        (t) =>
            !appData.courses.some((c) => (c.teacherIds || []).includes(t.id)),
    );
    if (teachersWithoutCourses.length && !term) {
        const warning = document.createElement("p");
        warning.className = "note note--warning";
        warning.innerHTML = `${icon("i-alert")}<span>${escapeHtml(
            teachersWithoutCourses.map((t) => t.name).join(", "),
        )} ${teachersWithoutCourses.length > 1 ? "n'ont" : "n'a"} aucun cours affecté.</span>`;
        list.appendChild(warning);
    }

    const summary = document.getElementById("course-summary");
    if (summary) {
        const weeklyHours = appData.courses.reduce(
            (total, course) =>
                total +
                slotsToDuration(course.duration || SLOTS_PER_HOUR) *
                    (course.frequency || 1),
            0,
        );
        const visible = term
            ? `${visibleCourses.length} / ${appData.courses.length} cours`
            : plural(appData.courses.length, "cours", "cours");
        summary.textContent = `${visible} · ${weeklyHours} h hebdomadaires`;
    }
}
"""

FUNCS["toggleAccordion"] = r"""
function toggleAccordion(accordion, teacherId) {
    const isActive = accordion.classList.contains("is-open");
    const header = accordion.querySelector(".accordion__head");
    accordion.classList.toggle("is-open", !isActive);
    if (header) {
        header.setAttribute("aria-expanded", isActive ? "false" : "true");
    }

    if (!Array.isArray(appData.openTeacherAccordions)) {
        appData.openTeacherAccordions = [];
    }
    if (isActive) {
        appData.openTeacherAccordions =
            appData.openTeacherAccordions.filter((id) => id !== teacherId);
    } else if (!appData.openTeacherAccordions.includes(teacherId)) {
        appData.openTeacherAccordions.push(teacherId);
    }
}
"""

FUNCS["expandAllTeachers"] = r"""
function expandAllTeachers() {
    if (!Array.isArray(appData.openTeacherAccordions)) {
        appData.openTeacherAccordions = [];
    }
    let changed = false;
    document.querySelectorAll(".accordion").forEach((accordion) => {
        const header = accordion.querySelector(".accordion__head");
        const teacherId = header ? header.dataset.teacherId : null;
        if (!teacherId || accordion.classList.contains("is-open")) return;
        accordion.classList.add("is-open");
        header.setAttribute("aria-expanded", "true");
        if (!appData.openTeacherAccordions.includes(teacherId)) {
            appData.openTeacherAccordions.push(teacherId);
        }
        changed = true;
    });
    if (changed) showNotification("Tous les professeurs déroulés");
}
"""

FUNCS["collapseAllTeachers"] = r"""
function collapseAllTeachers() {
    let changed = false;
    document.querySelectorAll(".accordion").forEach((accordion) => {
        const header = accordion.querySelector(".accordion__head");
        if (!accordion.classList.contains("is-open")) return;
        accordion.classList.remove("is-open");
        if (header) header.setAttribute("aria-expanded", "false");
        changed = true;
    });
    appData.openTeacherAccordions = [];
    if (changed) showNotification("Tous les professeurs repliés");
}
"""

FUNCS["toggleCoursePanel"] = r"""
function toggleCoursePanel(force) {
    const panel = document.getElementById("course-panel");
    const toggle = document.getElementById("course-panel-toggle");
    if (!panel) return;
    const isOpen =
        typeof force === "boolean"
            ? force
            : !panel.classList.contains("is-open");
    panel.classList.toggle("is-open", isOpen);
    if (toggle) {
        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        toggle.innerHTML = isOpen
            ? `${icon("i-x")}<span>Fermer</span>`
            : `${icon("i-plus")}<span>Nouveau cours</span>`;
    }
    if (isOpen) {
        const nameInput = document.getElementById("course-name");
        if (nameInput && !currentEditItem) {
            nameInput.focus({ preventScroll: true });
        }
    }
}
"""

FUNCS["openCoursePanel"] = r"""
function openCoursePanel() {
    toggleCoursePanel(true);
}
"""

FUNCS["resetCourseForm"] = r"""
function resetCourseForm() {
    document.getElementById("course-name").value = "";
    document.getElementById("course-class").value = "";
    document.getElementById("course-room").value = "";
    document.getElementById("course-duration").value = "2";
    document.getElementById("course-frequency").value = "1";
    document.getElementById("course-priority").value = "2";
    document.getElementById("course-constraints").value = "";
    document.getElementById("course-week-type").value = "Toutes";
    document.getElementById("course-fixed-day").value = "";
    document.getElementById("course-fixed-start-slot").value = "";
    selectedTeachers = [];
    updateSelectedTeachersDisplay();
    updateTeacherCheckboxes();
    closeTeacherDropdown();
    currentEditItem = null;
    const submit = document.getElementById("course-submit");
    if (submit) {
        submit.innerHTML = `${icon("i-check")}<span>Enregistrer le cours</span>`;
    }
    const toggle = document.getElementById("course-panel-toggle");
    if (toggle) {
        toggle.innerHTML = `${icon("i-x")}<span>Fermer</span>`;
    }
}
"""

FUNCS["editCourse"] = r"""
function editCourse(id) {
    const course = appData.courses.find((x) => x.id === id);
    if (!course) return;

    switchTab("courses");

    document.getElementById("course-name").value = course.name;
    document.getElementById("course-class").value = course.classId || "";
    document.getElementById("course-room").value = course.roomId || "";
    document.getElementById("course-duration").value = course.duration || 2;
    document.getElementById("course-frequency").value = course.frequency || 1;
    document.getElementById("course-priority").value = course.priority || 2;
    document.getElementById("course-constraints").value =
        course.constraints || "";
    document.getElementById("course-week-type").value =
        course.weekType || "Toutes";
    document.getElementById("course-fixed-day").value = course.fixedDay || "";
    document.getElementById("course-fixed-start-slot").value =
        course.fixedStartSlot || "";

    selectedTeachers = [...(course.teacherIds || [])];
    updateSelectedTeachersDisplay();
    updateTeacherCheckboxes();

    currentEditItem = { type: "course", data: course };
    openCoursePanel();

    const submit = document.getElementById("course-submit");
    if (submit) {
        submit.innerHTML = `${icon("i-check")}<span>Mettre à jour</span>`;
    }
    const toggle = document.getElementById("course-panel-toggle");
    if (toggle) {
        toggle.innerHTML = `${icon("i-x")}<span>Fermer</span>`;
    }
    document
        .getElementById("course-panel")
        .scrollIntoView({ behavior: "smooth", block: "start" });
}
"""

FUNCS["deleteCourse"] = r"""
function removeCourseFromSchedule(schedule, courseId) {
    if (!schedule) return;
    DAYS.forEach((day) => {
        if (!schedule[day]) return;
        TIME_SLOTS.forEach((slot) => {
            const value = schedule[day][slot];
            if (!value) return;
            if (Array.isArray(value)) {
                const next = value.filter((sd) => sd.courseId !== courseId);
                schedule[day][slot] = next.length ? next : null;
            } else if (value.courseId === courseId) {
                schedule[day][slot] = null;
            }
        });
    });
}

function deleteCourse(id) {
    const course = appData.courses.find((x) => x.id === id);
    if (!course) return;
    showConfirm(
        `Supprimer « ${course.name} » ?`,
        "Le cours sera retiré du catalogue et de tous les créneaux des semaines A et B.",
        () => {
            appData.courses = appData.courses.filter((x) => x.id !== id);
            [
                appData.schedule,
                appData.scheduleA,
                appData.scheduleB,
            ].forEach((schedule) => removeCourseFromSchedule(schedule, id));
            updateCourseList();
            updateScheduleDisplay();
            saveData();
            showNotification(`Cours « ${course.name} » supprimé`);
        },
        "Supprimer",
    );
}
"""

# ---------------------------------------------------------------- checkboxes
FUNCS["updateTeacherCheckboxes"] = r"""
function updateTeacherCheckboxes() {
    const container = document.getElementById("teacher-checkboxes");
    if (!container) return;
    if (!appData.teachers.length) {
        container.innerHTML = emptyStateHtml(
            "i-users",
            "Aucun professeur",
            "Ajoutez d'abord un professeur dans l'onglet Ressources.",
        );
        return;
    }
    container.innerHTML = appData.teachers
        .map((teacher) => {
            const isSelected = selectedTeachers.includes(teacher.id);
            return `<label class="check">
                <input type="checkbox" id="teacher-${teacher.id}" value="${teacher.id}" ${isSelected ? "checked" : ""} onchange="updateSelectedTeachers()">
                <span>${escapeHtml(teacher.name)}</span>
            </label>`;
        })
        .join("");
}
"""

FUNCS["updateSelectedTeachersDisplay"] = r"""
function updateSelectedTeachersDisplay() {
    const container = document.getElementById("selected-teachers-tags");
    if (!container) return;
    if (!selectedTeachers.length) {
        container.innerHTML =
            '<span class="picker__placeholder">Sélectionner des professeurs</span>';
        return;
    }
    container.innerHTML = selectedTeachers
        .map((teacherId) => {
            const teacher = appData.teachers.find((t) => t.id === teacherId);
            if (!teacher) return "";
            return `<span class="picker__tag">
                <span>${escapeHtml(teacher.name)}</span>
                <button type="button" onclick="event.stopPropagation(); removeSelectedTeacher('${teacherId}')" aria-label="Retirer ${escapeHtml(teacher.name)}">${icon("i-x")}</button>
            </span>`;
        })
        .join("");
}
"""

FUNCS["updateClassCheckboxes"] = r"""
function updateClassCheckboxes() {
    const container = document.getElementById("class-checkboxes");
    if (!container) return;
    if (!appData.classes.length) {
        container.innerHTML = emptyStateHtml(
            "i-cap",
            "Aucune classe",
            "Ajoutez des classes pour créer un groupe.",
        );
        return;
    }
    container.innerHTML = appData.classes
        .map((cls) => {
            const isSelected = selectedClasses.includes(cls.id);
            return `<label class="check">
                <input type="checkbox" id="class-${cls.id}" value="${cls.id}" ${isSelected ? "checked" : ""} onchange="updateSelectedClasses()">
                <span>${escapeHtml(cls.name)}</span>
            </label>`;
        })
        .join("");
}
"""

FUNCS["updateSelectedClassesDisplay"] = r"""
function updateSelectedClassesDisplay() {
    const container = document.getElementById("selected-classes-tags");
    if (!container) return;
    if (!selectedClasses.length) {
        container.innerHTML =
            '<span class="picker__placeholder">Sélectionner des classes</span>';
        return;
    }
    container.innerHTML = selectedClasses
        .map((classId) => {
            const cls = appData.classes.find((c) => c.id === classId);
            if (!cls) return "";
            return `<span class="picker__tag">
                <span>${escapeHtml(cls.name)}</span>
                <button type="button" onclick="event.stopPropagation(); removeSelectedClass('${classId}')" aria-label="Retirer ${escapeHtml(cls.name)}">${icon("i-x")}</button>
            </span>`;
        })
        .join("");
}
"""

FUNCS["updateForbiddenTeacherCheckboxes"] = r"""
function updateForbiddenTeacherCheckboxes() {
    const container = document.getElementById("forbidden-teacher-checkboxes");
    if (!container) return;
    if (!appData.teachers.length) {
        container.innerHTML = emptyStateHtml(
            "i-users",
            "Aucun professeur",
            "Ajoutez d'abord un professeur dans l'onglet Ressources.",
        );
        return;
    }
    container.innerHTML = appData.teachers
        .map((teacher) => {
            const isSelected = selectedForbiddenTeachers.includes(teacher.id);
            return `<label class="check">
                <input type="checkbox" id="forbidden-teacher-${teacher.id}" value="${teacher.id}" ${isSelected ? "checked" : ""} onchange="updateSelectedForbiddenTeachers()">
                <span>${escapeHtml(teacher.name)}</span>
            </label>`;
        })
        .join("");
}
"""

FUNCS["updateSelectedForbiddenTeachersDisplay"] = r"""
function updateSelectedForbiddenTeachersDisplay() {
    const container = document.getElementById(
        "selected-forbidden-teachers-tags",
    );
    if (!container) return;
    if (!selectedForbiddenTeachers.length) {
        container.innerHTML =
            '<span class="picker__placeholder">Sélectionner des professeurs</span>';
        return;
    }
    container.innerHTML = selectedForbiddenTeachers
        .map((teacherId) => {
            const teacher = appData.teachers.find((t) => t.id === teacherId);
            if (!teacher) return "";
            return `<span class="picker__tag">
                <span>${escapeHtml(teacher.name)}</span>
                <button type="button" onclick="event.stopPropagation(); removeSelectedForbiddenTeacher('${teacherId}')" aria-label="Retirer ${escapeHtml(teacher.name)}">${icon("i-x")}</button>
            </span>`;
        })
        .join("");
}
"""

# ---------------------------------------------------------------- planning
FUNCS["switchWeekView"] = r"""
function switchWeekView(view) {
    currentWeekView = view;

    if (view === "A") appData.schedule = appData.scheduleA;
    else if (view === "B") appData.schedule = appData.scheduleB;
    else appData.schedule = appData.scheduleA;

    document.querySelectorAll("[data-week]").forEach((button) => {
        const isActive = button.dataset.week === view;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });

    const singleLabel = document.getElementById("single-week-label");
    if (singleLabel) {
        const isWeekA = view !== "B";
        singleLabel.innerHTML = `<span class="week-block__badge week-block__badge--${isWeekA ? "a" : "b"}">${isWeekA ? "A" : "B"}</span>Semaine ${isWeekA ? "A" : "B"}`;
    }

    updateWeekViewDisplay();
    updateScheduleDisplay();
}
"""

FUNCS["updateWeekViewDisplay"] = r"""
function updateWeekViewDisplay() {
    const containerA = document.getElementById("schedule-a-container");
    const containerB = document.getElementById("schedule-b-container");
    const containerSingle = document.getElementById(
        "schedule-single-container",
    );
    const showBoth = currentWeekView === "both";

    if (containerA) containerA.classList.toggle("active", showBoth);
    if (containerB) containerB.classList.toggle("active", showBoth);
    if (containerSingle) containerSingle.classList.toggle("active", !showBoth);
}
"""

FUNCS["updateScheduleTypeSelector"] = r"""
function updateScheduleTypeSelector() {
    const typeSelect = document.getElementById("schedule-type-selector");
    const itemSelect = document.getElementById("schedule-item-selector");
    const itemLabel = document.getElementById("schedule-item-label");
    if (!typeSelect || !itemSelect || !itemLabel) return;

    const type = typeSelect.value;
    currentSelectedItem = { type, id: "" };
    itemSelect.innerHTML = "";

    if (type === "all") {
        itemLabel.textContent = "Ressource";
        itemSelect.disabled = true;
        itemSelect.innerHTML = '<option value="">Toutes</option>';
        updateFilterChip();
        updateScheduleDisplay();
        return;
    }

    const entries = [];
    if (type === "teacher") {
        itemLabel.textContent = "Professeur";
        appData.teachers.forEach((teacher) =>
            entries.push({ value: teacher.id, label: teacher.name }),
        );
    } else if (type === "class") {
        itemLabel.textContent = "Classe / Groupe";
        appData.classes.forEach((cls) =>
            entries.push({ value: cls.id, label: `${cls.name} · classe` }),
        );
        appData.halfGroups.forEach((hg) =>
            entries.push({
                value: hg.id,
                label: `${hg.name} · demi-groupe`,
            }),
        );
        appData.classGroups.forEach((cg) =>
            entries.push({ value: cg.id, label: `${cg.name} · groupe` }),
        );
    } else if (type === "room") {
        itemLabel.textContent = "Salle";
        appData.rooms.forEach((room) =>
            entries.push({
                value: room.id,
                label: `${room.name} · ${room.capacity} pl.`,
            }),
        );
    }

    if (!entries.length) {
        itemSelect.disabled = true;
        itemSelect.innerHTML =
            '<option value="">Aucune ressource disponible</option>';
        updateFilterChip();
        updateScheduleDisplay();
        return;
    }

    itemSelect.disabled = false;
    itemSelect.innerHTML = entries
        .map((entry) => `<option value="${entry.value}">${escapeHtml(entry.label)}</option>`)
        .join("");

    currentSelectedItem = { type, id: entries[0].value };
    itemSelect.value = entries[0].value;
    updateFilterChip();
    updateScheduleDisplay();
}
"""

FUNCS["filterScheduleByItem"] = r"""
function filterScheduleByItem() {
    const typeSelect = document.getElementById("schedule-type-selector");
    const itemSelect = document.getElementById("schedule-item-selector");
    if (!typeSelect || !itemSelect) return;

    currentSelectedItem = {
        type: typeSelect.value,
        id: itemSelect.value,
    };
    updateFilterChip();
    updateScheduleDisplay();
}
"""

NEW_FUNCS = {
    "clearScheduleFilter": r"""
function clearScheduleFilter() {
    const typeSelect = document.getElementById("schedule-type-selector");
    if (!typeSelect) return;
    typeSelect.value = "all";
    updateScheduleTypeSelector();
}
""",
    "updateFilterChip": r"""
function updateFilterChip() {
    const chip = document.getElementById("active-filter");
    const text = document.getElementById("active-filter-text");
    if (!chip || !text) return;

    const selection = currentSelectedItem || { type: "all", id: "" };
    if (!selection.id || selection.type === "all") {
        chip.hidden = true;
        return;
    }

    let label = "";
    let prefix = "";
    if (selection.type === "teacher") {
        const teacher = appData.teachers.find((t) => t.id === selection.id);
        label = teacher ? teacher.name : "";
        prefix = "Professeur";
    } else if (selection.type === "class") {
        label = getClassInfo(selection.id) || "";
        prefix = "Classe";
    } else if (selection.type === "room") {
        const room = appData.rooms.find((r) => r.id === selection.id);
        label = room ? room.name : "";
        prefix = "Salle";
    }

    if (!label) {
        chip.hidden = true;
        return;
    }
    text.textContent = `${prefix} · ${label}`;
    chip.hidden = false;
    toggleScheduleFilters(true);
}

function toggleScheduleFilters(force) {
    const toolbar = document.querySelector("#schedule .toolbar");
    if (!toolbar) return;
    const open =
        force === undefined ? toolbar.dataset.filtersOpen !== "true" : !!force;
    toolbar.dataset.filtersOpen = open ? "true" : "false";
    const button = document.getElementById("filters-toggle");
    if (button) button.setAttribute("aria-expanded", open ? "true" : "false");
}
""",
    "setDayFocus": r"""
function setDayFocus(index) {
    const next = Math.min(Math.max(Number(index) || 0, 0), DAYS.length - 1);
    currentDayIndex = next;
    try {
        localStorage.setItem("flowEdtDay", String(next));
    } catch (error) {
        /* stockage indisponible */
    }
    document.querySelectorAll(".timetable").forEach((table) => {
        table.dataset.dayFocus = String(next);
    });
    document.querySelectorAll(".day-tab").forEach((tab) => {
        const isActive = Number(tab.dataset.dayIndex) === next;
        tab.classList.toggle("active", isActive);
        tab.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
    updateDayTabs();
}
""",
    "updateDayTabs": r"""
function updateDayTabs() {
    const tabs = document.querySelectorAll(".day-tab");
    if (!tabs.length) return;

    const filterFn = getCurrentFilterFn();
    const schedules =
        currentWeekView === "both"
            ? [appData.scheduleA, appData.scheduleB]
            : [getCurrentSchedule()];

    const countDay = (day) => {
        let count = 0;
        schedules.forEach((schedule) => {
            if (!schedule || !schedule[day]) return;
            TIME_SLOTS.forEach((slot) => {
                const value = schedule[day][slot];
                if (!value) return;
                const list = Array.isArray(value) ? value : [value];
                list.forEach((slotData) => {
                    if (!slotData || !slotData.courseId) return;
                    if (slotData.slotIndex) return;
                    const course = appData.courses.find(
                        (c) => c.id === slotData.courseId,
                    );
                    if (!course) return;
                    if (filterFn && !filterFn(slotData, course)) return;
                    count += 1;
                });
            });
        });
        return count;
    };

    tabs.forEach((tab) => {
        const day = DAYS[Number(tab.dataset.dayIndex)];
        const counter = tab.querySelector(".day-tab__count");
        if (counter && day) counter.textContent = countDay(day);
    });
}
""",
    "updateLegend": r"""
function updateLegend() {
    const box = document.getElementById("schedule-legend");
    const items = document.getElementById("legend-items");
    if (!box || !items) return;

    // La légende ne liste que les professeurs réellement affichés.
    const usedCourseIds = new Set();
    [appData.scheduleA, appData.scheduleB].forEach((schedule) => {
        const visible = filterScheduleBySelection(schedule);
        DAYS.forEach((day) => {
            if (!visible[day]) return;
            TIME_SLOTS.forEach((slot) => {
                const value = visible[day][slot];
                if (!value) return;
                (Array.isArray(value) ? value : [value]).forEach((slotData) => {
                    if (slotData && slotData.courseId) {
                        usedCourseIds.add(slotData.courseId);
                    }
                });
            });
        });
    });

    const teacherIds = [];
    appData.courses.forEach((course) => {
        if (!usedCourseIds.has(course.id)) return;
        (course.teacherIds || []).forEach((teacherId) => {
            if (!teacherIds.includes(teacherId)) teacherIds.push(teacherId);
        });
    });

    if (!teacherIds.length) {
        box.hidden = true;
        return;
    }

    box.hidden = false;
    items.innerHTML = teacherIds
        .slice(0, 16)
        .map((teacherId) => {
            const teacher = appData.teachers.find((t) => t.id === teacherId);
            if (!teacher) return "";
            return `<span class="legend__item"><span class="legend__dot" style="--dot:${getTeacherColor(teacherId)}"></span>${escapeHtml(teacher.name)}</span>`;
        })
        .join("");
}
""",
    "countPlacedCourses": r"""
function countPlacedCourses() {
    const seen = new Set();
    [appData.scheduleA, appData.scheduleB].forEach((schedule) => {
        if (!schedule) return;
        DAYS.forEach((day) => {
            if (!schedule[day]) return;
            TIME_SLOTS.forEach((slot) => {
                const value = schedule[day][slot];
                if (!value) return;
                (Array.isArray(value) ? value : [value]).forEach((slotData) => {
                    if (slotData && slotData.courseId) {
                        seen.add(slotData.courseId);
                    }
                });
            });
        });
    });
    return seen.size;
}
""",
    "updateScheduleCallout": r"""
function updateScheduleCallout() {
    const box = document.getElementById("schedule-callout");
    if (!box) return;

    // Grille inutile tant que rien n'existe : on la masque au profit du guide.
    const pristine =
        !appData.teachers.length &&
        !appData.classes.length &&
        !appData.courses.length;
    const weekArea = document.querySelector(".week-area");
    const dayTabs = document.getElementById("day-tabs");
    const toolbar = document.querySelector("#schedule .toolbar");
    const kpis = document.querySelector("#schedule .kpis");
    [weekArea, dayTabs, toolbar, kpis].forEach((element) => {
        if (element) element.hidden = pristine;
    });

    if (pristine) {
        box.hidden = false;
        box.innerHTML = `${icon("i-users")}
            <span class="callout__text"><strong>Votre établissement est vide</strong>Ajoutez vos professeurs, salles et classes : tout se saisit ici, rien n'est prérempli.</span>
            <span class="callout__actions">
                <button class="btn btn--primary btn--sm" type="button" onclick="switchTab('resources')">Configurer les ressources</button>
            </span>`;
        return;
    }

    if (!appData.teachers.length || !appData.classes.length) {
        box.hidden = false;
        box.innerHTML = `${icon("i-users")}
            <span class="callout__text"><strong>Ressources incomplètes</strong>Il manque au moins un professeur ou une classe pour placer des cours.</span>
            <span class="callout__actions">
                <button class="btn btn--primary btn--sm" type="button" onclick="switchTab('resources')">Compléter les ressources</button>
            </span>`;
        return;
    }

    if (!appData.courses.length) {
        box.hidden = false;
        box.innerHTML = `${icon("i-book")}
            <span class="callout__text"><strong>Commencez par créer un cours</strong>Ajoutez vos matières et leurs contraintes, puis générez le planning.</span>
            <span class="callout__actions">
                <button class="btn btn--primary btn--sm" type="button" onclick="switchTab('courses'); openCoursePanel();">Ajouter un cours</button>
                <button class="btn btn--ghost btn--sm" type="button" onclick="switchTab('resources')">Configurer les ressources</button>
            </span>`;
        return;
    }

    // Filtre actif mais aucune ligne à afficher : on l'annonce clairement.
    if (getCurrentFilterFn() && countVisibleCourses() === 0) {
        const name = currentSelectionName();
        box.hidden = false;
        box.innerHTML = `${icon("i-search")}
            <span class="callout__text"><strong>Aucun cours ${name ? "pour " + escapeHtml(name) : "pour cette sélection"}</strong>Changez de semaine ou retirez le filtre pour retrouver tout le planning.</span>
            <span class="callout__actions">
                <button class="btn btn--primary btn--sm" type="button" onclick="clearScheduleFilter()">Retirer le filtre</button>
            </span>`;
        return;
    }

    if (countPlacedCourses() === 0) {
        box.hidden = false;
        box.innerHTML = `${icon("i-sparkles")}
            <span class="callout__text"><strong>Planning vide</strong>Générez une première proposition, puis ajustez les créneaux à la main.</span>
            <span class="callout__actions">
                <button class="btn btn--primary btn--sm" type="button" data-generate onclick="openGenerationSheet()">Génération automatique</button>
            </span>`;
        return;
    }

    box.hidden = true;
}
""",
    "openSheet": r"""
function openSheet(id) {
    const sheet = document.getElementById(id);
    if (!sheet) return;
    lastFocusedElement = document.activeElement;
    const modalConfirm = sheet.querySelector("#modal-confirm");
    if (modalConfirm) modalConfirm.style.display = "";
    sheet.classList.add("active");
    document.body.style.overflow = "hidden";
    const menuToggle = document.getElementById("menu-toggle");
    if (menuToggle && id === "app-menu") {
        menuToggle.setAttribute("aria-expanded", "true");
    }
    const focusable = sheet.querySelector(
        "input:not([type=hidden]), select, textarea, button",
    );
    if (focusable) {
        window.setTimeout(() => focusable.focus({ preventScroll: true }), 60);
    }
}
""",
    "closeSheet": r"""
function closeSheet(id) {
    const sheet = document.getElementById(id);
    if (!sheet) return;
    sheet.classList.remove("active");
    if (!document.querySelector(".sheet.active")) {
        document.body.style.overflow = "";
    }
    const menuToggle = document.getElementById("menu-toggle");
    if (menuToggle && id === "app-menu") {
        menuToggle.setAttribute("aria-expanded", "false");
    }
    if (
        lastFocusedElement &&
        typeof lastFocusedElement.focus === "function" &&
        document.contains(lastFocusedElement)
    ) {
        lastFocusedElement.focus({ preventScroll: true });
    }
    lastFocusedElement = null;
}
""",
    "openExportModal": r"""
function openExportModal() {
    openSheet("export-modal");
}
""",
    "closeExportModal": r"""
function closeExportModal() {
    closeSheet("export-modal");
}
""",
    "showConfirm": r"""
function showConfirm(title, message, action, confirmLabel) {
    const modal = document.getElementById("confirm-modal");
    const body = document.getElementById("confirm-message");
    const heading = document.getElementById("confirm-title");
    if (!modal || !body) return;

    if (heading) heading.textContent = title;
    body.innerHTML = `<p>${escapeHtml(message)}</p>`;
    const confirmButton = modal.querySelector(".sheet__foot .btn--danger");
    if (confirmButton) {
        confirmButton.innerHTML = `${icon("i-trash")}<span>${escapeHtml(confirmLabel || "Confirmer")}</span>`;
    }
    confirmAction = action;
    openSheet("confirm-modal");
}
""",
    "initDayFocus": r"""
function initDayFocus() {
    let saved = 0;
    try {
        saved = parseInt(localStorage.getItem("flowEdtDay") || "0", 10);
    } catch (error) {
        saved = 0;
    }
    if (!Number.isInteger(saved) || saved < 0 || saved >= DAYS.length) {
        saved = 0;
    }
    document.querySelectorAll(".day-tab").forEach((tab) => {
        tab.addEventListener("click", () =>
            setDayFocus(Number(tab.dataset.dayIndex)),
        );
    });
    setDayFocus(saved);
}
""",
    "initSheets": r"""
function initSheets() {
    document.querySelectorAll(".sheet").forEach((sheet) => {
        const backdrop = sheet.querySelector(".sheet__backdrop");
        if (backdrop) {
            backdrop.addEventListener("click", () => closeSheet(sheet.id));
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            const openSheetElement = document.querySelector(".sheet.active");
            if (openSheetElement) {
                closeSheet(openSheetElement.id);
                return;
            }
            closeAllPickers();
            return;
        }

        // piège à focus : la tabulation reste dans la feuille ouverte
        if (event.key !== "Tab") return;
        const sheet = document.querySelector(".sheet.active");
        if (!sheet) return;
        const focusables = [
            ...sheet.querySelectorAll(
                'a[href], button:not([disabled]), input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
            ),
        ].filter((element) => element.offsetParent !== null);
        if (!focusables.length) return;

        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement;
        const inside = sheet.contains(active);

        if (event.shiftKey && (active === first || !inside)) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && (active === last || !inside)) {
            event.preventDefault();
            first.focus();
        }
    });
}
""",
    "initImportDropzone": r"""
function initImportDropzone() {
    const zone = document.getElementById("dropzone");
    const input = document.getElementById("import-file");
    if (!zone || !input) return;

    ["dragenter", "dragover"].forEach((type) => {
        zone.addEventListener(type, (event) => {
            event.preventDefault();
            zone.classList.add("is-over");
        });
    });
    ["dragleave", "dragend"].forEach((type) => {
        zone.addEventListener(type, () => zone.classList.remove("is-over"));
    });
    zone.addEventListener("drop", (event) => {
        event.preventDefault();
        zone.classList.remove("is-over");
        const file = event.dataTransfer && event.dataTransfer.files[0];
        if (file) handleFileSelect({ target: { files: [file] } });
    });
}
""",
    "initApp": r"""
function initApp() {
    initTheme();
    initDensity();
    initSheets();
    initAppMenu();
    initImportDropzone();
    initDayFocus();
    if (window.matchMedia("(min-width: 900px)").matches) {
        toggleCoursePanel(true);
    }
    document.addEventListener("click", (event) => {
        if (!event.target.closest(".picker__panel, .picker")) {
            closeAllPickers();
        }
    });
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") updateSavedSchedulesList();
    });
}
""",
    "initAppMenu": r"""
function initAppMenu() {
    const sheet = document.getElementById("app-menu");
    if (!sheet) return;
    // une entrée de navigation referme le menu (en plus du onclick du balisage)
    sheet.querySelectorAll("[data-tab]").forEach((item) => {
        item.addEventListener("click", () => closeSheet("app-menu"));
    });
}
""",
    "toggleAppMenu": r"""
function toggleAppMenu(force) {
    const sheet = document.getElementById("app-menu");
    if (!sheet) return;
    const open =
        typeof force === "boolean"
            ? force
            : !sheet.classList.contains("active");
    if (open) openSheet("app-menu");
    else closeSheet("app-menu");
}
""",
}

# Remplacements complets de fonctions existantes
FUNCS.update(NEW_FUNCS)

# ---------------------------------------------------------------- studio profs
# Onglet « Professeurs » : sélection d'un enseignant, objectif horaire, puis
# ajout de ses cours classe par classe. Les cours créés sont les mêmes objets
# que dans l'onglet Cours : le catalogue et le planning restent la référence.
STUDIO_STATE = r"""
let studioTeacherId = null;
let studioClassId = "";
let studioDuration = SLOTS_PER_HOUR;
let studioFrequency = 1;
const STUDIO_DEFAULT_HOURS = 18;

function studioTeacher() {
    return appData.teachers.find((t) => t.id === studioTeacherId) || null;
}

function studioHoursOf(teacherId) {
    return (appData.courses || []).reduce((total, course) => {
        if (!(course.teacherIds || []).includes(teacherId)) return total;
        return (
            total +
            slotsToDuration(course.duration || SLOTS_PER_HOUR) *
                (course.frequency || 1)
        );
    }, 0);
}

function formatStudioHours(value) {
    const rounded = Math.round((Number(value) || 0) * 10) / 10;
    return Number.isInteger(rounded)
        ? String(rounded)
        : rounded.toFixed(1).replace(".", ",");
}

function studioTargetOf(teacher) {
    const target = Number(teacher && teacher.weeklyHours);
    return Number.isFinite(target) && target >= 0 ? target : STUDIO_DEFAULT_HOURS;
}

function studioClassesCatalog() {
    const entries = [];
    (appData.classes || []).forEach((cls) =>
        entries.push({ id: cls.id, label: cls.name, title: `${cls.name} (classe entière)`, half: false }),
    );
    (appData.halfGroups || []).forEach((hg) => {
        const cls = (appData.classes || []).find((c) => c.id === hg.classId);
        const label = cls
            ? `${cls.name} · ${hg.groupNumber ? "G" + hg.groupNumber : hg.groupName || "groupe"}`
            : hg.name;
        entries.push({ id: hg.id, label, title: hg.name, half: true });
    });
    return entries;
}

function setStudioText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}
"""

FUNCS["renderTeacherStudio"] = r"""
function renderTeacherStudio() {
    if (!document.getElementById("studio-teacher-list")) return;
    if (!studioTeacherId) {
        try {
            studioTeacherId = localStorage.getItem("flowEdtStudioTeacher");
        } catch (error) {
            studioTeacherId = null;
        }
    }
    renderStudioRail();
    renderStudioPanel();
}
"""

FUNCS["renderStudioRail"] = r"""
function renderStudioRail() {
    const list = document.getElementById("studio-teacher-list");
    if (!list) return;

    const search = document.getElementById("studio-teacher-search");
    const term = (search ? search.value : "").trim().toLowerCase();
    const visible = appData.teachers.filter(
        (teacher) => !term || teacher.name.toLowerCase().includes(term),
    );

    setCount("studio-teacher-count", appData.teachers.length);

    if (!appData.teachers.length) {
        studioTeacherId = null;
        list.innerHTML = "";
        return;
    }
    if (!appData.teachers.some((teacher) => teacher.id === studioTeacherId)) {
        studioTeacherId = (visible[0] || appData.teachers[0]).id;
    }

    if (!visible.length) {
        list.innerHTML = `<p class="studio__rail-empty">Aucun professeur pour « ${escapeHtml(term)} ».</p>`;
        return;
    }

    list.innerHTML = visible
        .map((teacher) => {
            const hours = studioHoursOf(teacher.id);
            const target = studioTargetOf(teacher);
            const isActive = teacher.id === studioTeacherId;
            return `<button class="studio__rail-item${isActive ? " is-active" : ""}" type="button" role="option" aria-selected="${isActive}" data-teacher-id="${teacher.id}" onclick="selectStudioTeacher('${teacher.id}')">
                <span class="studio__rail-avatar" style="--dot:${getTeacherColor(teacher.id)}" aria-hidden="true">${escapeHtml(initialsOf(teacher.name))}</span>
                <span class="studio__rail-text">
                    <span class="studio__rail-name">${escapeHtml(teacher.name)}</span>
                    <span class="studio__rail-meta${hours > target ? " is-over" : ""}">${formatStudioHours(hours)} h / ${formatStudioHours(target)} h</span>
                </span>
            </button>`;
        })
        .join("");
}
"""

FUNCS["selectStudioTeacher"] = r"""
function selectStudioTeacher(id) {
    if (!appData.teachers.some((teacher) => teacher.id === id)) return;
    studioTeacherId = id;
    try {
        localStorage.setItem("flowEdtStudioTeacher", id);
    } catch (error) {
        /* stockage indisponible */
    }
    renderTeacherStudio();
}
"""

FUNCS["renderStudioPanel"] = r"""
function renderStudioPanel() {
    const none = document.getElementById("studio-none");
    const pick = document.getElementById("studio-pick");
    const body = document.getElementById("studio-body");
    if (!none || !pick || !body) return;

    const teacher = studioTeacher();
    none.hidden = appData.teachers.length > 0;
    pick.hidden = Boolean(teacher) || appData.teachers.length === 0;
    body.hidden = !teacher;
    if (!teacher) return;

    const avatar = document.getElementById("studio-avatar");
    if (avatar) {
        avatar.textContent = initialsOf(teacher.name);
        avatar.style.setProperty("--dot", getTeacherColor(teacher.id));
    }
    setStudioText("studio-name", teacher.name);

    const courses = appData.courses.filter((course) =>
        (course.teacherIds || []).includes(teacher.id),
    );
    const classCount = new Set(courses.map((course) => course.classId)).size;
    const meta = document.getElementById("studio-meta");
    if (meta) {
        meta.textContent = courses.length
            ? `${plural(courses.length, "cours", "cours")} · ${plural(classCount, "classe", "classes")}`
            : "Aucun cours pour l'instant";
    }

    const hoursInput = document.getElementById("studio-weekly-hours");
    if (hoursInput && document.activeElement !== hoursInput) {
        hoursInput.value = String(studioTargetOf(teacher));
    }

    renderStudioRooms();
    renderStudioClasses();
    renderStudioSuggestions();
    syncStudioPresets();
    renderStudioCourses();
    updateStudioGauge();
    updateStudioPreview();
}
"""

FUNCS["renderStudioRooms"] = r"""
function renderStudioRooms() {
    const select = document.getElementById("studio-room");
    if (!select) return;
    const previous = select.value;
    select.innerHTML =
        '<option value="">Sans salle</option>' +
        appData.rooms
            .map(
                (room) =>
                    `<option value="${room.id}">${escapeHtml(room.name)}</option>`,
            )
            .join("");
    select.value = appData.rooms.some((room) => room.id === previous)
        ? previous
        : "";
}
"""

FUNCS["renderStudioClasses"] = r"""
function renderStudioClasses() {
    const box = document.getElementById("studio-classes");
    if (!box) return;

    const entries = studioClassesCatalog();
    if (!entries.length) {
        studioClassId = "";
        box.innerHTML = `<p class="studio__inline-empty">Ajoutez d'abord des classes dans l'onglet <strong>Ressources</strong>.</p>`;
        return;
    }
    if (!entries.some((entry) => entry.id === studioClassId)) {
        studioClassId = entries[0].id;
    }
    box.innerHTML = entries
        .map((entry) => {
            const isActive = entry.id === studioClassId;
            return `<button class="chip${isActive ? " is-active" : ""}" type="button" aria-pressed="${isActive}" data-class-id="${entry.id}" title="${escapeHtml(entry.title)}" onclick="selectStudioClass('${entry.id}')">${icon(entry.half ? "i-half" : "i-cap")}<span>${escapeHtml(entry.label)}</span></button>`;
        })
        .join("");
}
"""

FUNCS["selectStudioClass"] = r"""
function selectStudioClass(id) {
    studioClassId = id;
    document
        .querySelectorAll("#studio-classes .chip")
        .forEach((chip) =>
            chip.classList.toggle("is-active", chip.dataset.classId === id),
        );
    document
        .querySelectorAll("#studio-classes .chip")
        .forEach((chip) =>
            chip.setAttribute(
                "aria-pressed",
                chip.dataset.classId === id ? "true" : "false",
            ),
        );
    updateStudioPreview();
}
"""

FUNCS["renderStudioSuggestions"] = r"""
function renderStudioSuggestions() {
    const list = document.getElementById("studio-course-suggestions");
    if (!list) return;
    const names = [
        ...new Set(
            appData.courses
                .map((course) => (course.name || "").trim())
                .filter(Boolean),
        ),
    ].sort((a, b) => a.localeCompare(b, "fr"));
    list.innerHTML = names
        .map((name) => `<option value="${escapeHtml(name)}"></option>`)
        .join("");
}
"""

FUNCS["syncStudioPresets"] = r"""
function syncStudioPresets() {
    const sync = (containerId, value) => {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.querySelectorAll("button[data-value]").forEach((button) => {
            const isActive = Number(button.dataset.value) === value;
            button.classList.toggle("active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    };
    sync("studio-duration", studioDuration);
    sync("studio-frequency", studioFrequency);
}
"""

FUNCS["selectStudioPreset"] = r"""
function selectStudioPreset(kind, value) {
    if (kind === "duration") {
        studioDuration = Math.min(Math.max(Number(value) || SLOTS_PER_HOUR, 1), 8);
    } else if (kind === "frequency") {
        studioFrequency = Math.min(Math.max(Number(value) || 1, 1), 5);
    }
    syncStudioPresets();
    updateStudioPreview();
}
"""

FUNCS["updateStudioPreview"] = r"""
function updateStudioPreview() {
    const preview = document.getElementById("studio-preview");
    if (!preview) return;
    const input = document.getElementById("studio-course-name");
    const name = input ? input.value.trim() : "";
    const entry = studioClassesCatalog().find((item) => item.id === studioClassId);
    const perSession = slotsToDuration(studioDuration);
    const weekly = perSession * studioFrequency;

    if (!name || !entry) {
        preview.textContent =
            "Choisissez une matière et une classe : le total horaire s'affiche ici.";
        return;
    }
    const detail =
        studioFrequency > 1
            ? `${formatStudioHours(perSession)} h × ${studioFrequency}`
            : `${formatStudioHours(perSession)} h`;
    preview.innerHTML = `<strong>${escapeHtml(name)}</strong> · ${escapeHtml(entry.label)} · ${detail} = <strong>${formatStudioHours(weekly)} h</strong> par semaine`;
}
"""

FUNCS["updateStudioGauge"] = r"""
function updateStudioGauge() {
    const gauge = document.getElementById("studio-gauge");
    const teacher = studioTeacher();
    if (!gauge || !teacher) return;

    const done = studioHoursOf(teacher.id);
    const target = studioTargetOf(teacher);
    const ratio = target > 0 ? Math.min(done / target, 1) : done > 0 ? 1 : 0;

    setStudioText("studio-hours-value", `${formatStudioHours(done)} h`);
    setStudioText("studio-hours-state", `sur ${formatStudioHours(target)} h`);
    setStudioText("studio-list-title", teacher.name);
    const total = document.getElementById("studio-list-total");
    if (total) total.textContent = `${formatStudioHours(done)} h / sem.`;

    const fill = document.getElementById("studio-gauge-fill");
    if (fill) fill.style.width = `${(ratio * 100).toFixed(1)}%`;
    gauge.classList.toggle("is-over", done > target);
    gauge.classList.toggle("is-full", target > 0 && done === target);

    const note = document.getElementById("studio-gauge-note");
    if (!note) return;
    if (done > target) {
        note.textContent = `Dépassement de ${formatStudioHours(done - target)} h par rapport à l'objectif.`;
    } else if (target > 0 && done === target) {
        note.textContent = "Objectif atteint : la semaine de ce professeur est complète.";
    } else {
        note.textContent = `Reste ${formatStudioHours(target - done)} h à répartir.`;
    }
}
"""

FUNCS["renderStudioCourses"] = r"""
function renderStudioCourses() {
    const list = document.getElementById("studio-course-list");
    if (!list) return;
    const teacher = studioTeacher();
    if (!teacher) {
        list.innerHTML = "";
        return;
    }

    const courses = appData.courses.filter((course) =>
        (course.teacherIds || []).includes(teacher.id),
    );
    if (!courses.length) {
        list.innerHTML = emptyStateHtml(
            "i-book",
            "Aucun cours",
            "Ajoutez la première matière de ce professeur avec le formulaire ci-dessus.",
        );
        return;
    }

    list.innerHTML = courses
        .map((course) => {
            const classLabel = getClassInfo(course.classId) || "Classe non définie";
            const room = appData.rooms.find((item) => item.id === course.roomId);
            const weekly =
                slotsToDuration(course.duration || SLOTS_PER_HOUR) *
                (course.frequency || 1);
            return `<article class="course-card">
                <div class="course-card__top">
                    <h4 class="course-card__name">${escapeHtml(course.name)}</h4>
                    <div class="course-card__actions">
                        <button class="icon-btn icon-btn--sm" type="button" onclick="editCourse('${course.id}')" aria-label="Modifier ${escapeHtml(course.name)}" title="Modifier">${icon("i-pencil")}</button>
                        <button class="icon-btn icon-btn--sm icon-btn--danger" type="button" onclick="removeStudioCourse('${course.id}')" aria-label="Supprimer ${escapeHtml(course.name)}" title="Supprimer">${icon("i-trash")}</button>
                    </div>
                </div>
                <div class="meta">
                    <span class="meta__item">${icon("i-cap")}${escapeHtml(classLabel)}</span>
                    <span class="meta__item">${icon("i-clock")}${escapeHtml(formatCourseDuration(course))}</span>
                    <span class="meta__item">${icon("i-rotate")}${course.frequency || 1}× / sem.</span>
                    <span class="meta__item">${icon("i-door")}${escapeHtml(room ? room.name : "Sans salle")}</span>
                    <span class="badge badge--hours">${formatStudioHours(weekly)} h / sem.</span>
                </div>
            </article>`;
        })
        .join("");
}
"""

FUNCS["refreshStudio"] = r"""
function refreshStudio() {
    renderStudioRail();
    renderStudioCourses();
    updateStudioGauge();
    updateStudioPreview();
}
"""

FUNCS["updateStudioHoursTarget"] = r"""
function updateStudioHoursTarget(value) {
    const teacher = studioTeacher();
    if (!teacher) return;
    const parsed = Number(String(value).replace(",", "."));
    const target = Number.isFinite(parsed)
        ? Math.min(Math.max(parsed, 0), 45)
        : STUDIO_DEFAULT_HOURS;
    teacher.weeklyHours = target;
    saveData();
    updateStudioGauge();
    renderStudioRail();
}
"""

FUNCS["studioAddCourse"] = r"""
function studioAddCourse() {
    const teacher = studioTeacher();
    const input = document.getElementById("studio-course-name");
    const name = input ? input.value.trim() : "";

    if (!teacher) {
        showNotification("Choisissez d'abord un professeur", "warning");
        return;
    }
    if (!name) {
        showNotification("Indiquez la matière du cours", "warning");
        if (input) input.focus();
        return;
    }
    if (!studioClassId) {
        showNotification("Choisissez une classe", "warning");
        return;
    }
    const roomSelect = document.getElementById("studio-room");
    const roomId = roomSelect && roomSelect.value ? roomSelect.value : null;

    appData.courses.push({
        id: "course-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6),
        name,
        teacherIds: [teacher.id],
        classId: studioClassId,
        roomId,
        duration: studioDuration,
        frequency: studioFrequency,
        priority: 2,
        constraints: "",
        weekType: "Toutes",
        fixedDay: null,
        fixedStartSlot: null,
        scheduled: false,
    });

    if (input) {
        input.value = "";
        input.focus();
    }
    saveData();
    updateCourseList();
    updateScheduleDisplay();
    refreshStudio();
    showNotification(`« ${name} » ajouté à ${teacher.name}`);
}
"""

FUNCS["removeStudioCourse"] = r"""
function removeStudioCourse(id) {
    const course = appData.courses.find((item) => item.id === id);
    if (!course) return;
    showConfirm(
        `Supprimer « ${course.name} » ?`,
        "Le cours sera retiré du catalogue et de tous les créneaux des semaines A et B.",
        () => {
            appData.courses = appData.courses.filter((item) => item.id !== id);
            [appData.schedule, appData.scheduleA, appData.scheduleB].forEach(
                (schedule) => removeCourseFromSchedule(schedule, id),
            );
            saveData();
            updateCourseList();
            updateScheduleDisplay();
            refreshStudio();
            showNotification(`Cours « ${course.name} » supprimé`);
        },
        "Supprimer",
    );
}
"""

FUNCS["addTeacherFromStudio"] = r"""
function addTeacherFromStudio() {
    const input = document.getElementById("studio-new-teacher");
    const name = input ? input.value.trim() : "";
    if (!name) {
        if (input) input.focus();
        return;
    }
    if (
        appData.teachers.some(
            (teacher) => teacher.name.toLowerCase() === name.toLowerCase(),
        )
    ) {
        showNotification("Ce professeur existe déjà", "warning");
        return;
    }

    const teacher = { id: "teacher-" + Date.now(), name, weeklyHours: STUDIO_DEFAULT_HOURS };
    appData.teachers.push(teacher);
    studioTeacherId = teacher.id;
    try {
        localStorage.setItem("flowEdtStudioTeacher", teacher.id);
    } catch (error) {
        /* stockage indisponible */
    }
    if (input) input.value = "";
    updateAllUI();
    saveData();
    showNotification(`${name} ajouté`);
    const courseInput = document.getElementById("studio-course-name");
    if (courseInput) courseInput.focus();
}
"""

FUNCS["openTeacherSchedule"] = r"""
function openTeacherSchedule() {
    const teacher = studioTeacher();
    if (!teacher) {
        showNotification("Choisissez d'abord un professeur", "warning");
        return;
    }

    switchTab("schedule");

    const typeSelect = document.getElementById("schedule-type-selector");
    const itemSelect = document.getElementById("schedule-item-selector");
    if (!typeSelect || !itemSelect) return;

    typeSelect.value = "teacher";
    updateScheduleTypeSelector();
    itemSelect.value = teacher.id;
    currentSelectedItem = { type: "teacher", id: teacher.id };
    updateFilterChip();
    updateScheduleDisplay();
    showNotification(`Planning filtré sur ${teacher.name}`, "info");
}
"""
