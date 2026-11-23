#!/usr/bin/env python3
"""Contrôle des paquets produits dans dist/.

Vérifie, sans exécuter les binaires :
  · l'AppImage : format, contenu de l'AppDir, icônes, fichier .desktop ;
  · l'installateur : icônes et chaînes de version du PE, contenu de l'archive ;
  · le portable : arborescence, resources/app/index.html identique au dépôt.

Usage : python3 .packaging/verify.py
"""
from __future__ import annotations

import hashlib
import io
import re
import struct
import sys
import zipfile
from pathlib import Path

import pefile
from PIL import Image

PACK = Path(__file__).resolve().parent
ROOT = PACK.parent
DIST = ROOT / "dist"


def read_version() -> str:
    text = (ROOT / ".audit" / "build" / "patch.py").read_text(encoding="utf-8")
    return re.search(r'APP_VERSION = "([^"]+)"', text).group(1)


VERSION = read_version()
failures: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    print(f"  {'✓' if condition else '✗'} {label}{f' — {detail}' if detail else ''}")
    if not condition:
        failures.append(label)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# --------------------------------------------------------------------------


def verify_appimage() -> None:
    path = DIST / f"FlowEDT-{VERSION}-x86_64.AppImage"
    print(f"\nAppImage — {path.name}")
    if not path.exists():
        check(False, "présent", "fichier absent")
        return
    data = path.read_bytes()
    check(data[:4] == b"\x7fELF", "binaire ELF", f"{len(data) / (1 << 20):.1f} Mo")
    check(bool(path.stat().st_mode & 0o111), "exécutable")

    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as work:
        subprocess.run(
            [str(path), "--appimage-extract"],
            cwd=work,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        appdir = Path(work) / "squashfs-root"
        check((appdir / "AppRun").exists(), "AppRun")
        check((appdir / "flowedt.desktop").exists(), "flowedt.desktop")
        check((appdir / ".DirIcon").exists(), ".DirIcon")
        check(
            (appdir / "usr/lib/flowedt/flowedt").exists(),
            "binaire applicatif",
            "usr/lib/flowedt/flowedt",
        )
        icon = appdir / "usr/share/icons/hicolor/512x512/apps/flowedt.png"
        check(icon.exists() and Image.open(icon).size == (512, 512), "icône hicolor 512")
        desktop = (appdir / "flowedt.desktop").read_text(encoding="utf-8")
        check("Icon=flowedt" in desktop, "Icon= dans le .desktop")
        check("StartupWMClass=flow-edt" in desktop, "StartupWMClass=flow-edt (WM_CLASS réel)")
        app = appdir / "usr/lib/flowedt/resources/app"
        check((app / "main.js").exists(), "resources/app/main.js")
        check(
            md5((app / "index.html").read_bytes()) == md5((ROOT / "index.html").read_bytes()),
            "index.html identique au dépôt",
        )


def pe_icons(path: Path) -> list[tuple[int, int, str]]:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories([pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    found = []
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id != 3:  # RT_ICON
            continue
        for item in entry.directory.entries:
            for lang in item.directory.entries:
                data = lang.data.struct
                blob = pe.get_data(data.OffsetToData, data.Size)
                if blob[:8] == b"\x89PNG\r\n\x1a\n":
                    width, height = Image.open(io.BytesIO(blob)).size
                    found.append((width, height, "png"))
                else:
                    width, height = struct.unpack("<ii", blob[4:12])
                    found.append((width, height // 2, "dib"))
    return sorted(found)


def pe_version(path: Path) -> tuple[dict[str, str], tuple[int, ...]]:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories([pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    strings: dict[str, str] = {}
    numbers: tuple[int, ...] = ()
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id != 16:  # RT_VERSION
            continue
        for item in entry.directory.entries:
            for lang in item.directory.entries:
                data = lang.data.struct
                blob = pe.get_data(data.OffsetToData, data.Size)
                if len(numbers) == 0 and blob[40:44] == struct.pack("<I", 0xFEEF04BD):
                    _sig, _sv, fms, fls, pms, pls = struct.unpack_from("<IIIIII", blob, 40)
                    numbers = (
                        fms >> 16, fms & 0xFFFF, fls >> 16, fls & 0xFFFF,
                        pms >> 16, pms & 0xFFFF, pls >> 16, pls & 0xFFFF,
                    )
                text = blob.decode("utf-16-le", errors="ignore")
                tokens = re.findall(r"[ -~À-ÿ]{3,}", text)
                for index, token in enumerate(tokens[:-1]):
                    strings.setdefault(token, tokens[index + 1])
    return strings, numbers


def verify_setup() -> None:
    path = DIST / f"FlowEDT-{VERSION}-windows-x64-setup.exe"
    print(f"\nInstallateur Windows — {path.name}")
    if not path.exists():
        check(False, "présent", "fichier absent")
        return
    check(True, "taille", f"{path.stat().st_size / (1 << 20):.1f} Mo")
    icons = pe_icons(path)
    sizes = [width for width, _height, _kind in icons]
    check(sizes == [16, 24, 32, 48, 64, 128, 256], "icônes 16→256", str(sizes))
    strings, numbers = pe_version(path)
    check(strings.get("ProductName") == "Flow-EDT", "ProductName", strings.get("ProductName", ""))
    check(strings.get("FileVersion") == VERSION, "FileVersion", strings.get("FileVersion", ""))
    check(strings.get("CompanyName") == "B.Dupont", "CompanyName", strings.get("CompanyName", ""))
    check(
        numbers[:4] == (1, 2, 1, 0),
        "VS_FIXEDFILEINFO",
        ".".join(str(part) for part in numbers[:4]),
    )

    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as work:
        subprocess.run(
            ["7z", "x", "-y", f"-o{work}", str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        folder = Path(work)
        check((folder / "Flow-EDT.exe").exists(), "Flow-EDT.exe")
        check(not (folder / "portable.txt").exists(), "pas de portable.txt (données hors Program Files)")
        check((folder / "Uninstall.exe").exists(), "Uninstall.exe")
        app = folder / "resources" / "app"
        check((app / "main.js").exists(), "resources/app/main.js")
        check(
            md5((app / "index.html").read_bytes()) == md5((ROOT / "index.html").read_bytes()),
            "index.html identique au dépôt",
        )
        exe_icons = pe_icons(folder / "Flow-EDT.exe")
        check(
            [width for width, _h, _k in exe_icons] == [16, 32, 48, 256],
            "icônes de l'exécutable",
            str([width for width, _h, _k in exe_icons]),
        )
        exe_strings, exe_numbers = pe_version(folder / "Flow-EDT.exe")
        check(exe_strings.get("ProductName") == "Flow-EDT", "ProductName de l'exe")
        check(exe_strings.get("FileVersion") == VERSION, "FileVersion de l'exe",
              exe_strings.get("FileVersion", ""))
        check(exe_numbers[:4] == (1, 2, 1, 0), "version numérique de l'exe")


def verify_portable() -> None:
    path = DIST / f"FlowEDT-{VERSION}-windows-x64-portable.zip"
    print(f"\nPortable Windows — {path.name}")
    if not path.exists():
        check(False, "présent", "fichier absent")
        return
    check(True, "taille", f"{path.stat().st_size / (1 << 20):.1f} Mo")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        check("Flow-EDT/Flow-EDT.exe" in names, "Flow-EDT/Flow-EDT.exe")
        check("Flow-EDT/portable.txt" in names, "portable.txt")
        check("Flow-EDT/LICENSE.txt" in names, "LICENSE.txt")
        check("Flow-EDT/LICENSES.chromium.html" in names, "LICENSES.chromium.html")
        check(
            not any(name.startswith("Flow-EDT/FlowEDT-data") for name in names),
            "aucune donnée utilisateur embarquée",
        )
        check("Flow-EDT/resources/app/index.html" in names, "resources/app/index.html")
        same = md5(archive.read("Flow-EDT/resources/app/index.html")) == md5(
            (ROOT / "index.html").read_bytes()
        )
        check(same, "index.html identique au dépôt")


def main() -> int:
    print(f"Flow-EDT {VERSION} — vérification de dist/")
    verify_appimage()
    verify_setup()
    verify_portable()
    print()
    if failures:
        print(f"ÉCHECS ({len(failures)}) : " + " · ".join(failures))
        return 1
    print("Tout est conforme.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
