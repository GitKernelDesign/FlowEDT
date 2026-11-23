#!/usr/bin/env python3
"""Remplace l'icône et le nom de produit d'un exécutable Windows.

L'outil ne touche qu'aux octets des ressources, sans réécrire les sections :
la taille de chaque icône reste identique, donc le PE n'est pas restructuré.
"""
from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

import pefile
from PIL import Image

RT_ICON = 3
RT_VERSION = 16


def dib_from_png(path: Path, size: int) -> bytes:
    """DIB 32 bits au format des ressources RT_ICON (XOR + masque AND)."""
    image = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    pixels = image.load()

    header = struct.pack(
        "<IiiHHIIiiII",
        40,          # biSize
        size,        # biWidth
        size * 2,    # biHeight : XOR + masque
        1,           # biPlanes
        32,          # biBitCount
        0,           # biCompression
        0,           # biSizeImage
        0, 0, 0, 0,  # résolution et couleurs
    )

    xor = bytearray()
    for y in range(size - 1, -1, -1):  # les DIB sont stockés à l'envers
        for x in range(size):
            r, g, b, a = pixels[x, y]
            xor += bytes((b, g, r, a))

    # Masque AND : une ligne d'un octet par pixel, tout à zéro (opaque).
    # C'est la disposition exacte des icônes livrées avec Electron.
    mask = bytes(size * size)
    return header + bytes(xor) + mask


def png_from_png(path: Path, size: int) -> bytes:
    image = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def icon_entries(pe: pefile.PE) -> dict[int, tuple[int, int]]:
    """Identifiant → (offset fichier, taille) de chaque RT_ICON."""
    entries: dict[int, tuple[int, int]] = {}
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id != RT_ICON:
            continue
        for item in entry.directory.entries:
            data = item.directory.entries[0].data.struct
            entries[item.id] = (pe.get_offset_from_rva(data.OffsetToData), data.Size)
    return entries


def version_range(pe: pefile.PE) -> tuple[int, int]:
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id != RT_VERSION:
            continue
        data = entry.directory.entries[0].directory.entries[0].data.struct
        return pe.get_offset_from_rva(data.OffsetToData), data.Size
    raise SystemExit("ressource de version introuvable")


def _align4(value: int) -> int:
    return (value + 3) & ~3


def version_nodes(blob: bytes) -> list[tuple[str, int, int]]:
    """Parcourt un bloc VS_VERSIONINFO : (nom, offset de la valeur, nombre d'octets)."""
    found: list[tuple[str, int, int]] = []

    def walk(start: int, end: int) -> None:
        offset = start
        while offset + 6 <= end:
            length, value_length, _type = struct.unpack_from("<HHH", blob, offset)
            if length < 6 or offset + length > end:
                return
            key_end = offset + 6
            while key_end + 1 < offset + length and blob[key_end : key_end + 2] != b"\0\0":
                key_end += 2
            name = blob[offset + 6 : key_end].decode("utf-16-le", errors="replace")
            value_start = _align4(key_end + 2)
            if _type == 1 and value_length:  # texte
                found.append((name, value_start, value_length * 2))
            else:
                child = _align4(value_start + value_length * (2 if _type == 1 else 1))
                walk(child, offset + length)
            offset = _align4(offset + length)

    walk(0, len(blob))
    return found


def patch_version(region: bytearray, version: str, publisher: str) -> list[str]:
    """Réécrit les chaînes de version sans déplacer les blocs (remplissage NUL)."""
    wanted = {
        "FileVersion": version,
        "ProductVersion": version,
        "InternalName": "Flow-EDT.exe",
        "OriginalFilename": "Flow-EDT.exe",
        "CompanyName": publisher,
        "LegalCopyright": f"Licence GPL-3.0 \u2014 {publisher}",
    }
    changed: list[str] = []
    for name, offset, size in version_nodes(bytes(region)):
        if name not in wanted:
            continue
        encoded = wanted[name].encode("utf-16-le")
        if len(encoded) + 2 > size:  # il faut garder le terminateur
            continue
        region[offset : offset + size] = encoded + bytes(size - len(encoded))
        changed.append(f"{name}={wanted[name]}")
    return changed


def patch_fixed_version(region: bytearray, version: str) -> None:
    """Aligne dwFileVersion / dwProductVersion du bloc VS_FIXEDFILEINFO."""
    parts = [int(part) for part in version.split(".")]
    parts += [0] * (4 - len(parts))
    ms = (parts[0] << 16) | parts[1]
    ls = (parts[2] << 16) | parts[3]
    if region[40:44] != struct.pack("<I", 0xFEEF04BD):
        raise SystemExit("VS_FIXEDFILEINFO inattendu")
    for delta in (8, 16):  # FileVersion puis ProductVersion
        struct.pack_into("<I", region, 40 + delta, ms)
        struct.pack_into("<I", region, 40 + delta + 4, ls)


def main() -> int:
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    icon_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("icons")
    version = sys.argv[4] if len(sys.argv) > 4 else "0.0.0"
    publisher = sys.argv[5] if len(sys.argv) > 5 else "Flow-EDT"

    blob = bytearray(source.read_bytes())
    pe = pefile.PE(data=bytes(blob), fast_load=False)

    by_size = {16: "flowedt-16.png", 32: "flowedt-32.png", 48: "flowedt-48.png"}
    changed = []
    for icon_id, (offset, size) in icon_entries(pe).items():
        if size == 18963 or icon_id == 4:
            payload = png_from_png(icon_dir / "flowedt-256.png", 256)
            label = "256"
        else:
            dimension = {1320: 16, 5160: 32, 11560: 48}[size]
            payload = dib_from_png(icon_dir / by_size[dimension], dimension)
            label = str(dimension)
        if len(payload) > size:
            raise SystemExit(f"icône {label} trop grosse : {len(payload)} > {size}")
        blob[offset : offset + size] = payload + bytes(size - len(payload))
        changed.append(f"{label}px ({len(payload)}/{size} o)")

    start, length = version_range(pe)
    region = bytearray(blob[start : start + length])
    count = region.count("Electron".encode("utf-16-le"))
    region = bytearray(bytes(region).replace("Electron".encode("utf-16-le"), "Flow-EDT".encode("utf-16-le")))
    strings = patch_version(region, version, publisher)
    patch_fixed_version(region, version)
    blob[start : start + length] = region

    target.write_bytes(blob)
    print(f"icônes remplacées : {', '.join(changed)}")
    print(f"chaînes « Electron » → « Flow-EDT » : {count}")
    print(f"version {version} : {', '.join(strings) or 'inchangée'}")
    print(f"écrit : {target} ({len(blob)} octets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
