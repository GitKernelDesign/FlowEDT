#!/usr/bin/env python3
"""Audit harness for Flow-EDT: screenshots + console/page errors.

Usage: python3 shot.py <label> [url_path]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
URL = (PROJECT / "index.html").as_uri()

SEED = r"""
() => {
  // L'application ne livre plus aucune donnée : le harnais de QA crée son
  // propre établissement de test (ressources + cours) avant chaque capture.
  const teacher = (id, name) => ({ id, name });
  const room = (id, name, capacity) => ({ id, name, capacity });
  const cls = (id, name, students) => ({ id, name, students });
  const half = (id, classId, n) => ({
    id, classId, name: `${appData.classes.find((c) => c.id === classId).name} - Groupe ${n}`,
    groupNumber: n, groupName: `Groupe ${n}`,
  });

  appData.teachers = [
    teacher("t1", "MARTIN"), teacher("t2", "BERNARD"), teacher("t3", "DUBOIS"),
    teacher("t4", "THOMAS"), teacher("t5", "ROBERT"), teacher("t6", "RICHARD"),
    teacher("t7", "PETIT"), teacher("t8", "DURAND"), teacher("t9", "LEROY"),
    teacher("t10", "MOREAU"), teacher("t11", "SIMON"), teacher("t12", "LAURENT"),
    teacher("t13", "SPORT 1"), teacher("t14", "SPORT 2"), teacher("t15", "ECO-GES"),
  ];
  appData.rooms = [
    room("r1", "Gymnase", 30), room("r2", "Atelier 1", 30), room("r3", "Atelier 2", 30),
    room("r4", "Salle 1", 30), room("r5", "Salle 2", 30), room("r6", "Salle DAO", 30),
    room("r7", "A30", 30), room("r8", "A29", 30), room("r9", "E11", 30),
    room("r10", "M06", 30), room("r11", "E07", 30), room("r12", "E16", 30),
    room("r13", "Lab1", 30), room("r14", "Lab2", 30), room("r15", "Lab3", 30),
    room("r16", "E15", 30),
  ];
  appData.classes = [
    cls("c1", "1 G1", 30), cls("c2", "1 G2", 28), cls("c3", "2 G1", 32),
    cls("c4", "2 G2", 30), cls("c5", "3 G1", 30), cls("c6", "T G1", 25),
    cls("c7", "T G2", 25), cls("c8", "BTS 1", 25),
  ];
  appData.halfGroups = [
    half("hg1", "c1", 1), half("hg2", "c1", 2),
    half("hg3", "c2", 1), half("hg4", "c2", 2),
  ];
  appData.classGroups = [
    { id: "cg1", name: "Terminales", classIds: ["c6", "c7", "c8"] },
    { id: "cg2", name: "Première année", classIds: ["c3", "c4", "c5"] },
    { id: "cg3", name: "Deuxième année", classIds: ["c1", "c2"] },
  ];

  const mk = (id, name, teacherIds, classId, roomId, duration, frequency, weekType, priority) => ({
    id, name, teacherIds, classId, roomId, duration, frequency,
    priority: priority || 2, constraints: "", weekType: weekType || "Toutes",
    fixedDay: null, fixedStartSlot: null, scheduled: false,
  });
  appData.courses = [
    mk("c1", "Mathématiques", ["t1"], "c1", "r4", 4, 2, "Toutes", 3),
    mk("c2", "Français", ["t2"], "c1", null, 4, 2, "Toutes", 2),
    mk("c3", "Histoire-Géo", ["t3"], "c1", "r8", 4, 1, "Toutes", 2),
    mk("c4", "Anglais", ["t4"], "c1", null, 2, 2, "Toutes", 1),
    mk("c5", "EPS", ["t13"], "c1", "r1", 4, 1, "Toutes", 1),
    mk("c6", "Arts Appliqués", ["t5"], "hg1", "r3", 6, 1, "A", 2),
    mk("c7", "Physique", ["t6"], "hg2", "r13", 4, 1, "B", 2),
    mk("c8", "Économie", ["t15"], "c2", "r10", 4, 1, "Toutes", 2),
    mk("c9", "Mathématiques", ["t7"], "c3", "r11", 4, 2, "Toutes", 3),
    mk("c10", "Français", ["t8"], "c4", null, 4, 2, "Toutes", 2),
    mk("c11", "Anglais", ["t9"], "c5", null, 2, 2, "Toutes", 1),
    mk("c12", "EPS", ["t14"], "c6", "r1", 4, 1, "Toutes", 1),
  ];
  appData.cantineSlots = [{ classId: null, day: "Lundi", slot: "12:00-12:30" }];
  appData.forbiddenSlots = [{ teacherIds: ["t1"], day: "Vendredi", slot: "17:00-17:30" }];
  generateBasicSchedule();
  saveData();
  updateAllUI();
  updateScheduleDisplay();
}
"""

TABS = ["schedule", "resources", "courses", "teachers", "export"]


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    url = (PROJECT / sys.argv[2]).as_uri() if len(sys.argv) > 2 else URL
    out = ROOT / label
    out.mkdir(parents=True, exist_ok=True)

    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for device, (w, h) in {
            "mobile": (390, 844),
            "tablet": (900, 800),
            "desktop": (1440, 900),
        }.items():
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                device_scale_factor=2 if device == "mobile" else 1,
                is_mobile=device == "mobile",
                has_touch=device == "mobile",
                locale="fr-FR",
            )
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.goto(url, wait_until="load")
            page.wait_for_timeout(500)
            report[f"{device}_pagerrors"] = errors[:]

            page.evaluate(SEED)
            page.wait_for_timeout(400)
            # les notifications de démonstration masquent la capture
            page.evaluate(
                "() => { document.querySelectorAll('.toast').forEach(t => t.remove()); const c = document.getElementById('toast-container'); if (c) c.innerHTML = ''; }"
            )
            page.wait_for_timeout(100)

            metrics = {}
            for tab in TABS:
                page.evaluate(f"switchTab('{tab}')")
                page.wait_for_timeout(350)
                page.screenshot(path=str(out / f"{device}-{tab}.png"), full_page=True)
                metrics[tab] = page.evaluate(
                    """() => ({
                        scrollW: document.documentElement.scrollWidth,
                        clientW: document.documentElement.clientWidth,
                        docH: document.documentElement.scrollHeight,
                    })"""
                )
            # horizontal overflow offenders
            report[f"{device}_metrics"] = metrics
            report[f"{device}_overflow"] = page.evaluate(
                """() => {
                    const vw = innerWidth;
                    return [...document.querySelectorAll('body *')]
                      .filter(el => { const r = el.getBoundingClientRect();
                        return r.right > vw + 2 && r.width > 0 && getComputedStyle(el).position !== 'fixed'; })
                      .slice(0, 25)
                      .map(el => el.tagName + '.' + (el.className || '').toString().slice(0, 50) + ' w=' + Math.round(el.getBoundingClientRect().width));
                }"""
            )
            report[f"{device}_errors"] = errors[:]
            ctx.close()
        browser.close()

    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
