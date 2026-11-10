"""Build the design catalog from every design datasheet in results/.

Each layout script writes a `design.json` datasheet next to its GDS file
(see catalog/SCHEMA.md). This script collects them into

    catalog/README.md     a table with a preview of every design, readable on GitHub
    catalog/designs.json  the same data for search and filtering

Usage:
    python tools/build_catalog.py           # rebuild the catalog
    python tools/build_catalog.py --check   # fail if a datasheet is invalid or the
                                            # catalog is out of date (used in CI)

Standard library only.
"""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / "catalog"
STATUSES = ("exploratory", "drc-clean", "submitted", "fabricated")
REQUIRED = {
    "id": str, "title": str, "function": str, "status": str, "pdk": dict,
    "wavelength_um": dict, "footprint_um": list, "optical_ports": dict,
    "controls": dict, "files": dict, "generator": dict, "checks": dict,
    "key_results": list, "limitations": list, "tags": list,
}


def _text(v):
    return isinstance(v, str) and v.strip() != ""


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def cell(value):
    """Datasheet text made safe for one Markdown table cell or list line."""
    text = " ".join(str(value).split())
    return text.replace("\\", "\\\\").replace("|", "\\|")


def validate(path, sheet):
    errors = []
    for key, kind in REQUIRED.items():
        if key not in sheet:
            errors.append(f"{path}: missing '{key}'")
        elif not isinstance(sheet[key], kind):
            errors.append(f"{path}: '{key}' must be a {kind.__name__}")
    if errors:
        return errors
    if sheet["status"] not in STATUSES:
        errors.append(f"{path}: status must be one of {STATUSES}")
    if not _text(sheet["pdk"].get("name")):
        errors.append(f"{path}: pdk.name must be a non-empty string")
    if not isinstance(sheet["pdk"].get("open_source"), bool):
        errors.append(f"{path}: pdk.open_source must be true or false")
    if not _number(sheet["wavelength_um"].get("design")):
        errors.append(f"{path}: wavelength_um.design must be a number")
    band = sheet["wavelength_um"].get("band")
    if band is not None and not (isinstance(band, list) and len(band) == 2
                                 and all(_number(b) for b in band)):
        errors.append(f"{path}: wavelength_um.band must be [min, max]")
    fp = sheet["footprint_um"]
    if len(fp) != 2 or not all(_number(v) for v in fp):
        errors.append(f"{path}: footprint_um must be two numbers [x, y]")
    for key in ("inputs", "outputs"):
        v = sheet["optical_ports"].get(key)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            errors.append(f"{path}: optical_ports.{key} must be a non-negative integer")
    for key, v in sheet["controls"].items():
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            errors.append(f"{path}: controls.{key} must be a non-negative integer")
    for key in ("script", "environment"):
        if not _text(sheet["generator"].get(key)):
            errors.append(f"{path}: generator.{key} must be a non-empty string")
    for key in ("id", "title", "function"):
        if not _text(sheet[key]):
            errors.append(f"{path}: '{key}' must be a non-empty string")
    if "supersedes" in sheet and not _text(sheet["supersedes"]):
        errors.append(f"{path}: 'supersedes' must be a non-empty design id")
    for key in ("limitations", "tags"):
        if not all(_text(v) for v in sheet[key]):
            errors.append(f"{path}: every item in '{key}' must be a non-empty string")
    for key in ("gds", "preview"):
        rel = sheet["files"].get(key)
        if not rel:
            errors.append(f"{path}: files.{key} is required")
        elif not (path.parent / rel).is_file():
            errors.append(f"{path}: files.{key} '{rel}' does not exist")
    for key in ("passed", "total"):
        v = sheet["checks"].get(key)
        if not isinstance(v, int) or isinstance(v, bool):
            errors.append(f"{path}: checks.{key} must be an integer")
    for i, item in enumerate(sheet["key_results"]):
        if not isinstance(item, dict) or not all(k in item for k in ("name", "value", "source")):
            errors.append(f"{path}: key_results[{i}] needs name, value and source")
    return errors


def collect():
    sheets, errors = [], []
    for path in sorted(REPO.glob("results/*/design.json")):
        try:
            sheet = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON ({exc})")
            continue
        problems = validate(path, sheet)
        errors += problems
        if not problems:
            sheet["_folder"] = path.parent.relative_to(REPO).as_posix()
            sheets.append(sheet)
    ids = [s["id"] for s in sheets]
    errors += [f"duplicate design id '{i}'" for i in sorted({i for i in ids if ids.count(i) > 1})]
    for s in sheets:
        old = s.get("supersedes")
        if old is not None and old not in ids:
            errors.append(f"{s['id']}: supersedes unknown design id '{old}'")
        elif old == s["id"]:
            errors.append(f"{s['id']}: a design cannot supersede itself")
    return sorted(sheets, key=lambda s: s["id"]), errors


def fmt_wavelength(w):
    if "band" in w:
        return f"{w['design']} ({w['band'][0]}–{w['band'][1]})"
    return str(w.get("design", "–"))


def render_markdown(sheets):
    lines = [
        "# Design catalog",
        "",
        "Every chip layout in the lab, generated from the `design.json` datasheet that "
        "each layout script writes next to its GDS file. Do not edit this file by hand: "
        "run `python tools/build_catalog.py`. The same data is in "
        "[`designs.json`](designs.json) for search and filtering; the datasheet fields "
        "are described in [`SCHEMA.md`](SCHEMA.md).",
        "",
        f"{len(sheets)} design(s).",
        "",
        "| Preview | Design | Function | PDK | λ (µm) | Footprint (µm) | Ports | Controls | Status | Checks |",
        "|---------|--------|----------|-----|--------|----------------|-------|----------|--------|--------|",
    ]
    for s in sheets:
        folder = s["_folder"]
        preview = f"[<img src=\"../{folder}/{s['files']['preview']}\" width=\"220\">](../{folder}/{s['files']['preview']})"
        name = f"**[{cell(s['id'])}](../{folder}/)**<br>{cell(s['title'])}"
        pdk = cell(s["pdk"]["name"]) + ("" if s["pdk"]["open_source"] else " (closed)")
        ports = f"{s['optical_ports']['inputs']} in / {s['optical_ports']['outputs']} out"
        controls = ", ".join(f"{v} {cell(k)}" for k, v in s["controls"].items()) or "–"
        size = " × ".join(f"{v:g}" for v in s["footprint_um"])
        checks = f"{s['checks']['passed']}/{s['checks']['total']}"
        lines.append(f"| {preview} | {name} | {cell(s['function'])} | {pdk} | "
                     f"{fmt_wavelength(s['wavelength_um'])} | {size} | {ports} | {controls} | "
                     f"{cell(s['status'])} | {checks} |")
    lines += ["", "## Key results", ""]
    for s in sheets:
        lines.append(f"### {cell(s['id'])}: {cell(s['title'])}")
        lines.append("")
        lineage = []
        if s.get("supersedes"):
            lineage.append(f"Supersedes: {cell(s['supersedes'])}")
        newer = [t["id"] for t in sheets if t.get("supersedes") == s["id"]]
        if newer:
            lineage.append("Superseded by: " + ", ".join(cell(n) for n in newer))
        if lineage:
            lines.append(" · ".join(lineage))
            lines.append("")
        lines.append("Tags: " + ", ".join(f"`{cell(t)}`" for t in s["tags"]))
        lines.append("")
        for r in s["key_results"]:
            lines.append(f"- **{cell(r['name'])}:** {cell(r['value'])} ({cell(r['source'])})")
        lines.append("")
        lines.append("Limitations: " + "; ".join(cell(x) for x in s["limitations"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(sheets):
    clean = [{k: v for k, v in s.items() if k != "_folder"} | {"folder": s["_folder"]}
             for s in sheets]
    return json.dumps({"designs": clean}, indent=2, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="fail if a datasheet is invalid or the catalog is out of date")
    args = parser.parse_args()
    sheets, errors = collect()
    outputs = {CATALOG / "README.md": render_markdown(sheets),
               CATALOG / "designs.json": render_json(sheets)}
    if args.check:
        for path, text in outputs.items():
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                errors.append(f"{path.relative_to(REPO)} is out of date; run "
                              f"python tools/build_catalog.py")
    else:
        CATALOG.mkdir(exist_ok=True)
        for path, text in outputs.items():
            path.write_text(text, encoding="utf-8")
    for e in errors:
        print("ERROR:", e)
    print(f"{len(sheets)} design(s), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
