"""Run SiEPIC-Tools functional verification (layout_check) on a GDS file.

    python tools/siepic_verify.py results/opa-layout-003/mzi_2x2_siepic_full.gds [--json out.json]

Needs the environment in layout/requirements-verify.txt (SiEPIC 0.5.31,
siepic_ebeam_pdk 0.4.53, klayout 0.30.6). The layout is checked against the
EBeam technology and its design-for-test rules (DFT.xml).

SiEPIC builds its netlist from SiEPIC pins (PinRec 1/10 paths). Layouts made
with gdsfactory have such pins only in the PDK's fixed cells, so SiEPIC finds
the components but few or no nets, and its connectivity checks (disconnected
and mismatched pins) then cover nothing. This tool therefore reports how many
components, pins and nets SiEPIC found, and says whether connectivity was
covered; the lab checks optical connectivity separately with
layout/port_check.py. What SiEPIC does check on these layouts: component
overlaps, waveguide paths, grating-coupler orientation and pitch, and the
placement of the opt_in measurement label.

Exit status 0 when SiEPIC reports no errors.
"""
import argparse
import collections
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET


def run(gds):
    import pya
    import siepic_ebeam_pdk  # noqa: F401  (registers the EBeam technology)
    import SiEPIC
    from SiEPIC.utils import get_technology_by_name
    from SiEPIC.verification import layout_check

    def load():
        layout = pya.Layout()
        layout.read(str(gds))
        layout.technology_name = "EBeam"
        layout.TECHNOLOGY = get_technology_by_name("EBeam")
        return layout

    layout = load()
    nets, components = layout.top_cell().identify_nets(verbose=False)
    pins = sum(len(c.pins) for c in components)
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "verification.lyrdb"
        fresh = load()      # keep a reference: the cell needs its layout alive
        errors = layout_check(cell=fresh.top_cell(), verbose=False, GUI=True,
                              file_rdb=str(report))
        root = ET.parse(report).getroot()
    by_category = collections.Counter(
        item.findtext("category").replace("'", "") for item in root.iter("item"))
    checked = []

    def walk(node, prefix=""):
        for cat in node.findall("categories/category"):
            name = prefix + cat.findtext("name")
            if not cat.findall("categories/category"):
                checked.append(name)
            walk(cat, name + ".")
    walk(root)
    return {
        "siepic": SiEPIC.__version__,
        "pdk": "siepic_ebeam_pdk " + getattr(siepic_ebeam_pdk, "__version__", "0.4.53"),
        "components": len(components),
        "pins": pins,
        "nets": len(nets),
        "connectivity_covered": len(nets) > 0,
        "errors": int(errors or 0),
        "errors_by_category": dict(sorted(by_category.items())),
        "rules": checked,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("gds")
    parser.add_argument("--json")
    args = parser.parse_args()
    summary = run(args.gds)
    text = json.dumps(summary, indent=2)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
