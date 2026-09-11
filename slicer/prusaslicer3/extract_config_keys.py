#!/usr/bin/env python3
"""
Extrait, depuis les sources de PrusaSlicer 3.0, la liste des options de
configuration et la « boite » a laquelle chacune appartient.

    python3 extract_config_keys.py /chemin/vers/PrusaSlicer > config_keys.json

Pourquoi : PresetEvaluator valide chaque cle contre la classe de reglages
correspondant au 'kind' du preset. Une cle rangee dans la mauvaise boite est
rejetee en silence (erreur non fatale dans le log, valeur ignoree) :

    [error] [PresetEvaluator.cpp:312] Invalid key <option> for Slic3r::Domain::ToolPrintSettings

La correspondance boite <-> kind vient de ConfigBoxesFDM.cpp :

    PrintSettings     -> FDMConfigLocation::Print    -> kind: print
    ToolPrintSettings -> FDMConfigLocation::Tool     -> kind: tool_print
    PrinterSettings   -> FDMConfigLocation::Printer  -> kind: printer
    FilamentSettings  -> FDMConfigLocation::Filament -> kind: material / filament

Une boite contient les options dont 'location' vaut la boite, plus celles dont
'overrides_in' la contient (ConfigOverrides, Config.cpp:196).

Attention : ce n'est PAS Biz/Config/Legacy/PrintConfig.cpp qui fait foi. Ce
fichier-la est le lecteur des profils 2.x ; les presets YAML 3.0 passent par
src/slic3r-domain/.../ConfigDefsFDM.cpp.
"""
import json
import re
import sys
from pathlib import Path

REL = "src/slic3r-domain/src/Slic3r/Domain"
ALIASES = {
    "printer": "Printer", "print": "Print",
    "fdm_tool": "Tool", "fdm_object": "Object", "fdm_volume": "Volume",
    "sla_object": "SLA:Object", "sla_material": "SLA:Material",
}


def normalize(token: str) -> str:
    token = token.strip()
    if token in ALIASES:
        return ALIASES[token]
    token = token.replace("FDMConfigLocation::", "").replace("ConfigLocation{", "")
    token = token.replace("SLAConfigLocation::", "SLA:").replace("}", "")
    return token.strip()


def strip_comments(src: str) -> str:
    """Les blocs commentes contiennent de vrais defs.add() : les retirer."""
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def parse(path: Path, drop_sla_branches: bool) -> dict:
    src = strip_comments(path.read_text("utf-8"))
    # Le suffixe '+ axis.name' est la boucle des limites machine (x, y, z, e).
    parts = re.split(r'def\s*=\s*defs\.add\(\s*"([a-z0-9_]+)"(\s*\+\s*axis\.name)?', src)
    out = {}
    for i in range(1, len(parts), 3):
        name, per_axis, body = parts[i], parts[i + 1], parts[i + 2]
        if drop_sla_branches:
            # ConfigCommon.cpp definit FFF et SLA ensemble ; seul FFF nous interesse.
            body = re.sub(r"if\s*\(technology\s*==\s*SLA\)\s*\{.*?\n\s*\}", "", body, flags=re.S)
            body = re.sub(r"if\s*\(technology\s*==\s*SLA\)\s*\n?\s*def->[^\n]*\n", "\n", body)
            body = re.sub(r"\n\s*else\s*\n?\s*def->overrides_in[^\n]*\n", "\n", body)
            body = re.sub(r"\}\s*else\s*\{.*?\n\s*\}", "", body, flags=re.S)
        locations = {normalize(m.group(1))
                     for m in re.finditer(r"def->location\s*=\s*([^;]+);", body)}
        overrides = set()
        for m in re.finditer(r"def->overrides_in\s*=\s*(?:Locations)?\s*\{([^}]*)\}", body):
            overrides |= {normalize(t) for t in m.group(1).split(",") if t.strip()}
        for key in ([name + axis for axis in "xyze"] if per_axis else [name]):
            out[key] = {"location": sorted(locations), "overrides_in": sorted(overrides)}
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1]) / REL
    if not root.is_dir():
        sys.exit(f"{root} introuvable : passez la racine d'un depot PrusaSlicer 3.0.")

    defs = parse(root / "ConfigCommon.cpp", True)
    defs.update(parse(root / "ConfigDefsFDM.cpp", False))

    orphans = sorted(k for k, v in defs.items() if not v["location"])
    if orphans:
        print(f"attention : sans location -> {', '.join(orphans)}", file=sys.stderr)

    json.dump(defs, sys.stdout, indent=1, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
