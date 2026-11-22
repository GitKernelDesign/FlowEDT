#!/usr/bin/env python3
"""Tests fonctionnels Playwright pour Flow-EDT."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
URL = (ROOT.parent / "index.html").as_uri()
SEED = (ROOT / "shot.py").read_text().split('SEED = r"""')[1].split('"""')[0]
HTML = (ROOT.parent / "index.html").read_text(encoding="utf-8")

LEGACY_DEMO = {
    "teachers": [{"id": f"t{i}", "name": f"PROF {i}"} for i in range(1, 16)],
    "rooms": [{"id": f"r{i}", "name": f"SALLE {i}", "capacity": 30} for i in range(1, 17)],
    "classes": [{"id": f"c{i}", "name": f"CLASSE {i}", "students": 30} for i in range(1, 9)],
    "halfGroups": [],
    "classGroups": [],
    "courses": [],
    "scheduleA": {},
    "scheduleB": {},
    "schedule": {},
    "forbiddenSlots": [],
    "cantineSlots": [],
    "lastSave": None,
    "schemaVersion": 2,
}

PEEK_SEED = r"""
() => {
  // Jeu dédié : une cellule à deux cours (cartes empilées) et une à trois
  // cours (carte + badge), pour vérifier le décalage et l'aperçu.
  const t = (id, name) => ({ id, name });
  const r = (id, name) => ({ id, name, capacity: 30 });
  const c = (id, name) => ({ id, name, students: 28 });
  appData.teachers = [t('t1','MARTIN'), t('t2','BERNARD'), t('t3','DUBOIS'), t('t4','THOMAS')];
  appData.rooms = [r('r1','Salle 101'), r('r2','Salle 102'), r('r3','Salle 103')];
  appData.classes = [c('k1','4A'), c('k2','4B'), c('k3','5A')];
  appData.halfGroups = []; appData.classGroups = [];
  const mk = (id, name, teacherIds, classId, roomId, duration) => ({
    id, name, teacherIds, classId, roomId, duration,
    frequency: 1, priority: 2, constraints: '', weekType: 'Toutes',
    fixedDay: null, fixedStartSlot: null, scheduled: false,
  });
  appData.courses = [
    mk('m1','Mathématiques',['t1'],'k1','r1',4),
    mk('m2','Français',['t2'],'k2','r2',4),
    mk('m3','Histoire-Géographie',['t3'],'k3','r3',2),
    mk('m4','Anglais',['t4'],'k1','r2',2),
    mk('m5','SVT',['t2'],'k2','r1',2),
    mk('m6','Musique',['t4'],'k3','r2',2),
  ];
  appData.cantineSlots = []; appData.forbiddenSlots = [];
  appData.scheduleA = {}; appData.scheduleB = {};
  const two = [
    { courseId: 'm1', roomId: 'r1', occId: 'p1' },
    { courseId: 'm2', roomId: 'r2', occId: 'p2' },
  ];
  const three = [
    { courseId: 'm3', roomId: 'r3', occId: 'p3' },
    { courseId: 'm5', roomId: 'r1', occId: 'p5' },
    { courseId: 'm6', roomId: 'r2', occId: 'p6' },
  ];
  appData.scheduleA.Lundi = {};
  ['8:00-8:30', '8:30-9:00', '9:00-9:30', '9:30-10:00'].forEach((key, index) => {
    appData.scheduleA.Lundi[key] = two.map((entry) => ({ ...entry, slotIndex: index }));
  });
  appData.scheduleA.Lundi['10:00-10:30'] = [
    { courseId: 'm4', roomId: 'r2', slotIndex: 0, occId: 'p4' },
  ];
  appData.scheduleA.Mardi = {};
  ['8:00-8:30', '8:30-9:00'].forEach((key, index) => {
    appData.scheduleA.Mardi[key] = three.map((entry) => ({ ...entry, slotIndex: index }));
  });
  saveData(); updateAllUI(); updateScheduleDisplay();
}
"""

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="fr-FR")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append("console:" + m.text) if m.type == "error" else None)
        page.goto(URL, wait_until="load")
        page.wait_for_timeout(400)

        # ---------- 0. établissement vierge au premier lancement ----------
        start = HTML.index("function createDefaultData()")
        default_body = HTML[start : HTML.index("initializeEmptySchedule();", start)]
        check(
            "aucune ressource livrée par défaut",
            "{ id:" not in default_body and "teachers: []," in default_body,
        )
        check(
            "aucun prof ni élève prérempli dans le fichier",
            all(
                word not in HTML
                for word in ("FERTE", "BLANCO", "DEREGNAUCOURT", "Gymnase", "2AMA")
            ),
        )
        state = page.evaluate(
            "() => [appData.teachers.length, appData.rooms.length, appData.classes.length, appData.courses.length]"
        )
        check("données vides au démarrage", state == [0, 0, 0, 0], str(state))
        check(
            "guide d'accueil sur le planning",
            page.is_visible("#schedule-callout")
            and "Votre établissement est vide" in page.inner_text("#schedule-callout"),
        )
        check(
            "grille masquée quand tout est vide",
            page.evaluate(
                "() => document.querySelector('.week-area').hidden"
                " && document.getElementById('day-tabs').hidden"
                " && document.querySelector('#schedule .toolbar').hidden"
            ),
        )
        check(
            "pastille de sauvegarde neutre",
            page.inner_text("#save-indicator").strip() == "Aucune donnée"
            and page.evaluate("document.getElementById('save-indicator').classList.contains('is-idle')"),
            page.inner_text("#save-indicator"),
        )
        page.evaluate("autoSave()")
        page.wait_for_timeout(100)
        check(
            "aucune sauvegarde vide au démarrage",
            page.evaluate("localStorage.getItem('emploiDuTemps') === null"),
        )
        page.evaluate("switchTab('resources')")
        page.wait_for_timeout(250)
        empties = page.eval_on_selector_all("#resources .empty", "els => els.length")
        check("états vides des ressources", empties >= 5, f"{empties} blocs")
        check(
            "compteurs de ressources à zéro",
            page.inner_text("#resource-summary").replace("\n", " ").strip().lower()
            == "0 professeur 0 salle 0 classe",
            page.inner_text("#resource-summary"),
        )

        # ancien jeu de démonstration : purgé s'il n'a jamais été retouché
        page.evaluate(
            "data => localStorage.setItem('emploiDuTemps', JSON.stringify(data))",
            LEGACY_DEMO,
        )
        page.reload(wait_until="load")
        page.wait_for_timeout(500)
        check(
            "ancienne démo purgée au chargement",
            page.evaluate("appData.teachers.length === 0 && appData.classes.length === 0"),
        )
        kept = dict(LEGACY_DEMO, courses=[{"id": "k1", "name": "COURS PERSO", "teacherIds": ["t1"], "classId": "c1"}])
        page.evaluate(
            "data => localStorage.setItem('emploiDuTemps', JSON.stringify(data))",
            kept,
        )
        page.reload(wait_until="load")
        page.wait_for_timeout(500)
        check(
            "données retouchées conservées",
            page.evaluate("appData.teachers.length === 15 && appData.courses.length === 1"),
        )

        page.evaluate("localStorage.clear()")
        page.reload(wait_until="load")
        page.wait_for_timeout(500)
        page.evaluate(SEED)
        page.wait_for_timeout(400)
        check(
            "grille rendue dès qu'il y a des données",
            page.evaluate(
                "!document.querySelector('.week-area').hidden"
                " && !document.querySelector('#schedule .toolbar').hidden"
                " && document.getElementById('schedule-callout').hidden"
            ),
        )

        # ---------- 1. ressources ----------
        page.evaluate("switchTab('resources')")
        page.wait_for_timeout(250)
        before = page.eval_on_selector_all("#teacher-list .res-item", "els => els.length")
        page.fill("#new-teacher", "PROF TEST")
        page.click("form.add-row button[type=submit]")
        page.wait_for_timeout(200)
        after = page.eval_on_selector_all("#teacher-list .res-item", "els => els.length")
        check("ajout professeur", after == before + 1, f"{before} → {after}")

        page.fill("#new-room", "SALLE TEST")
        page.fill("#room-capacity", "24")
        page.click("form.add-row:has(#new-room) button[type=submit]")
        page.wait_for_timeout(200)
        check("ajout salle", page.evaluate("appData.rooms.some(r => r.name === 'SALLE TEST' && r.capacity === 24)"))

        page.fill("#new-class", "CLASSE TEST")
        page.fill("#class-students", "30")
        page.click("form.add-row:has(#new-class) button[type=submit]")
        page.wait_for_timeout(200)
        check("ajout classe", page.evaluate("appData.classes.some(c => c.name === 'CLASSE TEST')"))

        # ---------- 2. création d'un cours ----------
        page.evaluate("switchTab('courses')")
        page.wait_for_timeout(250)
        page.click("#course-panel-toggle")
        page.wait_for_timeout(300)
        check("formulaire cours visible", page.is_visible("#course-name"))
        page.fill("#course-name", "COURS TEST")
        page.click("#teacher-multi-select")
        page.wait_for_timeout(200)
        page.evaluate("document.getElementById('teacher-t1').click()")
        page.wait_for_timeout(150)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        page.select_option("#course-class", index=1)
        page.select_option("#course-duration", index=2)
        page.click("#course-submit")
        page.wait_for_timeout(500)
        check("cours créé", page.evaluate("appData.courses.some(c => c.name === 'COURS TEST')"))

        # ---------- 3. édition d'un cours ----------
        page.evaluate("openCoursePanel(true)")
        page.wait_for_timeout(300)
        check("panneau d'édition ouvert", page.is_visible("#course-name"))
        page.evaluate("editCourse(appData.courses.find(c => c.name === 'COURS TEST').id)")
        page.wait_for_timeout(300)
        check("bouton Mettre à jour", "Mettre" in (page.inner_text("#course-submit") or ""))
        check("bouton confirmer visible (édition)", page.evaluate("document.getElementById('modal-confirm').style.display !== 'none'"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # ---------- 4. détail d'un créneau ----------
        page.evaluate("switchTab('schedule')")
        page.wait_for_timeout(300)
        page.evaluate("showCourseDetails('Lundi', TIME_SLOTS[0], appData.schedule['Lundi'][TIME_SLOTS[0]])")
        page.wait_for_timeout(300)
        check("fiche détail (dl)", page.eval_on_selector_all("#modal-body .detail__grid", "els => els.length") > 0)
        check("bouton confirmer masqué (détail)", page.evaluate("document.getElementById('modal-confirm').style.display === 'none'"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        page.evaluate("editTeacher(appData.teachers[0].id)")
        page.wait_for_timeout(300)
        check("bouton confirmer restauré après détail", page.evaluate("document.getElementById('modal-confirm').style.display !== 'none'"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # ---------- 5. filtre professeur ----------
        page.evaluate("toggleScheduleFilters(true)")
        page.wait_for_timeout(150)
        page.select_option("#schedule-type-selector", "teacher")
        page.wait_for_timeout(200)
        page.select_option("#schedule-item-selector", index=1)
        page.wait_for_timeout(400)
        check("puce de filtre active", page.evaluate("!document.getElementById('active-filter').hidden"))
        rows = page.evaluate("[...document.querySelectorAll('#schedule table.timetable')].filter(t => t.offsetParent !== null).reduce((n, t) => n + t.querySelectorAll('tbody tr').length, 0)")
        check("table filtrée rendue", rows > 0, f"{rows} lignes")
        page.evaluate("clearScheduleFilter()")
        page.wait_for_timeout(300)
        check("filtre retiré", page.evaluate("document.getElementById('active-filter').hidden"))

        # ---------- 6. semaines ----------
        page.evaluate("switchWeekView('B')")
        page.wait_for_timeout(250)
        check("semaine B active", page.evaluate("document.querySelector('[data-week=\"B\"]').classList.contains('active')"))
        page.evaluate("switchWeekView('both')")
        page.wait_for_timeout(250)
        grids = page.evaluate("[...document.querySelectorAll('#schedule table.timetable')].filter(t => t.offsetParent !== null).length")
        check("vue A+B affiche 2 grilles", grids >= 2, f"{grids} grilles")
        page.evaluate("switchWeekView('A')")
        page.wait_for_timeout(250)

        # ---------- 7. thème ----------
        page.evaluate("toggleTheme()")
        page.wait_for_timeout(300)
        check("thème sombre", page.evaluate("document.documentElement.dataset.theme === 'dark'"))
        page.screenshot(path=str(ROOT / "dark-mobile-schedule.png"), full_page=True)
        page.evaluate("switchTab('resources')")
        page.wait_for_timeout(300)
        page.screenshot(path=str(ROOT / "dark-mobile-resources.png"), full_page=True)
        page.evaluate("toggleTheme()")
        page.wait_for_timeout(200)

        # ---------- 8. modale de confirmation ----------
        page.evaluate("switchTab('export')")
        page.wait_for_timeout(250)
        page.evaluate("document.querySelector('[onclick*=\"confirmReset\"]').click()")
        page.wait_for_timeout(300)
        check("modale reset ouverte", page.evaluate("document.getElementById('confirm-modal').classList.contains('active')"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        check("modale fermée par Échap", page.evaluate("!document.getElementById('confirm-modal').classList.contains('active')"))
        check("données conservées", page.evaluate("appData.teachers.length > 10"))

        # ---------- 9. navigation basse ----------
        for tab, label in [("resources", "Ressources"), ("courses", "Cours"), ("schedule", "Planning"), ("export", "Sauvegarde")]:
            page.evaluate(f"switchTab('{tab}')")
            page.wait_for_timeout(150)
            ok = page.evaluate(f"document.getElementById('{tab}').classList.contains('active')")
            check(f"onglet {label}", ok)

        # ---------- 10. piège à focus des feuilles ----------
        page.evaluate("switchTab('schedule')")
        page.wait_for_timeout(200)
        page.evaluate("showCourseDetails('Lundi', TIME_SLOTS[2], appData.schedule['Lundi'][TIME_SLOTS[2]])")
        page.wait_for_timeout(300)
        page.click("#edit-modal", position={"x": 5, "y": 5})
        page.wait_for_timeout(250)
        check("fermeture par clic sur le fond", page.evaluate("!document.getElementById('edit-modal').classList.contains('active')"))

        # ---------- 11. menu burger (mobile) ----------
        page.evaluate("switchTab('schedule')")
        page.wait_for_timeout(200)
        check("bouton burger visible", page.is_visible("#menu-toggle"))
        check(
            "menu refermé par défaut",
            page.evaluate("!document.getElementById('app-menu').classList.contains('active')"),
        )
        page.click("#menu-toggle")
        page.wait_for_timeout(350)
        check(
            "menu ouvert",
            page.evaluate("document.getElementById('app-menu').classList.contains('active')"),
        )
        check("aria-expanded à true", page.get_attribute("#menu-toggle", "aria-expanded") == "true")

        nav_mobile = page.eval_on_selector_all(".menu-nav__item", "els => els.map(e => e.dataset.tab)")
        nav_desktop = page.eval_on_selector_all(".nav__item", "els => els.map(e => e.dataset.tab)")
        check(
            "parité navigation desktop / mobile",
            nav_mobile == nav_desktop,
            f"{nav_mobile}",
        )
        check(
            "statut de sauvegarde présent dans le menu",
            page.inner_text("#menu-save-text").strip().startswith("Enregistré"),
            page.inner_text("#menu-save-text"),
        )
        check("réglages thème + compacité dans le menu", page.is_visible("#theme-switch") and page.is_visible("#density-switch"))

        page.click('.menu-nav__item[data-tab="courses"]')
        page.wait_for_timeout(400)
        check(
            "navigation depuis le menu",
            page.evaluate("document.querySelector('.tab-content.active').id === 'courses'"),
        )
        check(
            "menu refermé après navigation",
            page.evaluate("!document.getElementById('app-menu').classList.contains('active')"),
        )

        page.click("#menu-toggle")
        page.wait_for_timeout(300)
        check("compacité masquée hors planning (mobile)", not page.is_visible("#density-switch"))
        check("thème toujours réglable hors planning", page.is_visible("#theme-switch"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        page.evaluate("switchTab('schedule')")
        page.wait_for_timeout(250)

        page.click("#menu-toggle")
        page.wait_for_timeout(300)
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        check(
            "menu fermé par Échap",
            page.evaluate("!document.getElementById('app-menu').classList.contains('active')"),
        )
        check("aria-expanded remis à false", page.get_attribute("#menu-toggle", "aria-expanded") == "false")

        # ---------- 12. affichage compact ----------
        page.evaluate("switchTab('schedule')")
        page.wait_for_timeout(350)
        measure = (
            "[...document.querySelectorAll('#schedule .slot-course')]"
            ".map(el => el.getBoundingClientRect().height)"
            ".filter(h => h > 0)[0] || 0"
        )
        height_before = page.evaluate(measure)
        page.click("#menu-toggle")
        page.wait_for_timeout(300)
        check(
            "canapé affiché en mode confort",
            page.evaluate(
                "getComputedStyle(document.querySelector('#density-switch .icon--sofa')).display !== 'none'"
                " && getComputedStyle(document.querySelector('#density-switch .icon--compact')).display === 'none'"
            ),
        )
        page.click("#density-switch")
        page.wait_for_timeout(350)
        check(
            "mode compact actif",
            page.evaluate("document.documentElement.dataset.density === 'compact'"),
        )
        check("interrupteur compact coché", page.get_attribute("#density-switch", "aria-checked") == "true")
        check(
            "icône de grille en mode compact",
            page.evaluate(
                "getComputedStyle(document.querySelector('#density-switch .icon--compact')).display !== 'none'"
                " && getComputedStyle(document.querySelector('#density-switch .icon--sofa')).display === 'none'"
            ),
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        height_after = page.evaluate(measure)
        check(
            "cartes de cours plus compactes",
            height_after < height_before,
            f"{height_before:.0f} → {height_after:.0f} px",
        )
        page.reload()
        page.wait_for_timeout(600)
        check(
            "compacité conservée au rechargement",
            page.evaluate("document.documentElement.dataset.density === 'compact'"),
        )
        check(
            "bouton compacité reflète l'état",
            page.evaluate("document.getElementById('density-toggle').getAttribute('aria-pressed') === 'true'"),
        )
        page.evaluate("applyDensity('confort')")
        page.wait_for_timeout(150)

        # ---------- 12b. filtres du planning : non-régression ----------
        # Chaque test compare la grille rendue à une spécification écrite ici,
        # indépendante du code de production.
        FILTER_SPEC = """
        (payload) => {
            const { type, id } = payload;
            const classesOf = (value) => {
                const group = (appData.classGroups || []).find((g) => g.id === value);
                if (group) return group.classIds || [];
                const halfGroup = (appData.halfGroups || []).find((h) => h.id === value);
                if (halfGroup) return [halfGroup.classId];
                return [value];
            };
            const covers = (course, placement) => {
                if (type === 'teacher') return (course.teacherIds || []).includes(id);
                if (type === 'room') return (placement.roomId || course.roomId) === id;
                const target = classesOf(id);
                return [course.classId].concat(classesOf(course.classId))
                    .some((key) => target.includes(key));
            };
            const halfIds = (appData.halfGroups || [])
                .filter((h) => h.classId === id)
                .map((h) => h.id);
            const schedule = getCurrentSchedule();
            const expected = {};
            const allowed = new Set();
            let starts = 0;
            let hours = 0;
            let halfHit = false;
            DAYS.forEach((day) => {
                TIME_SLOTS.forEach((slot) => {
                    const value = schedule[day] && schedule[day][slot];
                    if (!value) return;
                    const kept = (Array.isArray(value) ? value : [value]).filter((placement) => {
                        const course = appData.courses.find((c) => c.id === placement.courseId);
                        return course ? covers(course, placement) : false;
                    });
                    if (!kept.length) return;
                    expected[`${day}|${slot}`] = kept.length;
                    kept.forEach((placement) => {
                        const course = appData.courses.find((c) => c.id === placement.courseId);
                        allowed.add(course.name);
                        if (halfIds.includes(course.classId)) halfHit = true;
                        if (!placement.slotIndex) {
                            starts += 1;
                            hours += (course.duration || 2) / 2;
                        }
                    });
                });
            });
            const filtered = filterScheduleBySelection(schedule);
            const actual = {};
            DAYS.forEach((day) => {
                TIME_SLOTS.forEach((slot) => {
                    const value = filtered[day] && filtered[day][slot];
                    if (!value) return;
                    actual[`${day}|${slot}`] = (Array.isArray(value) ? value : [value]).length;
                });
            });
            const shown = [...document.querySelectorAll('#schedule table.timetable')]
                .filter((table) => table.offsetParent !== null)
                .flatMap((table) => [...table.querySelectorAll('.slot-course__name')])
                .map((element) => element.textContent.trim());
            const foreign = [...new Set(shown.filter((name) => !allowed.has(name)))];
            return { expected, actual, starts, hours, halfHit, foreign, shown: shown.length };
        }
        """

        def pick_filter(kind, name):
            page.evaluate("clearScheduleFilter()")
            page.wait_for_timeout(120)
            page.evaluate("toggleScheduleFilters(true)")
            page.wait_for_timeout(120)
            page.select_option("#schedule-type-selector", kind)
            page.wait_for_timeout(180)
            fid = page.evaluate(
                """([kind, name]) => {
                    const source = kind === 'teacher' ? appData.teachers
                        : kind === 'room' ? appData.rooms
                        : [...appData.classes, ...(appData.halfGroups || []), ...(appData.classGroups || [])];
                    const found = source.find((item) => item.name === name);
                    const select = document.getElementById('schedule-item-selector');
                    select.value = found.id;
                    filterScheduleByItem();
                    toggleScheduleFilters(false);
                    return found.id;
                }""",
                [kind, name],
            )
            page.wait_for_timeout(400)
            return fid

        page.evaluate("switchWeekView('A')")
        page.wait_for_timeout(300)

        fid = pick_filter("teacher", "MARTIN")
        spec = page.evaluate(FILTER_SPEC, {"type": "teacher", "id": fid})
        check(
            "filtre professeur : créneaux conformes à la sélection",
            spec["expected"] == spec["actual"],
            f'{len(spec["actual"])} créneaux',
        )
        check(
            "filtre professeur : aucune carte d'un autre professeur",
            spec["foreign"] == [],
            ", ".join(spec["foreign"][:4]),
        )
        check("filtre professeur : grille non vide", spec["shown"] > 0, f'{spec["shown"]} cartes')
        check(
            "filtre professeur : compteurs alignés sur la grille",
            page.inner_text("#total-courses").strip() == str(spec["starts"])
            and page.inner_text("#total-hours").strip() == f'{spec["hours"]:g}',
            f'{page.inner_text("#total-courses").strip()} cours / '
            f'{page.inner_text("#total-hours").strip()} h '
            f'(attendu {spec["starts"]} / {spec["hours"]:g})',
        )
        check(
            "filtre professeur : conflits recalculés",
            page.inner_text("#conflicts").strip() == "0"
            and not page.evaluate("document.getElementById('stat-conflicts').classList.contains('conflict')"),
            page.inner_text("#conflicts"),
        )
        check(
            "légende limitée aux professeurs affichés",
            page.eval_on_selector_all("#legend-items .legend__item", "els => els.map(e => e.textContent.trim())") == ["MARTIN"],
        )

        # clic sur un créneau filtré : la fiche doit lister tous les cours
        clicked = page.evaluate(
            """() => {
                const cell = [...document.querySelectorAll('#schedule table.timetable')]
                    .filter((table) => table.offsetParent !== null)
                    .flatMap((table) => [...table.querySelectorAll('td.slot')])
                    .find((td) => {
                        const value = (appData.scheduleA[td.dataset.day] || {})[td.dataset.slot];
                        return value && (Array.isArray(value) ? value : [value]).length >= 2;
                    });
                if (!cell) return null;
                const value = appData.scheduleA[cell.dataset.day][cell.dataset.slot];
                const list = Array.isArray(value) ? value : [value];
                const teachers = [...new Set(list.flatMap((placement) => {
                    const course = appData.courses.find((c) => c.id === placement.courseId);
                    return (course.teacherIds || []).map((id) => {
                        const teacher = appData.teachers.find((t) => t.id === id);
                        return teacher ? teacher.name : '';
                    });
                }).filter(Boolean))];
                const courses = [...new Set(list.map((placement) => {
                    const course = appData.courses.find((c) => c.id === placement.courseId);
                    return course ? course.name : '';
                }).filter(Boolean))];
                cell.click();
                return { teachers, courses, count: list.length };
            }"""
        )
        page.wait_for_timeout(400)
        modal_text = page.inner_text("#modal-body")
        check(
            "créneau filtré : fiche complète (tous les cours)",
            clicked is not None
            and page.eval_on_selector_all("#modal-body .detail", "els => els.length") == clicked["count"]
            and all(name in modal_text for name in clicked["teachers"]),
            f'{len(clicked["courses"])} cours, {len(clicked["teachers"])} professeurs',
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)

        fid = pick_filter("class", "1 G1")
        spec = page.evaluate(FILTER_SPEC, {"type": "class", "id": fid})
        check(
            "filtre classe : créneaux conformes à la sélection",
            spec["expected"] == spec["actual"],
            f'{len(spec["actual"])} créneaux',
        )
        check("filtre classe : demi-groupes inclus", spec["halfHit"])
        check(
            "filtre classe : aucune carte étrangère",
            spec["foreign"] == [],
            ", ".join(spec["foreign"][:4]),
        )

        fid = pick_filter("class", "Terminales")
        spec = page.evaluate(FILTER_SPEC, {"type": "class", "id": fid})
        check(
            "filtre groupe de classes : grille non vide",
            spec["shown"] > 0 and spec["starts"] > 0,
            f'{spec["shown"]} cartes',
        )
        check(
            "filtre groupe de classes : créneaux conformes",
            spec["expected"] == spec["actual"],
            f'{len(spec["actual"])} créneaux',
        )
        check(
            "filtre groupe de classes : aucune carte étrangère",
            spec["foreign"] == [],
            ", ".join(spec["foreign"][:4]),
        )

        fid = pick_filter("room", "Salle 1")
        spec = page.evaluate(FILTER_SPEC, {"type": "room", "id": fid})
        check(
            "filtre salle : créneaux conformes à la sélection",
            spec["expected"] == spec["actual"],
            f'{len(spec["actual"])} créneaux',
        )
        check(
            "filtre salle : aucune carte étrangère",
            spec["foreign"] == [],
            ", ".join(spec["foreign"][:4]),
        )
        check(
            "filtre salle : carte des heures masquée",
            page.evaluate("document.getElementById('stat-hours').hidden"),
        )

        fid = pick_filter("teacher", "MOREAU")
        check(
            "filtre sans résultat : message dédié",
            page.is_visible("#schedule-callout")
            and "Aucun cours pour MOREAU" in page.inner_text("#schedule-callout"),
            page.inner_text("#schedule-callout").replace("\n", " ")[:80],
        )
        page.click("#schedule-callout button")
        page.wait_for_timeout(400)
        check(
            "filtre sans résultat : bouton de retrait",
            page.evaluate("getCurrentFilterFn() === null"),
        )

        # hauteur de ligne : la grille ne doit plus se déformer
        row_heights = page.eval_on_selector_all(
            "#schedule table.timetable:not([hidden]) tbody td.slot",
            "els => els.filter(e => e.offsetParent !== null).map(e => Math.round(e.getBoundingClientRect().height))",
        )
        row_heights = [height for height in row_heights if height > 0]
        check(
            "lignes du planning de hauteur constante",
            bool(row_heights) and max(row_heights) - min(row_heights) <= 1 and min(row_heights) >= 44,
            f"{min(row_heights)}–{max(row_heights)} px sur {len(row_heights)} cellules",
        )
        page.evaluate("applyDensity('compact')")
        page.wait_for_timeout(300)
        compact_heights = page.eval_on_selector_all(
            "#schedule table.timetable:not([hidden]) tbody td.slot",
            "els => els.filter(e => e.offsetParent !== null).map(e => Math.round(e.getBoundingClientRect().height))",
        )
        compact_heights = [height for height in compact_heights if height > 0]
        check(
            "lignes compactes homogènes",
            bool(compact_heights)
            and max(compact_heights) - min(compact_heights) <= 1
            and max(compact_heights) < max(row_heights),
            f"{min(compact_heights)}–{max(compact_heights)} px",
        )
        page.evaluate("applyDensity('confort')")
        page.wait_for_timeout(250)

        # ---------- 12c. onglet Professeurs (studio) ----------
        page.evaluate("switchTab('teachers')")
        page.wait_for_timeout(400)
        check(
            "onglet Professeurs accessible",
            page.evaluate("document.querySelector('.tab-content.active').id === 'teachers'"),
        )
        rail_count = page.eval_on_selector_all(
            "#studio-teacher-list .studio__rail-item", "els => els.length"
        )
        check(
            "liste des professeurs alimentée",
            rail_count == page.evaluate("appData.teachers.length")
            and rail_count > 10,
            f"{rail_count} entrées",
        )
        check(
            "premier professeur sélectionné d'office",
            page.inner_text("#studio-name").strip() == "MARTIN"
            and page.evaluate("!document.getElementById('studio-body').hidden"),
        )

        page.click("#studio-teacher-list .studio__rail-item[data-teacher-id='t2']")
        page.wait_for_timeout(300)
        check(
            "sélection d'un professeur",
            page.inner_text("#studio-name").strip() == "BERNARD"
            and page.evaluate("document.querySelector('.studio__rail-item.is-active').dataset.teacherId === 't2'"),
        )

        page.fill("#studio-weekly-hours", "12")
        page.wait_for_timeout(350)
        check(
            "volume horaire enregistré",
            page.evaluate("appData.teachers.find(t => t.id === 't2').weeklyHours === 12"),
        )
        check(
            "jauge alignée sur l'objectif",
            page.inner_text("#studio-hours-state").strip() == "sur 12 h"
            and page.inner_text("#studio-gauge-note").strip() == "Reste 8 h à répartir.",
            page.inner_text("#studio-gauge-note").strip(),
        )

        page.fill("#studio-course-name", "SVT")
        page.click("#studio-classes .chip[data-class-id='c4']")
        page.click("#studio-duration button[data-value='4']")
        page.click("#studio-frequency button[data-value='2']")
        page.wait_for_timeout(250)
        check(
            "aperçu du cours avant ajout",
            "SVT" in page.inner_text("#studio-preview")
            and "4 h" in page.inner_text("#studio-preview"),
            page.inner_text("#studio-preview"),
        )

        page.click("#studio-add")
        page.wait_for_timeout(500)
        created = page.evaluate(
            "() => { const c = appData.courses.find(x => x.name === 'SVT');"
            " return c ? [c.teacherIds.join(','), c.classId, c.duration, c.frequency] : null; }"
        )
        check(
            "cours ajouté depuis le studio",
            created == ["t2", "c4", 4, 2],
            str(created),
        )
        check(
            "champ matière vidé pour enchaîner",
            page.input_value("#studio-course-name") == "",
        )
        check(
            "charge horaire recalculée",
            page.evaluate(
                "() => [document.getElementById('studio-hours-value').textContent.trim(),"
                " document.getElementById('studio-list-total').textContent.trim()]"
            )
            == ["8 h", "8 h / sem."],
            page.inner_text("#studio-gauge-note").strip(),
        )
        check(
            "cours listé sous le professeur",
            "SVT" in page.inner_text("#studio-course-list"),
        )

        page.click("#studio-course-list .course-card:last-child .icon-btn--danger")
        page.wait_for_timeout(350)
        check(
            "suppression confirmée depuis le studio",
            page.evaluate("document.getElementById('confirm-modal').classList.contains('active')")
            and "SVT" in page.inner_text("#confirm-title"),
        )
        page.click("#confirm-modal .sheet__foot .btn--danger")
        page.wait_for_timeout(450)
        check(
            "cours supprimé et charge ajustée",
            page.evaluate("!appData.courses.some(c => c.name === 'SVT')")
            and page.inner_text("#studio-hours-value").strip() == "4 h",
        )

        before_teachers = page.evaluate("appData.teachers.length")
        page.fill("#studio-new-teacher", "NOUVEAU PROF")
        page.click("#studio-new-teacher ~ button")
        page.wait_for_timeout(500)
        check(
            "professeur créé depuis le studio",
            page.evaluate("appData.teachers.length") == before_teachers + 1
            and page.inner_text("#studio-name").strip() == "NOUVEAU PROF",
            f"{before_teachers} → {page.evaluate('appData.teachers.length')}",
        )
        check(
            "compteur de professeurs à jour",
            page.inner_text("#studio-teacher-count").strip() == str(before_teachers + 1),
            page.inner_text("#studio-teacher-count").strip(),
        )

        page.click("#studio-planning")
        page.wait_for_timeout(600)
        check(
            "planning filtré sur le professeur",
            page.evaluate(
                "() => [document.querySelector('.tab-content.active').id,"
                " document.getElementById('schedule-type-selector').value,"
                " getCurrentFilterFn() !== null]"
            )
            == ["schedule", "teacher", True],
        )
        check(
            "puce de filtre nomme le professeur",
            "NOUVEAU PROF" in page.inner_text("#active-filter"),
        )

        page.reload(wait_until="load")
        page.wait_for_timeout(700)
        page.evaluate("switchTab('teachers')")
        page.wait_for_timeout(450)
        check(
            "sélection et heures conservées",
            page.inner_text("#studio-name").strip() == "NOUVEAU PROF"
            and page.evaluate("appData.teachers.find(t => t.id === 't2').weeklyHours === 12"),
        )

        nouveau_id = page.evaluate(
            "appData.teachers.find(t => t.name === 'NOUVEAU PROF').id"
        )
        page.evaluate("switchTab('resources')")
        page.wait_for_timeout(250)
        page.evaluate(f"deleteTeacher('{nouveau_id}')")
        page.wait_for_timeout(400)
        page.evaluate("switchTab('teachers')")
        page.wait_for_timeout(400)
        check(
            "studio : sélection retombée sur un professeur existant",
            page.evaluate("!appData.teachers.some(t => t.name === 'NOUVEAU PROF')")
            and page.inner_text("#studio-name").strip() != "NOUVEAU PROF"
            and page.evaluate("!document.getElementById('studio-body').hidden"),
            page.inner_text("#studio-name").strip(),
        )

        # établissement vierge : l'onglet doit guider au lieu de casser
        empty_ctx = browser.new_context(viewport={"width": 390, "height": 844})
        epage = empty_ctx.new_page()
        empty_errors = []
        epage.on("pageerror", lambda e: empty_errors.append(str(e)))
        epage.goto(URL, wait_until="load")
        epage.wait_for_timeout(400)
        epage.evaluate("localStorage.clear()")
        epage.reload(wait_until="load")
        epage.wait_for_timeout(500)
        epage.evaluate("switchTab('teachers')")
        epage.wait_for_timeout(350)
        check(
            "studio vide : message d'accueil",
            epage.is_visible("#studio-none")
            and "Aucun professeur" in epage.inner_text("#studio-none")
            and epage.evaluate("document.getElementById('studio-body').hidden"),
        )
        epage.fill("#studio-new-teacher", "PREMIER PROF")
        epage.click("#studio-new-teacher ~ button")
        epage.wait_for_timeout(500)
        check(
            "studio vide : création immédiate",
            epage.evaluate("appData.teachers.length === 1")
            and epage.inner_text("#studio-name").strip() == "PREMIER PROF"
            and not empty_errors,
            "; ".join(empty_errors[:2]),
        )
        empty_ctx.close()

        # ---------- 12d. salles : jamais deux classes au même endroit ----------
        ROOM_SCAN = """() => {
            const overlaps = [];
            const seen = {};
            ['A', 'B'].forEach((week) => {
                const schedule = week === 'A' ? appData.scheduleA : appData.scheduleB;
                DAYS.forEach((day) => TIME_SLOTS.forEach((slot) => {
                    const value = schedule[day] && schedule[day][slot];
                    if (!value) return;
                    const list = (Array.isArray(value) ? value : [value]).filter(Boolean);
                    list.forEach((sd) => {
                        seen[sd.courseId] = (seen[sd.courseId] || 0) + 1;
                    });
                    const byRoom = {};
                    list.forEach((sd) => {
                        if (!sd.roomId) return;
                        (byRoom[sd.roomId] = byRoom[sd.roomId] || []).push(sd.courseId);
                    });
                    Object.entries(byRoom).forEach(([roomId, ids]) => {
                        if (ids.length > 1) overlaps.push([week, day, slot, roomId, ids]);
                    });
                }));
            });
            return { overlaps, seen };
        }"""

        page.evaluate(SEED)
        page.wait_for_timeout(700)
        seed_rooms = page.evaluate(ROOM_SCAN)
        check(
            "génération auto : aucune salle occupée deux fois",
            seed_rooms["overlaps"] == [],
            str(seed_rooms["overlaps"][:2]),
        )

        # deux classes, une seule salle : les cours doivent se répartir
        spread = page.evaluate(
            """() => {
                appData.classes = [
                    { id: 'z1', name: 'Z1', students: 20 },
                    { id: 'z2', name: 'Z2', students: 20 },
                ];
                appData.halfGroups = [];
                appData.classGroups = [];
                appData.teachers = [
                    { id: 'p1', name: 'P1' },
                    { id: 'p2', name: 'P2' },
                ];
                appData.rooms = [{ id: 's1', name: 'Salle unique', capacity: 25 }];
                appData.forbiddenSlots = [];
                appData.cantineSlots = [];
                const make = (id, name, teacherId, classId) => ({
                    id, name, teacherIds: [teacherId], classId, roomId: 's1',
                    duration: 2, frequency: 1, priority: 2, constraints: '',
                    weekType: 'Toutes', fixedDay: null, fixedStartSlot: null,
                    scheduled: false,
                });
                appData.courses = [
                    make('a1', 'Cours A', 'p1', 'z1'),
                    make('a2', 'Cours B', 'p2', 'z2'),
                ];
                generateBasicSchedule();
                currentWeekView = 'A';
                appData.schedule = appData.scheduleA;
                return true;
            }"""
        )
        spread_rooms = page.evaluate(ROOM_SCAN)
        check(
            "une seule salle : les deux cours sont placés",
            set(spread_rooms["seen"]) == {"a1", "a2"}
            and all(count == 4 for count in spread_rooms["seen"].values()),
            f'{spread_rooms["seen"]} (2 créneaux × 2 semaines)',
        )
        check(
            "une seule salle : aucun chevauchement",
            spread_rooms["overlaps"] == [],
            str(spread_rooms["overlaps"][:2]),
        )

        # créneau imposé identique pour les deux cours : un seul est retenu
        fixed_rooms = page.evaluate(
            """() => {
                appData.courses.forEach((course) => {
                    course.fixedDay = 'Lundi';
                    course.fixedStartSlot = '0';
                });
                generateBasicSchedule();
                currentWeekView = 'A';
                appData.schedule = appData.scheduleA;
                return true;
            }"""
        )
        fixed_scan = page.evaluate(ROOM_SCAN)
        check(
            "créneau imposé : la salle n'accueille qu'un cours",
            fixed_scan["overlaps"] == [] and len(fixed_scan["seen"]) == 1,
            str(fixed_scan["seen"]),
        )

        # salle imposée déjà prise : bascule vers une autre salle libre
        fallback = page.evaluate(
            """() => {
                appData.courses[0].fixedDay = null;
                appData.courses[0].fixedStartSlot = null;
                appData.courses[1].fixedDay = null;
                appData.courses[1].fixedStartSlot = null;
                appData.rooms.push({ id: 's2', name: 'Salle 2', capacity: 25 });
                generateBasicSchedule();
                currentWeekView = 'A';
                appData.schedule = appData.scheduleA;
                initializeEmptySchedule();
                currentWeekView = 'A';
                appData.schedule = appData.scheduleA;
                const [first, second] = appData.courses;
                appData.scheduleA['Lundi'][TIME_SLOTS[0]] = {
                    courseId: first.id, roomId: 's1', duration: 2, slotIndex: 0,
                };
                const chosen = resolveRoomForPlacement(
                    second,
                    appData.scheduleA,
                    'Lundi',
                    0,
                    2,
                    second.roomId,
                );
                return { ok: chosen === 's2', chosen };
            }"""
        )
        check(
            "salle imposée occupée : repli sur une salle libre",
            fallback.get("ok") is True,
            str(fallback),
        )

        # ajout manuel : la salle occupée est refusée
        manual = page.evaluate(
            """() => {
                initializeEmptySchedule();
                currentWeekView = 'A';
                appData.schedule = appData.scheduleA;
                const day = 'Lundi';
                const slot = TIME_SLOTS[0];
                const [first, second] = appData.courses;
                appData.scheduleA[day][slot] = {
                    courseId: first.id, roomId: 's1', duration: 2, slotIndex: 0,
                };
                appData.scheduleA[day][TIME_SLOTS[1]] = {
                    courseId: first.id, roomId: 's1', duration: 2, slotIndex: 1,
                };
                const makeSelect = (id, options) => {
                    const select = document.createElement('select');
                    select.id = id;
                    options.forEach(([value, label]) => {
                        const option = document.createElement('option');
                        option.value = value;
                        option.textContent = label;
                        select.appendChild(option);
                    });
                    document.body.appendChild(select);
                    return select;
                };
                makeSelect('select-course-for-slot', [[second.id, 'Cours B']]);
                makeSelect('select-room-for-slot', [['s1', 'Salle unique']]);
                assignCourseToSlot(day, slot);
                const cell = appData.scheduleA[day][slot];
                const count = (Array.isArray(cell) ? cell : [cell]).filter(Boolean).length;
                const toast = document.querySelector(
                    '#toast-container .toast:last-child .toast__text',
                );
                return { count, toast: toast ? toast.textContent.trim() : '' };
            }"""
        )
        check(
            "ajout manuel : salle occupée refusée",
            manual["count"] == 1 and "Salle occupée" in manual["toast"],
            str(manual),
        )

        # le compteur de conflits signale une double occupation importée
        forged = page.evaluate(
            """() => {
                const day = 'Mardi';
                const slot = TIME_SLOTS[0];
                appData.scheduleA[day][slot] = [
                    { courseId: 'a1', roomId: 's1', duration: 2, slotIndex: 0 },
                    { courseId: 'a2', roomId: 's1', duration: 2, slotIndex: 0 },
                ];
                currentWeekView = 'A';
                updateConflictCount();
                const count = document.getElementById('conflicts').textContent.trim();
                appData.scheduleA[day][slot] = null;
                updateConflictCount();
                return { count, cleared: document.getElementById('conflicts').textContent.trim() };
            }"""
        )
        check(
            "compteur : double occupation signalée",
            forged["count"] not in ("0", "") and forged["cleared"] == "0",
            str(forged),
        )

        # ---------- 12e. génération automatique : options, verrou, qualité ----------
        GEN_SCAN = """(week) => {
            const schedule = week === 'A' ? appData.scheduleA : appData.scheduleB;
            const expected = appData.courses.filter((course) => {
                const type = course.weekType || 'Toutes';
                return type === 'Toutes' || type === 'both' || type === week;
            });
            const counts = {};
            const conflicts = { teacher: 0, class: 0, room: 0 };
            DAYS.forEach((day) => TIME_SLOTS.forEach((slot) => {
                const cell = schedule[day] && schedule[day][slot];
                if (!cell) return;
                const list = (Array.isArray(cell) ? cell : [cell]).filter(Boolean);
                list.forEach((slotData) => {
                    if (slotData.courseId) {
                        counts[slotData.courseId] = (counts[slotData.courseId] || 0) + 1;
                    }
                });
                for (let i = 0; i < list.length; i += 1) {
                    for (let j = i + 1; j < list.length; j += 1) {
                        const first = appData.courses.find((c) => c.id === list[i].courseId);
                        const second = appData.courses.find((c) => c.id === list[j].courseId);
                        if (!first || !second) continue;
                        if ((first.teacherIds || []).some((id) => (second.teacherIds || []).includes(id))) conflicts.teacher += 1;
                        if (hasClassGroupConflict(first.classId, second.classId)) conflicts.class += 1;
                        if (list[i].roomId && list[i].roomId === list[j].roomId) conflicts.room += 1;
                    }
                }
            }));
            const missing = expected
                .filter((course) => (counts[course.id] || 0) !== (course.duration || 2) * (course.frequency || 1))
                .map((course) => [course.name, counts[course.id] || 0, (course.duration || 2) * (course.frequency || 1)]);
            const foreign = expected.filter(
                (course) => course.weekType === (week === 'A' ? 'B' : 'A'),
            ).length;
            return { missing, conflicts, foreign, courses: expected.length };
        }"""

        page.evaluate(SEED)
        page.wait_for_timeout(700)
        page.evaluate("switchTab('schedule')")
        page.wait_for_timeout(250)

        check(
            "onglet Optimisation supprimé",
            page.evaluate("!document.getElementById('optimize')")
            and page.eval_on_selector_all("[data-tab='optimize']", "els => els.length") == 0,
        )
        check(
            "navigation mobile à 5 onglets",
            page.eval_on_selector_all(".bottom-nav__item", "els => els.length") == 5,
        )

        page.click(".toolbar [data-generate]")
        page.wait_for_timeout(300)
        check(
            "feuille de génération ouverte",
            page.evaluate("document.getElementById('generation-modal').classList.contains('active')"),
        )
        check(
            "quatre priorités proposées",
            page.eval_on_selector_all(
                "#generation-modal input[type=range]", "els => els.length"
            )
            == 4,
        )
        check(
            "poids de génération par défaut",
            page.evaluate(
                "() => ['teacher','room','class','priority'].map((k) => document.getElementById('generation-weight-' + k).value)"
            )
            == ["5", "3", "2", "4"],
        )

        page.evaluate(
            """() => {
                const set = (key, value) => {
                    const input = document.getElementById('generation-weight-' + key);
                    input.value = String(value);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                };
                set('teacher', 6); set('room', 1); set('class', 3); set('priority', 7);
            }"""
        )
        before_gen = page.evaluate("() => JSON.stringify([appData.scheduleA, appData.scheduleB])")
        page.click("#generation-run")
        page.wait_for_timeout(40)
        check(
            "génération : boutons verrouillés",
            page.evaluate(
                "() => generationRunning === true"
                " && document.getElementById('generation-run').disabled"
                " && document.querySelector('.toolbar [data-generate]').disabled"
            ),
        )
        for _ in range(120):
            if not page.evaluate("generationRunning"):
                break
            page.wait_for_timeout(100)
        check("génération : calcul terminé", page.evaluate("generationRunning === false"))
        check(
            "génération : feuille refermée et boutons rendus",
            page.evaluate(
                "() => !document.getElementById('generation-modal').classList.contains('active')"
                " && !document.querySelector('.toolbar [data-generate]').disabled"
            ),
        )
        check(
            "génération : les deux semaines sont réécrites",
            page.evaluate("() => JSON.stringify([appData.scheduleA, appData.scheduleB])") != before_gen,
        )
        gen_scan = {week: page.evaluate(GEN_SCAN, week) for week in ("A", "B")}
        check(
            "génération : tous les cours placés",
            all(not spec["missing"] for spec in gen_scan.values()),
            str({week: spec["missing"][:3] for week, spec in gen_scan.items()}),
        )
        check(
            "génération : aucun conflit prof / classe / salle",
            all(not any(spec["conflicts"].values()) for spec in gen_scan.values()),
            str({week: spec["conflicts"] for week, spec in gen_scan.items()}),
        )
        check(
            "génération : semaines A et B respectées",
            all(spec["foreign"] == 0 for spec in gen_scan.values()),
        )
        check("génération : compteur de conflits à zéro", page.inner_text("#conflicts").strip() == "0")
        hours_pair = page.evaluate(
            "() => [calculateExpectedHours(), calculateActualHoursFromSchedule()]"
        )
        check(
            "génération : heures effectuées = heures attendues",
            hours_pair[0] > 0 and hours_pair[0] == hours_pair[1],
            str(hours_pair),
        )
        check(
            "génération : poids mémorisés",
            page.evaluate("JSON.parse(localStorage.getItem('flowEdtGenerationWeights'))")
            == {"teacher": 6, "room": 1, "class": 3, "priority": 7},
        )
        page.click(".toolbar [data-generate]")
        page.wait_for_timeout(250)
        check(
            "génération : poids rechargés à l'ouverture",
            page.evaluate(
                "() => ['teacher','room','class','priority'].map((k) => document.getElementById('generation-weight-' + k).value)"
            )
            == ["6", "1", "3", "7"],
        )
        page.evaluate("closeSheet('generation-modal')")
        page.wait_for_timeout(150)

        # verrou : un seul calcul, même si deux lancements s'enchaînent
        lock = page.evaluate(
            """() => {
                window.__genCalls = 0;
                window.__genOriginal = window.buildTimetable;
                window.buildTimetable = function (...args) {
                    window.__genCalls += 1;
                    return window.__genOriginal.apply(this, args);
                };
                startGeneration();
                const busy = generationRunning === true;
                const disabled = document.getElementById('generation-run').disabled;
                startGeneration();
                const toast = document.querySelector('#toast-container .toast:last-child .toast__text');
                return { busy, disabled, toast: toast ? toast.textContent : '' };
            }"""
        )
        for _ in range(120):
            if not page.evaluate("generationRunning"):
                break
            page.wait_for_timeout(100)
        lock_calls = page.evaluate("() => [window.__genCalls, generationRunning]")
        page.evaluate("() => { window.buildTimetable = window.__genOriginal; }")
        check("génération : verrou posé pendant le calcul", lock["busy"] and lock["disabled"], str(lock))
        check("génération : second lancement refusé", "déjà en cours" in lock["toast"], str(lock))
        check("génération : un seul calcul exécuté", lock_calls == [1, False], str(lock_calls))

        # cours à créneau fixe : la place imposée est respectée
        fixed_opt = page.evaluate(
            """() => {
                appData.classes = [
                    { id: 'q1', name: 'Q1', students: 20 },
                    { id: 'q2', name: 'Q2', students: 20 },
                ];
                appData.halfGroups = [];
                appData.classGroups = [];
                appData.teachers = [
                    { id: 'u1', name: 'U1' },
                    { id: 'u2', name: 'U2' },
                ];
                appData.rooms = [{ id: 'v1', name: 'V1', capacity: 30 }];
                appData.forbiddenSlots = [{ teacherIds: ['u1'], day: 'Lundi', slot: '8:00-8:30' }];
                appData.cantineSlots = [{ classId: 'q2', day: 'Lundi', slot: '12:00-12:30' }];
                const make = (id, name, teacherId, classId, extra) => Object.assign({
                    id, name, teacherIds: [teacherId], classId, roomId: null,
                    duration: 4, frequency: 1, priority: 2, constraints: '',
                    weekType: 'Toutes', fixedDay: null, fixedStartSlot: null,
                }, extra);
                appData.courses = [
                    make('f1', 'Fixe', 'u1', 'q1', { fixedDay: 'Mardi', fixedStartSlot: '2' }),
                    make('f2', 'Libre', 'u2', 'q2', { weekType: 'B' }),
                ];
                const outcome = buildTimetable('local', 300, { teacher: 5, room: 3, class: 2, priority: 4 });
                const slot = TIME_SLOTS[2];
                const cell = outcome.scheduleA['Mardi'][slot];
                return {
                    fixed: Boolean(cell) && (Array.isArray(cell) ? cell : [cell]).some((sd) => sd.courseId === 'f1'),
                    weekBFixed: outcome.scheduleA['Mardi'] ? JSON.stringify(outcome.scheduleA['Mardi']).includes('f2') : false,
                    weekB: JSON.stringify(outcome.scheduleB).includes('f2'),
                    unplaced: outcome.unplaced.length,
                    forbidden: JSON.stringify(outcome.scheduleA['Lundi']['8:00-8:30'] || '').includes('f1'),
                    cantine: JSON.stringify(outcome.scheduleA['Lundi']['12:00-12:30'] || '').includes('f2'),
                };
            }"""
        )
        check(
            "génération : créneau fixe respecté",
            fixed_opt["fixed"] is True,
            str(fixed_opt),
        )
        check(
            "génération : semaine B isolée",
            fixed_opt["weekBFixed"] is False and fixed_opt["weekB"] is True,
            str(fixed_opt),
        )
        check(
            "génération : plage interdite et cantine respectées",
            fixed_opt["forbidden"] is False and fixed_opt["cantine"] is False,
            str(fixed_opt),
        )

        # établissement sans salle : les cours sont quand même planifiés
        no_room = page.evaluate(
            """() => {
                appData.rooms = [];
                appData.courses = [{
                    id: 'w1', name: 'Sans salle', teacherIds: ['u1'], classId: 'q1',
                    roomId: null, duration: 2, frequency: 1, priority: 1,
                    constraints: '', weekType: 'Toutes', fixedDay: null,
                    fixedStartSlot: null,
                }];
                const outcome = buildTimetable('greedy', 100, { teacher: 5, room: 3, class: 2, priority: 4 });
                let cells = 0;
                DAYS.forEach((day) => TIME_SLOTS.forEach((slot) => {
                    if (outcome.scheduleA[day][slot]) cells += 1;
                }));
                return { placed: outcome.placed, total: outcome.total, cells };
            }"""
        )
        check(
            "génération : fonctionne sans salle déclarée",
            no_room == {"placed": 2, "total": 2, "cells": 2},
            str(no_room),
        )

        # ---------- 12 bis. cartes décalées, aperçu au survol et au doigt ----------
        page.evaluate(PEEK_SEED)
        page.wait_for_timeout(300)
        page.evaluate("() => { switchTab('schedule'); clearScheduleFilter(); }")
        page.wait_for_timeout(400)
        stacked = page.evaluate(
            """() => {
                const cell = [...document.querySelectorAll('#schedule td.slot--course')]
                    .find((td) => td.offsetParent !== null
                        && td.querySelectorAll('.slot-course').length === 2
                        && td.dataset.day === 'Lundi');
                if (!cell) return null;
                const cards = [...cell.querySelectorAll('.slot-course')].map((card) => ({
                    stack: card.style.getPropertyValue('--stack'),
                    left: Math.round(card.getBoundingClientRect().left),
                    width: Math.round(card.getBoundingClientRect().width),
                }));
                const single = [...document.querySelectorAll('#schedule td.slot--course')]
                    .find((td) => td.offsetParent !== null
                        && td.dataset.day === 'Lundi'
                        && td.dataset.slot === '10:00-10:30');
                return {
                    cards,
                    titles: [...cell.querySelectorAll('.slot-course')].map((card) => card.title),
                    singleTitle: single
                        ? (single.querySelector('.slot-course') || {}).title || ''
                        : '',
                };
            }"""
        )
        check(
            "cartes empilées : la seconde est décalée",
            stacked is not None
            and [card["stack"] for card in stacked["cards"]] == ["0", "1"]
            and 0 < stacked["cards"][1]["left"] - stacked["cards"][0]["left"] <= 6
            and stacked["cards"][1]["width"] < stacked["cards"][0]["width"],
            str(stacked and stacked["cards"]),
        )
        check(
            "pas d'infobulle native sur un créneau à deux cours",
            stacked is not None and stacked["titles"] == ["", ""],
            str(stacked and stacked["titles"]),
        )
        check(
            "infobulle conservée pour un cours seul",
            stacked is not None
            and "THOMAS" in stacked["singleTitle"]
            and "Salle 102" in stacked["singleTitle"],
            str(stacked and stacked["singleTitle"]),
        )

        page.click('.day-tab[data-day-index="1"]')
        page.wait_for_timeout(350)
        badge = page.evaluate(
            """() => {
                const el = [...document.querySelectorAll('#schedule td.slot--course .slot-more')]
                    .find((node) => node.getBoundingClientRect().height > 0);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
            }"""
        )
        if badge:
            page.touchscreen.tap(badge["x"], badge["y"])
        page.wait_for_timeout(400)
        mobile_peek = page.evaluate(
            """() => {
                const peek = document.getElementById('slot-peek');
                if (!peek) return null;
                const box = peek.getBoundingClientRect();
                const bar = document.querySelector('.app-bar').getBoundingClientRect();
                const nav = document.querySelector('.bottom-nav').getBoundingClientRect();
                return {
                    hidden: peek.hidden,
                    title: (peek.querySelector('.slot-peek__title') || {}).textContent,
                    names: [...peek.querySelectorAll('.slot-peek__name')].map((n) => n.textContent.trim()),
                    modal: document.getElementById('edit-modal').classList.contains('active'),
                    inView: box.top >= bar.bottom && box.bottom <= nav.top,
                };
            }"""
        )
        check(
            "aperçu tactile : tous les cours du créneau",
            mobile_peek is not None
            and mobile_peek["hidden"] is False
            and mobile_peek["names"] == ["Histoire-Géographie", "SVT", "Musique"],
            str(mobile_peek and mobile_peek["names"]),
        )
        check(
            "aperçu tactile : la fiche ne s'ouvre pas",
            mobile_peek is not None and mobile_peek["modal"] is False,
        )
        check(
            "aperçu tactile : entre en-tête et navigation",
            mobile_peek is not None and mobile_peek["inView"] is True,
            str(mobile_peek and mobile_peek["title"]),
        )
        page.touchscreen.tap(4, 320)
        page.wait_for_timeout(300)
        check(
            "aperçu refermé par un appui ailleurs",
            page.evaluate("(document.getElementById('slot-peek') || { hidden: true }).hidden"),
        )

        # ---------- 13. bureau : burger masqué, compacité dans la barre ----------
        desk = browser.new_context(viewport={"width": 1440, "height": 900})
        dpage = desk.new_page()
        dpage.goto(URL, wait_until="load")
        dpage.wait_for_timeout(400)
        check("nav desktop visible", dpage.is_visible(".nav"))
        check("burger masqué en desktop", not dpage.is_visible("#menu-toggle"))
        check("bouton compacité visible en desktop", dpage.is_visible("#density-toggle"))
        check("pastille de sauvegarde visible en desktop", dpage.is_visible("#save-indicator"))
        dpage.click("#density-toggle")
        dpage.wait_for_timeout(250)
        check("compacité pilotable depuis la barre", dpage.evaluate("document.documentElement.dataset.density === 'compact'"))
        check(
            "icône de grille en compact (barre)",
            dpage.evaluate("getComputedStyle(document.querySelector('#density-toggle .icon--compact')).display !== 'none'"),
        )
        dpage.click("#density-toggle")
        dpage.wait_for_timeout(250)
        check(
            "canapé en mode confort (barre)",
            dpage.evaluate("getComputedStyle(document.querySelector('#density-toggle .icon--sofa')).display !== 'none'"),
        )
        dpage.evaluate("switchTab('courses')")
        dpage.wait_for_timeout(300)
        check("compacité masquée hors planning (bureau)", not dpage.is_visible("#density-toggle"))
        dpage.evaluate("switchTab('schedule')")
        dpage.wait_for_timeout(300)
        check("compacité de retour sur le planning", dpage.is_visible("#density-toggle"))

        dpage.evaluate(SEED)
        dpage.wait_for_timeout(500)
        desk_heights = dpage.eval_on_selector_all(
            "#schedule table.timetable:not([hidden]) tbody td.slot",
            "els => els.filter(e => e.offsetParent !== null).map(e => Math.round(e.getBoundingClientRect().height))",
        )
        desk_heights = [height for height in desk_heights if height > 0]
        check(
            "lignes régulières en bureau",
            # Un créneau peut contenir plusieurs cours : la ligne s'étire un peu.
            bool(desk_heights)
            and max(desk_heights) - min(desk_heights) <= 8
            and min(desk_heights) >= 44,
            f"{min(desk_heights)}–{max(desk_heights)} px sur {len(desk_heights)} cellules",
        )
        dpage.evaluate("applyDensity('compact')")
        dpage.wait_for_timeout(300)
        desk_compact = dpage.eval_on_selector_all(
            "#schedule table.timetable:not([hidden]) tbody td.slot",
            "els => els.filter(e => e.offsetParent !== null).map(e => Math.round(e.getBoundingClientRect().height))",
        )
        desk_compact = [height for height in desk_compact if height > 0]
        check(
            "lignes compactes régulières en bureau",
            bool(desk_compact)
            and max(desk_compact) - min(desk_compact) <= 1
            and max(desk_compact) < max(desk_heights),
            f"{min(desk_compact)}–{max(desk_compact)} px sur {len(desk_compact)} cellules",
        )

        dpage.evaluate(PEEK_SEED)
        dpage.wait_for_timeout(300)
        dpage.evaluate("() => { switchTab('schedule'); clearScheduleFilter(); }")
        dpage.wait_for_timeout(400)
        target = dpage.evaluate(
            """() => {
                const cell = [...document.querySelectorAll('#schedule td.slot--course')]
                    .find((td) => td.offsetParent !== null
                        && td.dataset.day === 'Lundi'
                        && td.querySelectorAll('.slot-course').length === 2);
                if (!cell) return null;
                const card = cell.querySelector('.slot-course');
                const r = card.getBoundingClientRect();
                return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
            }"""
        )
        if target:
            dpage.mouse.move(target["x"], target["y"])
            dpage.mouse.move(target["x"] + 1, target["y"] + 1)
        dpage.wait_for_timeout(400)
        hover_peek = dpage.evaluate(
            """() => {
                const peek = document.getElementById('slot-peek');
                if (!peek) return null;
                const bar = document.querySelector('.app-bar').getBoundingClientRect();
                const box = peek.getBoundingClientRect();
                return {
                    hidden: peek.hidden,
                    title: (peek.querySelector('.slot-peek__title') || {}).textContent,
                    count: (peek.querySelector('.slot-peek__count') || {}).textContent,
                    items: [...peek.querySelectorAll('.slot-peek__item')].map((li) => ({
                        name: li.querySelector('.slot-peek__name').textContent.trim(),
                        meta: li.querySelector('.slot-peek__meta').textContent.trim(),
                    })),
                    underBar: box.top >= bar.bottom,
                };
            }"""
        )
        check(
            "aperçu au survol : les deux cours de la cellule",
            hover_peek is not None
            and hover_peek["hidden"] is False
            and hover_peek["title"] == "Lundi · 8:00 – 8:30"
            and [item["name"] for item in hover_peek["items"]] == ["Mathématiques", "Français"],
            str(hover_peek and hover_peek["items"]),
        )
        check(
            "aperçu au survol : classe, professeur et salle",
            hover_peek is not None
            and hover_peek["items"][0]["meta"] == "4A · MARTIN · Salle 101",
            str(hover_peek and hover_peek["items"][0]["meta"]),
        )
        check(
            "aperçu au survol : sous la barre d'en-tête",
            hover_peek is not None and hover_peek["underBar"] is True,
        )
        dpage.mouse.move(4, 4)
        dpage.wait_for_timeout(300)
        check(
            "aperçu refermé en quittant la cellule",
            dpage.evaluate("(document.getElementById('slot-peek') || { hidden: true }).hidden"),
        )
        if target:
            dpage.mouse.move(target["x"], target["y"])
            dpage.mouse.move(target["x"] + 1, target["y"] + 1)
        dpage.wait_for_timeout(300)
        dpage.keyboard.press("Escape")
        dpage.wait_for_timeout(200)
        check(
            "aperçu refermé par Échap",
            dpage.evaluate("(document.getElementById('slot-peek') || { hidden: true }).hidden"),
        )
        check(
            "pas d'aperçu pour un créneau d'un seul cours",
            dpage.evaluate(
                """() => {
                    const cell = [...document.querySelectorAll('#schedule td.slot--course')]
                        .find((td) => td.offsetParent !== null
                            && td.dataset.day === 'Lundi'
                            && td.dataset.slot === '10:00-10:30');
                    return !!cell && slotPeekUseful(cell) === false;
                }"""
            ),
        )

        dpage.evaluate("applyDensity('confort')")
        dpage.wait_for_timeout(150)
        desk.close()

        check("aucune erreur JS", not errors, "; ".join(errors[:4]))
        browser.close()

    ok = sum(1 for _, c, _ in results if c)
    for name, cond, detail in results:
        print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    print(f"\n{ok}/{len(results)} tests réussis")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
