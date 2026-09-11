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
