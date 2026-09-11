#!/usr/bin/env python3
"""
Assemble la source de presets locale pour PrusaSlicer 3.0.

    python3 build_source.py        ->  ekozan-jubilee-source.zip

Structure produite (relevee dans les sources de PrusaSlicer 3.0.0-alpha11,
LocalPresetUpdaterRepository::extract_local_archive_repository) :

    ekozan-jubilee-source.zip
    |- manifest.json              en-tete de la source : name / id / url
    |- vendor_indices.zip         contient Ekozan.idx
    |- Ekozan/1.0.0/
       |- manifest.json           [ { filename, filehash SHA-256 }, ... ]
       |- vendor.yaml
       |- preset-*.yaml
       |- assets/...

Chargement : PrusaSlicer 3.0 > Preset Sources & Updates > Local sources >
ajouter ce zip.

Bibliotheque standard uniquement.
"""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

REPO_ID = "ekozan-jubilee"
REPO_NAME = "Ekozan - Jubilee"
REPO_DESC = "Jubilee toolchanger + nivellement Trident, sous Klipper/KTCC"
# Non utilisee pour une source locale (les fichiers sortent du zip), mais
# le champ est obligatoire dans le manifeste.
REPO_URL = "https://github.com/ekozan/Printer_Data"

VENDOR_ID = "Ekozan"
HERE = Path(__file__).parent
SRC = HERE / "vendor"
IDX = HERE / f"{VENDOR_ID}.idx"
OUT = HERE / f"{REPO_ID}-source.zip"


def vendor_version() -> str:
    """Version declaree dans vendor.yaml (sans dependre de pyyaml)."""
    m = re.search(r"^version:\s*(\S+)\s*$", (SRC / "vendor.yaml").read_text("utf-8"), re.M)
    if not m:
        sys.exit("vendor.yaml : champ 'version' introuvable.")
    return m.group(1)


def idx_versions() -> list[str]:
    out = []
    for line in IDX.read_text("utf-8").splitlines():
        line = line.strip()
        # Les lignes de cle ("min_slic3r_version = ...") ne sont pas des versions.
        if not line or line.startswith("#") or re.match(r"^[a-z0-9_]+\s*=", line):
            continue
        out.append(line.split(" ")[0])
    return out


def main() -> None:
    version = vendor_version()
    versions = idx_versions()
    if version not in versions:
        sys.exit(
            f"Desynchronisation : vendor.yaml annonce {version}, "
            f"absent de {IDX.name} ({', '.join(versions) or 'vide'}).\n"
            f"Ajoutez une ligne '{version} <description>' en tete de {IDX.name}."
        )
    if versions[0] != version:
        sys.exit(
            f"{IDX.name} doit lister la version courante ({version}) en premiere "
            f"ligne, or il commence par {versions[0]}."
        )

    files = sorted(p for p in SRC.rglob("*") if p.is_file())
    if not files:
        sys.exit(f"Aucun fichier dans {SRC}.")

    # Manifeste de version : chemin relatif + SHA-256, recalcule a chaque build.
    manifest = [
        {
            "filename": p.relative_to(SRC).as_posix(),
            "filehash": hashlib.sha256(p.read_bytes()).hexdigest().upper(),
        }
        for p in files
    ]

    base = f"{VENDOR_ID}/{version}"
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "manifest.json",
            json.dumps(
                {
                    "name": REPO_NAME,
                    "id": REPO_ID,
                    "url": REPO_URL,
                    "description": REPO_DESC,
                },
                indent=4,
                ensure_ascii=False,
            ),
        )
        # vendor_indices.zip : un zip imbrique contenant les .idx
        indices = HERE / "vendor_indices.zip"
        with zipfile.ZipFile(indices, "w", zipfile.ZIP_DEFLATED) as zi:
            zi.write(IDX, IDX.name)
        z.write(indices, "vendor_indices.zip")
        indices.unlink()

        z.writestr(f"{base}/manifest.json", json.dumps(manifest, indent=4))
        for p in files:
            z.write(p, f"{base}/{p.relative_to(SRC).as_posix()}")

    size = OUT.stat().st_size
    print(f"{OUT.name}  ({size / 1024:.0f} Ko)")
    print(f"  vendeur {VENDOR_ID} version {version}, {len(files)} fichier(s) :")
    for e in manifest:
        print(f"    {e['filename']}")


if __name__ == "__main__":
    main()
