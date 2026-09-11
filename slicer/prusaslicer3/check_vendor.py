#!/usr/bin/env python3
"""
Rejoue les invariants que PrusaSlicer 3.0 impose au chargement, pour les
attraper ici plutot que par une imprimante absente de la liste.

    python3 check_vendor.py

Necessite pyyaml. Appele automatiquement par build_source.py s'il est
disponible.

Les regles viennent de :
  HwConfigEvaluator::create_printer_config  (les ASSERT)
  Domain::Preset::suggest_name
  Biz::Preset::IO::PresetLoader / HwConfigLoader
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml requis : pip install pyyaml")

HERE = Path(__file__).parent
SRC = HERE / "vendor"

errors: list[str] = []
notes: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text("utf-8")) if d]


def main() -> None:
    vendor_docs = docs(SRC / "vendor.yaml")
    by_kind: dict[str, list[dict]] = {}
    for d in vendor_docs:
        by_kind.setdefault(d.get("kind", "?"), []).append(d)

    vendors = by_kind.get("vendor", [])
    if len(vendors) != 1:
        err(f"vendor.yaml doit contenir exactement un document 'vendor' (trouve {len(vendors)}).")
        return
    vendor = vendors[0]

    # --- Identite : le nom du .idx doit etre l'id du vendeur -----------------
    idx = HERE / f"{vendor['id']}.idx"
    if not idx.exists():
        err(f"{idx.name} absent : le fichier .idx doit porter l'id du vendeur ({vendor['id']}).")
    else:
        # Attention : les lignes de cle ("min_slic3r_version = ...") contiennent
        # un chiffre, un motif [a-z_]+ les laisserait passer.
        versions = [
            ln.split(" ")[0]
            for ln in (l.strip() for l in idx.read_text("utf-8").splitlines())
            if ln and not ln.startswith("#") and not re.match(r"^[a-z0-9_]+\s*=", ln)
        ]
        if not versions:
            err(f"{idx.name} ne declare aucune version.")
        elif versions[0] != str(vendor.get("version")):
            err(
                f"{idx.name} commence par {versions[0]} alors que vendor.yaml "
                f"annonce {vendor.get('version')}."
            )

    printers = {p["id"]: p for p in by_kind.get("printer", [])}
    tools = {t["id"]: t for t in by_kind.get("tool", [])}
    sheets = {s["id"]: s for s in by_kind.get("sheet", [])}

    if not printers:
        err("Aucun document 'printer'.")
    if not by_kind.get("printer_config"):
        err("Aucun document 'printer_config' : rien n'apparaitra dans la liste des imprimantes.")

    # --- Les ASSERT de create_printer_config ---------------------------------
    for cfg in by_kind.get("printer_config", []):
        cid = cfg.get("id", "?")
        printer = printers.get(cfg.get("printer"))
        if printer is None:
            err(f"printer_config '{cid}' : printer '{cfg.get('printer')}' introuvable "
                f"(ids valides : {', '.join(printers) or 'aucun'}).")
            continue

        tool_count = cfg.get("tool_count", printer.get("tool_count", 1))
        cfg_tools = cfg.get("tools") or []
        # ASSERT(templ.tools.size() == templ.tool_count || templ.tools.size() == 1)
        if len(cfg_tools) not in (1, tool_count):
            err(
                f"printer_config '{cid}' : {len(cfg_tools)} outil(s) declare(s) pour "
                f"tool_count={tool_count}. La liste 'tools' doit en compter 1 "
                f"(repliquee sur tous les emplacements) ou exactement tool_count. "
                f"Le choix du diametre de buse se fait par les documents 'tool', "
                f"pas en allongeant cette liste."
            )
        for entry in cfg_tools:
            tid = entry.get("tool")
            tool = tools.get(tid)
            if tool is None:
                err(f"printer_config '{cid}' : outil '{tid}' introuvable "
                    f"(ids valides : {', '.join(tools) or 'aucun'}).")
            elif tool.get("technology") != printer.get("technology"):
                err(f"printer_config '{cid}' : outil '{tid}' en "
                    f"{tool.get('technology')} contre {printer.get('technology')} pour l'imprimante.")

        if cfg.get("sheet") is not None and cfg["sheet"] not in sheets:
            err(f"printer_config '{cid}' : surface '{cfg['sheet']}' introuvable "
                f"(ids valides : {', '.join(sheets) or 'aucun'}).")

        # suggest_name ecrase le 'name' du printer_config
        nozzle = tools.get(cfg_tools[0]["tool"], {}).get("name", "?") if cfg_tools else "?"
        shown = printer.get("name", "?")
        if tool_count > 1:
            shown += f" {tool_count}T"
        notes.append(f"    {cid:12} -> affiche « {shown} {nozzle} »")

    # --- Presets : heritage et references par nom ----------------------------
    preset_ids: set[str] = set()
    preset_names: dict[str, set[str]] = {}
    preset_docs: list[tuple[str, dict]] = []
    for f in sorted(SRC.glob("*.yaml")):
        if f.name == "vendor.yaml":
            continue
        for d in docs(f):
            preset_docs.append((f.name, d))
            if "id" in d:
                preset_ids.add(d["id"])
            kind = d.get("kind", "?")
            for name in collect_names(d):
                preset_names.setdefault(kind, set()).add(name)

    for fname, d in preset_docs:
        check_value_types(fname, d)
        check_key_ownership(fname, d)

    for fname, d in preset_docs:
        for parent in d.get("inherits", []) or []:
            if parent not in preset_ids:
                err(f"{fname} : '{d.get('id')}' herite de '{parent}', qui n'existe pas.")

    for fname, d in preset_docs:
        for key, kind in (("default_print", "print"), ("default_material", "filament")):
            for ref in collect_values(d, key):
                if ref not in preset_names.get(kind, set()):
                    err(f"{fname} : {key} = '{ref}' ne correspond a aucun preset "
                        f"'{kind}' nomme ({', '.join(sorted(preset_names.get(kind, set()))) or 'aucun'}).")

    # --- Assets references ----------------------------------------------------
    for p in printers.values():
        for key, val in (p.get("visual") or {}).items():
            if val and not (SRC / "assets" / val).exists():
                err(f"printer '{p['id']}' : {key} = '{val}' absent de vendor/assets/.")

    print(f"vendor {vendor['id']} v{vendor.get('version')} — "
          f"{len(printers)} modele(s), {len(tools)} outil(s), "
          f"{len(by_kind.get('printer_config', []))} configuration(s)")
    for n in notes:
        print(n)
    if errors:
        print(f"\n{len(errors)} probleme(s) :", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print("  invariants du chargeur : OK")



# --- Pieges de typage YAML -------------------------------------------------
# Options dont la valeur doit rester une CHAINE : YAML relit "0x0" comme
# l'entier 0 et "0x180" comme 384. Prusa quote systematiquement ces valeurs
# (extruder_offset: ['0x0']). Un entier la ou le chargeur attend un point fait
# echouer tout le bundle, silencieusement : BundleLoader attrape l'exception,
# la journalise, et aucune imprimante n'apparait.
POINT_OPTIONS = {"bed_shape", "extruder_offset"}

# Options devenues des enumerations en 3.0 alors qu'elles etaient booleennes
# ou numeriques en 2.9. Valeurs relevees dans le PrintConfig de l'alpha11.
ENUM_OPTIONS = {
    "support_material": {"none", "enforcers_only", "everywhere"},
    "arc_fitting": {"disabled", "emit_center"},
    "brim_type": {"no_brim", "outer_only", "inner_only", "outer_and_inner"},
    "gcode_label_objects": {"disabled", "octoprint", "firmware"},
    "machine_limits_usage": {"emit_to_gcode", "time_estimate_only", "ignore"},
    "perimeter_generator": {"classic", "arachne"},
    "seam_position": {"random", "nearest", "aligned", "rear"},
    "support_material_style": {"grid", "snug", "organic"},
    "gcode_flavor": {"klipper", "marlin", "marlin2", "reprap", "reprapfirmware",
                     "repetier", "teacup", "makerware", "sailfish", "mach3",
                     "machinekit", "smoothie"},
}


def check_value_types(fname: str, doc) -> None:
    """Valeurs mal typees apres relecture YAML."""
    def visit(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "values" and isinstance(v, dict):
                    for opt, val in v.items():
                        items = val if isinstance(val, list) else [val]
                        if opt in POINT_OPTIONS:
                            for it in items:
                                if not isinstance(it, str):
                                    err(f"{fname} : {opt} = {it!r} ({type(it).__name__}). "
                                        f"YAML a reinterprete la valeur ; entourez chaque "
                                        f"point de quotes simples, par exemple '0x0'.")
                        if opt in ENUM_OPTIONS and isinstance(val, (int, float, bool)):
                            err(f"{fname} : {opt} = {val!r} est numerique alors que "
                                f"l'option est une enumeration en 3.0. Valeurs attendues : "
                                f"{', '.join(sorted(ENUM_OPTIONS[opt]))}.")
                        elif opt in ENUM_OPTIONS and val not in ENUM_OPTIONS[opt]:
                            err(f"{fname} : {opt} = {val!r} hors des valeurs permises "
                                f"({', '.join(sorted(ENUM_OPTIONS[opt]))}).")
                else:
                    visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)
    visit(doc)


# --- Rangement des options par 'kind' --------------------------------------
# PresetEvaluator valide chaque cle contre la classe de reglages qui correspond
# au 'kind' du preset (PresetEvaluator.cpp:312). Une cle rangee ailleurs est
# rejetee sans que le bundle echoue : elle disparait simplement, et le reglage
# ne s'applique pas. Le log ne dit rien d'autre que
#   [error] Invalid key <option> for Slic3r::Domain::<X>Settings
#
# Table produite par extract_config_keys.py depuis ConfigDefsFDM.cpp /
# ConfigCommon.cpp. Ce n'est pas Legacy/PrintConfig.cpp qui fait foi : celui-la
# ne sert qu'a relire les profils 2.x.
KIND_TO_BOX = {
    "printer": "Printer",
    "print": "Print",
    "tool_print": "Tool",
    "material": "Filament",
    "filament": "Filament",
}

_KEY_TABLE: dict | None = None


def key_table() -> dict:
    global _KEY_TABLE
    if _KEY_TABLE is None:
        table = HERE / "config_keys.json"
        _KEY_TABLE = json.loads(table.read_text("utf-8")) if table.exists() else {}
        if not _KEY_TABLE:
            notes.append("    config_keys.json absent : rangement des options non verifie")
    return _KEY_TABLE


def check_key_ownership(fname: str, doc) -> None:
    table = key_table()
    if not table:
        return
    box = KIND_TO_BOX.get(doc.get("kind"))
    if box is None:
        err(f"{fname} : kind '{doc.get('kind')}' inconnu "
            f"(attendu : {', '.join(sorted(KIND_TO_BOX))}).")
        return
    allowed = {k for k, v in table.items()
               if box in v["location"] or box in v["overrides_in"]}

    def visit(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "values" and isinstance(v, dict):
                    for opt in v:
                        if opt in allowed:
                            continue
                        if opt not in table:
                            err(f"{fname} : '{doc.get('id', '?')}' declare l'option "
                                f"'{opt}', inconnue de PrusaSlicer 3.0.")
                        else:
                            homes = table[opt]["location"] + table[opt]["overrides_in"]
                            kinds = sorted({k2 for k2, b in KIND_TO_BOX.items() if b in homes})
                            err(f"{fname} : '{doc.get('id', '?')}' est un preset "
                                f"'{doc.get('kind')}' mais '{opt}' appartient a "
                                f"{', '.join(homes)}. Deplacez-la dans un preset "
                                f"{' ou '.join(kinds) or '(aucun kind de preset)'} : "
                                f"ici elle est ignoree en silence.")
                else:
                    visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)
    visit(doc)


def collect_names(node) -> list[str]:
    """Noms de presets, y compris ceux portes par les variants."""
    out = []
    if isinstance(node, dict):
        if isinstance(node.get("name"), str):
            out.append(node["name"])
        for v in node.get("variants", []) or []:
            out += collect_names(v)
    return out


def collect_values(node, key: str) -> list[str]:
    out = []
    if isinstance(node, dict):
        vals = node.get("values")
        if isinstance(vals, dict) and isinstance(vals.get(key), str):
            out.append(vals[key])
        for v in node.get("variants", []) or []:
            out += collect_values(v, key)
    return out


if __name__ == "__main__":
    main()
