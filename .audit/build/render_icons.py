#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exporte icon.svg en PNG (512, 192, 180, 32, 16) via Chromium.

Le rendu passe par Playwright pour conserver la transparence hors du carré
arrondi. Relancer après toute modification de icon.svg :

    python3 .audit/build/render_icons.py
"""
import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT = Path(__file__).resolve().parent.parent.parent
SVG = (PROJECT / "icon.svg").read_text(encoding="utf-8")
URI = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()
SIZES = (512, 192, 180, 32, 16)


def page(size: int) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:transparent}}img{{display:block}}
</style></head><body><img src="{URI}" width="{size}" height="{size}"></body></html>"""


def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for size in SIZES:
            page_obj = browser.new_page(viewport={"width": size, "height": size})
            page_obj.set_content(page(size))
            page_obj.wait_for_timeout(120)
            page_obj.screenshot(
                path=str(PROJECT / f"icon-{size}.png"), omit_background=True
            )
            page_obj.close()
            print(f"icon-{size}.png")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
