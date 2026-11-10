"""Run the official SiEPIC EBeam DRC deck on a GDS file with the KLayout application.

    python tools/siepic_drc.py results/opa-layout-002/mzi_2x2_siepic.gds [--json out.json]

The deck comes from the siepic_ebeam_pdk wheel pinned (with its hash) in
layout/requirements-drc.txt; its sha256 is checked as well. The deck is run
unchanged except for two added arguments: the layout to check (`source`) and
the report file (`report`), which batch mode needs. KLayout's DRC engine is part
of the application, not of the klayout Python package, so the `klayout` binary
must be installed (Ubuntu 24.04: klayout=0.28.16-0ubuntu0.24.04.1).

Exit status 0 when the layout has no violations. Standard library only.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

REPO = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO / "layout" / "requirements-drc.txt"
DECK_MEMBER = "siepic_ebeam_pdk/drc/SiEPIC_EBeam_DRC.lydrc"
DECK_SHA256 = "341bdbd7c2aa3d67643e1f549a1c6162fdf153ed4831fe2437078b653ccab38b"
REPORT_LINE = 'report("SiEPIC-EBeam-PDK DRC")'
EXPECTED_KLAYOUT = "KLayout 0.28.16"


def fetch_wheel(cache):
    subprocess.run([sys.executable, "-m", "pip", "download", "--quiet", "--no-deps",
                    "--require-hashes", "-r", str(REQUIREMENTS), "-d", str(cache)], check=True)
    wheels = sorted(Path(cache).glob("siepic_ebeam_pdk-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected one siepic_ebeam_pdk wheel in {cache}, found {wheels}")
    return wheels[0]


def deck_text(wheel):
    raw = zipfile.ZipFile(wheel).read(DECK_MEMBER)
    sha = hashlib.sha256(raw).hexdigest()
    if sha != DECK_SHA256:
        raise SystemExit(f"DRC deck sha256 {sha} does not match the pinned {DECK_SHA256}")
    text = html.unescape(re.search(r"<text>(.*)</text>", raw.decode(), re.S).group(1))
    if text.count(REPORT_LINE) != 1:
        raise SystemExit("unexpected deck layout: report() line not found exactly once")
    return text.replace(REPORT_LINE, 'source($input)\nreport("SiEPIC-EBeam-PDK DRC", $report)')


def klayout_version(binary):
    out = subprocess.run([binary, "-v"], capture_output=True, text=True,
                         env=os.environ | {"QT_QPA_PLATFORM": "offscreen"})
    return out.stdout.strip()


def run(gds, binary="klayout", wheel=None, keep_report=None):
    gds = Path(gds).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        wheel = Path(wheel) if wheel else fetch_wheel(tmp)
        deck = tmp / "siepic_ebeam.drc"
        deck.write_text(deck_text(wheel), encoding="utf-8")
        report = Path(keep_report).resolve() if keep_report else tmp / "report.lyrdb"
        proc = subprocess.run([binary, "-b", "-r", str(deck), "-rd", f"input={gds}",
                               "-rd", f"report={report}"], capture_output=True, text=True,
                              env=os.environ | {"QT_QPA_PLATFORM": "offscreen"})
        if proc.returncode != 0 or not report.is_file():
            raise SystemExit(f"KLayout DRC failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
        root = ET.parse(report).getroot()
    rules = {c.findtext("name").strip("'"): c.findtext("description") or ""
             for c in root.iter("category") if c.findtext("name")}
    violations = {}
    for item in root.iter("item"):
        cat = item.findtext("category").strip("'")
        entry = violations.setdefault(cat, {"description": rules.get(cat, ""), "count": 0,
                                            "examples": []})
        entry["count"] += 1
        if len(entry["examples"]) < 5:
            entry["examples"] += [v.text for v in item.iter("value")][:1]
    return {"klayout": klayout_version(binary), "deck": DECK_MEMBER, "deck_sha256": DECK_SHA256,
            "pdk_wheel": wheel.name if wheel else None, "rules": sorted(rules),
            "violations": violations,
            "total_violations": sum(v["count"] for v in violations.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("gds")
    parser.add_argument("--klayout", default="klayout")
    parser.add_argument("--wheel", help="use this siepic_ebeam_pdk wheel instead of downloading")
    parser.add_argument("--json", help="write the summary here")
    parser.add_argument("--report", help="keep the KLayout report database (.lyrdb) here")
    args = parser.parse_args()
    summary = run(args.gds, args.klayout, args.wheel, args.report)
    text = json.dumps(summary, indent=2)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    print(text)
    if summary["klayout"] != EXPECTED_KLAYOUT:
        print(f"WARNING: expected {EXPECTED_KLAYOUT}, found {summary['klayout']}")
    return 1 if summary["total_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
