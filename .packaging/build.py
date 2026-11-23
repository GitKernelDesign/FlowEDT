#!/usr/bin/env python3
"""Construit les paquets de bureau de Flow-EDT.

  AppImage Linux · installation Windows (NSIS) · archive portable Windows

Les binaires Electron sont mis en cache dans .packaging/cache ; les paquets
finaux sont écrits dans dist/ à la racine du dépôt.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent
ROOT = PACK.parent
CACHE = PACK / "cache"
OUT = ROOT / "dist"
WORK = PACK / "work"
APP = PACK / "app"
ICONS = PACK / "icons"
NSIS = CACHE / "nsis" / "nsis-bundle"

ELECTRON_VERSION = "45.4.1"


def read_version() -> str:
    text = (ROOT / ".audit" / "build" / "patch.py").read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION = "([^"]+)"', text)
    if not match:
        raise SystemExit("APP_VERSION introuvable dans .audit/build/patch.py")
    return match.group(1)


VERSION = read_version()


def run(cmd: list[str], **kwargs) -> None:
    print("  $", " ".join(str(part) for part in cmd[:6]))
    subprocess.run([str(part) for part in cmd], check=True, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fresh(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


# --------------------------------------------------------------------------

def prepare_app(target: Path) -> None:
    """Copie la coquille Electron (main.js, index.html, icône, licence)."""
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(APP / "main.js", target / "main.js")
    shutil.copy2(ROOT / "index.html", target / "index.html")
    shutil.copy2(ICONS / "flowedt.png", target / "icon.png")
    shutil.copy2(ROOT / "LICENSE", target / "LICENSE")
    package = json.loads((APP / "package.json").read_text(encoding="utf-8"))
    package["version"] = VERSION
    (target / "package.json").write_text(
        json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def check_cache() -> None:
    for name in ("electron-linux", "electron-win"):
        folder = CACHE / name
        if not folder.exists() or not any(folder.iterdir()):
            raise SystemExit(f"{folder} manquant : relancer le téléchargement Electron")
    if not (NSIS / "windows" / "makensis.exe").exists():
        raise SystemExit(f"NSIS introuvable dans {NSIS}")


# --------------------------------------------------------------------------

def build_appimage() -> Path:
    print("→ AppImage Linux")
    appdir = fresh(WORK / "FlowEDT.AppDir")
    libdir = appdir / "usr" / "lib" / "flowedt"
    shutil.copytree(CACHE / "electron-linux", libdir)
    shutil.move(libdir / "electron", libdir / "flowedt")
    prepare_app(libdir / "resources" / "app")

    (appdir / "usr" / "bin").mkdir(parents=True)
    launcher = appdir / "usr" / "bin" / "flowedt"
    launcher.write_text(
        "#!/bin/sh\n"
        '# Lanceur interne : AppRun s\'occupe de l\'environnement.\n'
        'exec "$APPDIR/usr/lib/flowedt/flowedt" "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    apprun = appdir / "AppRun"
    apprun.write_text(
        "#!/bin/sh\n"
        "HERE=$(dirname \"$(readlink -f \"$0\")\")\n"
        "export APPDIR=\"$HERE\"\n"
        "# Le bac à sable de Chromium exige un binaire setuid : impossible depuis\n"
        "# une image montée en lecture seule, on le désactive explicitement.\n"
        "exec \"$HERE/usr/lib/flowedt/flowedt\" --no-sandbox \"$@\"\n",
        encoding="utf-8",
    )
    apprun.chmod(0o755)

    desktop = appdir / "flowedt.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Flow-EDT\n"
        "GenericName=Générateur d'emplois du temps\n"
        "Comment=Composer les emplois du temps d'un établissement scolaire\n"
        "Exec=flowedt %U\n"
        "Icon=flowedt\n"
        "Terminal=false\n"
        "Categories=Education;Office;\n"
        "Keywords=emploi du temps;planning;collège;lycée;EDT;\n"
        "StartupWMClass=flow-edt\n"
        "StartupNotify=true\n",
        encoding="utf-8",
    )
    shutil.copy2(ICONS / "flowedt.png", appdir / "flowedt.png")
    (appdir / ".DirIcon").symlink_to("flowedt.png")
    icon_dir = appdir / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
    icon_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ICONS / "flowedt.png", icon_dir / "flowedt.png")

    target = OUT / f"FlowEDT-{VERSION}-x86_64.AppImage"
    if target.exists():
        target.unlink()
    env = dict(os.environ, ARCH="x86_64", VERSION=VERSION)
    run(
        [
            "appimagetool",
            "--no-appstream",
            appdir,
            target,
        ],
        env=env,
    )
    target.chmod(0o755)
    return target


# --------------------------------------------------------------------------

def prepare_windows() -> Path:
    """Arborescence Windows complète : binaire renommé et patché, application, licence."""
    print("→ Windows : préparation de l'arborescence")
    folder = fresh(WORK / "Flow-EDT")
    shutil.copytree(CACHE / "electron-win", folder, dirs_exist_ok=True)
    patched = folder / "Flow-EDT.exe"
    run(
        [
            sys.executable,
            PACK / "tools" / "patch_exe.py",
            folder / "electron.exe",
            patched,
            ICONS,
            VERSION,
            "B.Dupont",
        ]
    )
    (folder / "electron.exe").unlink()
    # default_app.asar n'est jamais chargé dès que resources/app existe.
    (folder / "resources" / "default_app.asar").unlink(missing_ok=True)
    prepare_app(folder / "resources" / "app")
    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE.txt")
    shutil.copy2(ROOT / "README.md", folder / "README.md")
    return folder


def build_portable(folder: Path) -> Path:
    print("→ Windows portable")
    # portable.txt : les données (FlowEDT-data) restent à côté de l'exécutable.
    marker = folder / "portable.txt"
    marker.write_text(
        "Mode portable : les données (FlowEDT-data) restent dans ce dossier.\n",
        encoding="utf-8",
    )
    archive = OUT / f"FlowEDT-{VERSION}-windows-x64-portable.zip"
    if archive.exists():
        archive.unlink()
    try:
        run(["7z", "a", "-tzip", "-mx=5", "-bso0", "-bsp0", archive, folder.name], cwd=WORK)
    finally:
        marker.unlink(missing_ok=True)
    return archive


def build_setup(app_folder: Path) -> Path:
    print("→ Installation Windows (NSIS)")
    target = OUT / f"FlowEDT-{VERSION}-windows-x64-setup.exe"
    if target.exists():
        target.unlink()
    size_kb = sum(item.stat().st_size for item in app_folder.rglob("*") if item.is_file()) // 1024
    env = dict(os.environ)
    env["NSISDIR"] = str(NSIS / "windows")
    run(
        [
            NSIS / "linux" / "x64" / "makensis",
            "-V2",
            f"-DAPP_VERSION={VERSION}",
            f"-DAPP_SOURCE={app_folder}",
            f"-DAPP_SIZE_KB={size_kb}",
            f"-DOUT_FILE={target}",
            f"-DICON_FILE={ICONS / 'flowedt.ico'}",
            f"-DLICENSE_FILE={ROOT / 'LICENSE'}",
            PACK / "installer.nsi",
        ],
        env=env,
    )
    return target


# --------------------------------------------------------------------------

def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    check_cache()
    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    print(f"Flow-EDT {VERSION} — Electron {ELECTRON_VERSION}")

    produced: list[Path] = []
    if only in ("all", "linux"):
        produced.append(build_appimage())
    if only in ("all", "windows"):
        folder = prepare_windows()
        # Le dossier d'installation ne doit pas contenir portable.txt : sinon
        # l'application installée écrirait ses données dans Program Files.
        staging = fresh(WORK / "Flow-EDT-install")
        shutil.copytree(folder, staging, dirs_exist_ok=True)
        produced.append(build_setup(staging))
        produced.append(build_portable(folder))

    print("\nPaquets :")
    for item in produced:
        size = item.stat().st_size / (1 << 20)
        print(f"  {item.name:52} {size:7.1f} Mo  sha256 {sha256(item)[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
