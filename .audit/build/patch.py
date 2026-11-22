#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Applique la refonte UX/UI à index.html.

Le script est idempotent : il repart toujours de .audit/index.original.html.
"""
import base64
import re
import sys
import textwrap
from pathlib import Path

from impl import FUNCS, HELPERS, PICKER_HELPERS, STUDIO_STATE
from impl2 import FUNCS2, ONLOAD
from impl3 import FUNCS3

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT.parent
PROJECT = AUDIT.parent
SOURCE = AUDIT / "index.original.html"
TARGET = PROJECT / "index.html"

CSS = (ROOT / "style.css").read_text(encoding="utf-8")
BODY = (ROOT / "body.html").read_text(encoding="utf-8")

INDENT = " " * 12

# Métadonnées du projet — seule source de vérité pour la version et la licence.
APP_NAME = "Flow-EDT"
APP_VERSION = "1.2.0"
APP_LICENSE = "GPL-3.0"
APP_YEAR = "2026"
APP_AUTHOR = "B.Dupont"

ICON_FILE = PROJECT / "icon.svg"
ICON_URI = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(ICON_FILE.read_text(encoding="utf-8").encode()).decode()
)

BANNER = f"""<!--
  {APP_NAME} {APP_VERSION} — générateur d'emplois du temps
  Copyright (C) {APP_YEAR} {APP_AUTHOR}
  Logiciel libre distribué sous licence GNU GPL v3 (voir LICENSE) : vous pouvez
  le redistribuer et/ou le modifier selon les termes de la licence. Ce programme
  est fourni sans AUCUNE GARANTIE.
-->
"""

HEAD_EXTRA = """        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#f5f7fa" />
        <meta name="application-version" content="__VERSION__" />
        <meta name="license" content="__LICENSE__" />
        <meta name="color-scheme" content="light dark" />
        <meta
            name="description"
            content="Flow-EDT — générateur d'emplois du temps scolaires : ressources, cours, contraintes et génération automatique."
        />
        <link rel="icon" type="image/svg+xml" href="__ICON__" />
        <link rel="apple-touch-icon" href="icon-180.png" />
        <script>
            (function () {
                try {
                    var saved = localStorage.getItem("flowEdtTheme");
                    if (
                        saved === "dark" ||
                        (!saved &&
                            window.matchMedia("(prefers-color-scheme: dark)")
                                .matches)
                    ) {
                        document.documentElement.dataset.theme = "dark";
                    }
                    var density = localStorage.getItem("flowEdtDensity");
                    if (density === "compact") {
                        document.documentElement.dataset.density = "compact";
                    }
                    document.documentElement.dataset.tab = "schedule";
                } catch (error) {
                    /* stockage indisponible */
                }
            })();
        </script>
"""

FOOTER = """        <footer class="app-footer">
            <p>Flow-EDT — générateur d'emplois du temps</p>
            <p>Développé par B.Dupont · Licence __LICENSE__ · Version __VERSION__</p>
        </footer>
"""

FUNC_NAMES_ALL = set(FUNCS) | set(FUNCS2)
DEAD = [
    "findSuitableRoom",
    "findSuitableRoomForSchedule",
    "runGreedy",
    "runGenetic",
    "generateRandomSchedule",
    "crossover",
    "mutate",
    "moveRandomCourse",
    "replaceRandomCourse",
    "removeRandomCourse",
    "startOptimization",
    "runOptimization",
    "updateProgress",
    "canPlaceCourseInSlots",
    "updateFilterSelects",
    "setViewMode",
    "applyScheduleFilter",
    "renderFilteredSchedule",
    "applyScheduleFilterByItem",
    "resetScheduleFilter",
    "switchToMainView",
    "switchScheduleView",
    "renderTeachersScheduleTable",
    "renderClassesScheduleTable",
    "renderRoomsScheduleTable",
    "updateTeachersScheduleDisplay",
    "updateClassesScheduleDisplay",
    "updateRoomsScheduleDisplay",
]


def find_span(text: str, name: str):
    """Retourne (start, end) en offsets de la fonction top-level `name`."""
    lines = text.splitlines(keepends=True)
    start_line = None
    pattern = re.compile(
        r"^ {12}(?:async\s+)?function\s+" + re.escape(name) + r"\s*\("
    )
    for index, line in enumerate(lines):
        if pattern.match(line):
            start_line = index
            break
    if start_line is None:
        return None
    for end_line in range(start_line + 1, len(lines)):
        if lines[end_line].rstrip("\r\n") == "            }":
            start = sum(len(l) for l in lines[:start_line])
            end = sum(len(l) for l in lines[:end_line]) + len(
                lines[end_line].rstrip("\r\n")
            )
            return start, end
    return None


def replace_function(text: str, name: str, body: str) -> str:
    span = find_span(text, name)
    if not span:
        raise SystemExit(f"Fonction introuvable : {name}")
    start, end = span
    indented = "\n".join(
        (INDENT + line) if line.strip() else "" for line in body.splitlines()
    )
    return text[:start] + indented + text[end:]


def remove_function(text: str, name: str) -> str:
    span = find_span(text, name)
    if not span:
        return text
    start, end = span
    # retire aussi la ou les lignes vides qui suivent
    while text[end : end + 1] == "\n":
        end += 1
    return text[:start] + text[end:]


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    text = source

    # ---------- 1. HEAD ----------
    title = "<title>Flow-EDT — Générateur d'emplois du temps</title>"
    text = re.sub(r"<title>.*?</title>", title, text, count=1, flags=re.S)

    viewport = re.search(r'<meta name="viewport"[^>]*/>', text)
    if not viewport:
        raise SystemExit("meta viewport introuvable")
    head_extra = (
        HEAD_EXTRA.replace("__VERSION__", APP_VERSION)
        .replace("__LICENSE__", APP_LICENSE)
        .replace("__ICON__", ICON_URI)
    )
    text = (
        text[: viewport.start()].rstrip(" \t")
        + head_extra
        + text[viewport.end() :]
    )

    # bandeau de licence juste après le doctype
    if "<!doctype" in text[:200] and not text.startswith("<!--"):
        doctype_end = text.index(">", text.index("<!doctype")) + 1
        text = text[:doctype_end] + "\n" + BANNER + text[doctype_end:]

    # ---------- 2. CSS ----------
    style_start = text.index("<style>")
    style_end = text.index("</style>", style_start) + len("</style>")
    text = (
        text[:style_start]
        + "<style>\n"
        + CSS.rstrip()
        + "\n        </style>"
        + text[style_end:]
    )

    # ---------- 3. BODY ----------
    body_start = text.index("    <body>") + len("    <body>")
    script_start = text.index("        <script>", body_start)
    text = (
        text[:body_start]
        + "\n"
        + BODY.rstrip()
        + "\n\n"
        + text[script_start:]
    )

    # ---------- 4. FOOTER ----------
    footer_start = text.index("<footer", text.rindex("</script>"))
    footer_end = text.index("</footer>", footer_start) + len("</footer>")
    footer = FOOTER.replace("__VERSION__", APP_VERSION).replace(
        "__LICENSE__", APP_LICENSE
    )
    text = text[:footer_start] + footer.strip() + text[footer_end:]

    # ---------- 5. HELPERS ----------
    anchor = "            // Extraire l'heure de début d'un créneau"
    if anchor not in text:
        raise SystemExit("ancre helpers introuvable")
    text = text.replace(
        anchor,
        textwrap.indent((HELPERS + PICKER_HELPERS).strip(), " " * 12) + "\n\n" + anchor,
        1,
    )

    # ---------- 6. FONCTIONS REMPLACÉES / AJOUTÉES ----------
    combined = {**FUNCS, **FUNCS2, **FUNCS3}
    new_functions = {}
    for name, body in combined.items():
        if find_span(text, name):
            text = replace_function(text, name, body.strip())
        else:
            new_functions[name] = body.strip()

    if new_functions:
        # l'état de l'onglet Professeurs précède ses fonctions
        block = "\n".join(
            textwrap.indent(body, INDENT)
            for body in [STUDIO_STATE, *new_functions.values()]
        )
        anchor = text.rindex("        </script>")
        text = (
            text[:anchor]
            + "            // ==================== COMPOSANTS UI ====================\n\n"
            + block
            + "\n\n"
            + text[anchor:]
        )
        print(f"nouvelles fonctions ajoutées : {', '.join(new_functions)}")

    # ---------- 6b. SALLES : PAS DE DOUBLE OCCUPATION ----------
    # Les générateurs et les optimiseurs faisaient
    # `course.roomId || findSuitableRoomForDuration(...)` : dès qu'une salle
    # était imposée au cours, elle était utilisée sans vérifier qu'elle est
    # libre, ce qui superposait deux classes dans la même salle. On passe
    # désormais par resolveRoomForPlacement(), qui contrôle la disponibilité
    # sur toute la durée et bascule sur une autre salle si besoin.
    room_call = re.compile(
        r"(?P<base>\w+(?:\[[^\]]+\])*(?:\.[A-Za-z_$][\w$]*)*)\.roomId"
        r"\s*\|\|\s*findSuitableRoomForDuration\(\s*"
        r"(?P<course>[\w$]+),\s*(?P<schedule>[\w.\[\]$]+),\s*"
        r"(?P<day>[\w$]+),\s*(?P<index>[\w$]+),\s*(?P<span>[\w$]+),?\s*\)"
    )

    def room_replacement(match):
        line_start = text.rfind("\n", 0, match.start()) + 1
        indent = re.match(r" *", text[line_start:]).group(0)
        args = [
            match.group("course"),
            match.group("schedule"),
            match.group("day"),
            match.group("index"),
            match.group("span"),
            match.group("base") + ".roomId",
        ]
        body = "".join(f"{indent}    {arg},\n" for arg in args)
        return "resolveRoomForPlacement(\n" + body + indent + ")"

    text, room_calls = room_call.subn(room_replacement, text)
    print(f"salles : {room_calls} placements sécurisés")
    if room_calls != 6:
        raise SystemExit(f"placements de salle inattendus : {room_calls}")

    # ---------- 6c. VERROU DE GÉNÉRATION ----------
    # `optimizationRunning` devient `generationRunning` : la génération est
    # désormais le seul calcul lourd et un seul lancement peut être en cours.
    if "let optimizationRunning = false;" not in text:
        raise SystemExit("verrou optimizationRunning introuvable")
    text = text.replace(
        "let optimizationRunning = false;",
        "let generationRunning = false;",
        1,
    )

    # ---------- 7. FONCTIONS MORTES ----------
    for name in DEAD:
        text = remove_function(text, name)

    # doublon de saveData
    occurrences = [m.start() for m in re.finditer(r"^ {12}function saveData\(", text, re.M)]
    if len(occurrences) == 2:
        text = remove_function(text, "saveData")  # supprime la 1re
        # il en reste une : OK
    elif len(occurrences) > 2:
        raise SystemExit("trop de saveData")

    # ---------- 8. ONLOAD ----------
    onload_pattern = re.compile(
        r"^ {12}window\.onload = function \(\) \{.*?^ {12}\};",
        re.S | re.M,
    )
    if not onload_pattern.search(text):
        raise SystemExit("window.onload introuvable")
    text = onload_pattern.sub(
        lambda _: textwrap.indent(ONLOAD.strip(), " " * 12), text, count=1
    )

    # ---------- 9. CORRECTIONS CIBLÉES ----------
    # 9a. openTeacherAccordions manquant à la création des données par défaut
    text, count = re.subn(
        r"(\n(\s*)schemaVersion: 2,)",
        r"\1\n\2openTeacherAccordions: [],",
        text,
        count=1,
    )
    assert count == 1, "schemaVersion introuvable"

    # 9b. les statistiques sont désormais gérées par updateHoursStat remplacée
    # (masquage via l'attribut `hidden`), plus de bascule de style inline.

    # 9c. ouverture des modales via le helper (verrou de scroll + focus)
    text, count = re.subn(
        r'document\.getElementById\("edit-modal"\)\.classList\.add\("active"\);',
        'openSheet("edit-modal");',
        text,
    )
    print(f"modales converties : {count}")

    # 9d. appels au sélecteur de filtres legacy
    text, count = re.subn(r"\n[ \t]*updateFilterSelects\(\);", "", text)
    print(f"appels updateFilterSelects retirés : {count}")

    # 9e. fermeture du panneau cours sur mobile après ajout
    text, count = re.subn(
        r"(showNotification\(`Cours \"\$\{name\}\" (?:ajouté|modifié)`\);\n\s*resetCourseForm\(\);)",
        r"\1\n                    if (window.matchMedia('(max-width: 899px)').matches) {\n                        toggleCoursePanel(false);\n                    }",
        text,
    )
    print(f"fermeture panneau après ajout : {count}")

    # 9l. le studio professeurs suit toutes les mises à jour globales
    anchor = "                updateCantineSlotSelects();\n"
    assert anchor in text, "updateAllUI introuvable"
    text = text.replace(anchor, anchor + "                renderTeacherStudio();\n", 1)

    # 9f. nettoyage du commentaire final
    text = text.replace("            // Un peu codé avec le cul :)\n", "")

    # 9g. le tableau de bord ne doit plus référencer la vue supprimée
    text = text.replace(
        '                        currentScheduleView = "main";\n', ""
    )
    text = text.replace(
        '            // Variable pour suivre la vue actuelle\n            let currentScheduleView = "main";\n\n', ""
    )
    text = text.replace('            let currentScheduleView = "main";\n', "")

    # 9h. libellés d'options homogènes (les selects dynamiques réécrivent leur 1re option)
    text = text.replace(
        '<option value="">Sélectionnez un créneau</option>',
        '<option value="">Choisir un créneau</option>',
    )
    text = text.replace(
        '<option value="">Sélectionnez un jour</option>',
        '<option value="">Choisir un jour</option>',
    )
    text = text.replace(
        '<option value="">Sélectionnez une classe</option>',
        '<option value="">Choisir une classe</option>',
    )

    # 9i. plus aucun jeu de démonstration : au premier lancement (ou lorsque le
    # stockage ne contient que l'ancien exemple jamais retouché), l'application
    # s'ouvre sur un établissement vide.
    anchor = "                        appData = JSON.parse(saved);\n"
    assert anchor in text, "affectation appData introuvable"
    purge = (
        anchor
        + "                        // L'ancien jeu de démonstration n'a plus lieu d'être :\n"
        + "                        // s'il n'a jamais été modifié, on repart d'une base vide.\n"
        + "                        if (isPristineLegacyDemo(appData)) {\n"
        + '                            localStorage.removeItem("emploiDuTemps");\n'
        + "                            createDefaultData();\n"
        + "                            return;\n"
        + "                        }\n"
    )
    text = text.replace(anchor, purge, 1)

    # 9j. plus aucun nom d'établissement, même en commentaire
    text = text.replace(
        '            // Ex: "2AMA-Groupe1" -> "2AMA"\n',
        "",
    )

    # 9k. palette des professeurs (teintes de la charte : sarcelle, saumon, ardoise…)
    # L'ancienne liste (rouge vif, turquoise, jaune pâle…) datait d'avant la refonte.
    TEACHER_COLORS = [
        "#3a9c89",  # sarcelle
        "#cc683e",  # terre cuite
        "#4f88b0",  # acier bleu
        "#7d57a8",  # mauve
        "#479061",  # sauge
        "#ae8132",  # miel
        "#b8515f",  # bois de rose
        "#43859d",  # bleu pétrole
        "#798d49",  # olive
        "#c66b2f",  # ambre
        "#9459a6",  # violet
        "#3f8d70",  # émeraude
        "#c24f3d",  # corail
        "#4f65a1",  # bleu ardoise
        "#ae8a29",  # blé
        "#a85780",  # prune
        "#398793",  # cyan profond
        "#5d814b",  # vert olive
        "#945794",  # lie-de-vin
        "#4b6b8b",  # bleu nuit
    ]
    palette = INDENT + "const TEACHER_COLORS = [\n"
    palette += "".join(f'{INDENT}    "{c}",\n' for c in TEACHER_COLORS)
    palette += INDENT + "];\n"
    text, count = re.subn(
        r" {12}const TEACHER_COLORS = \[.*?\n {12}\];\n",
        lambda _: palette,
        text,
        count=1,
        flags=re.S,
    )
    assert count == 1, "TEACHER_COLORS introuvable"

    # ---------- 10. ÉCRITURE ----------
    leftovers = [
        name
        for name in DEAD + ["currentScheduleView"]
        if re.search(r"\b" + re.escape(name) + r"\b", text)
    ]
    if leftovers:
        print("ATTENTION références restantes :", leftovers)

    TARGET.write_text(text, encoding="utf-8")
    print(f"Écrit : {TARGET} ({len(text)} caractères)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
