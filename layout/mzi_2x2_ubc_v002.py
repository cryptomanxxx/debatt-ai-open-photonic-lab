"""OPA-LAYOUT-002: the programmable 2x2 MZI in an open foundry PDK (SiEPIC EBeam).

Same circuit idea as OPA-LAYOUT-001, now built from the cells of an open
silicon-photonics PDK (ubcpdk, the gdsfactory version of the SiEPIC EBeam
PDK, MIT licence) so that it targets a real electron-beam process:

  - two broadband directional couplers (ebeam_bdc_te1550), the PDK's answer to
    the narrow band of a plain directional coupler (see OPA-COUPLER-003),
  - a balanced MZI (delta_length = 0) with a metal heater on one arm,
  - four TE grating couplers (ebeam_gc_te1550) on the standard 127 um fiber-array
    pitch, and bond pads for the heater, via the PDK's add_fiber_array_pads_rf.

ubcpdk 3.3.0 is the newest release without the proprietary gdsfactoryplus
dependency, so it runs in its own locked Python 3.12 environment
(layout/requirements-lock-ubc.txt).

Checks:
  1. four optical fiber ports, same orientation, 127 um pitch,
  2. two electrical pad ports for the heater,
  3. the expected PDK cells: 2 ebeam_bdc_te1550, 4 ebeam_gc_te1550, 1 heater,
  4. equal optical path length in the two MZI arms,
  5. a measurement label with the lab's name (the PDK default is a developer's
     personal username),
  6. only layers defined by the PDK,
  7. a byte-for-byte reproducible GDS,
  8. no violations of the official SiEPIC EBeam DRC deck (tools/siepic_drc.py,
     KLayout 0.28.16, siepic_ebeam_pdk 0.4.53 pinned by hash).

Two additions to the PDK-generated layout make it DRC-clean:
  - a floorplan (FLOORPLAN, 99/0) around the chip; the deck requires every
    silicon shape to lie inside one,
  - M2 extensions over the two heater contacts. The PDK's tapered route leaves
    each 10 x 20 um contact at an angle exactly at the edge of the M1 heater,
    which the deck's 3 um M2-over-M1 overlap rule flags. Each contact's M2 is
    extended 3 um beyond the M1 on every side.

Not done: verification of the broadband coupler, and any measurement.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import gdsfactory as gf
from gdsfactory.config import CONF
import klayout.db as kdb

LAB_USERNAME = "DebattAIOPA"
# ubcpdk reads CONFIG.username into its label defaults at import time, and falls
# back to a developer's personal username; set the lab's name first.
CONF.username = LAB_USERNAME

import ubcpdk  # noqa: E402
from ubcpdk import PDK, cells  # noqa: E402
import yaml  # noqa: E402

OUT = Path("results/opa-layout-002")
FIBER_PITCH = 127.0
TOL = 1e-3
TOP_NAME = "OPA_LAYOUT_002"
M1, M2, FLOORPLAN = (11, 0), (12, 0), (99, 0)
M2_EXTENSION = 3.0          # um, the deck's minimum M2-over-M1 overlap
FLOORPLAN_MARGIN = 5.0      # um around the chip

PDK.activate()


def core_mzi():
    return cells.mzi_heater_2x2(delta_length=0, splitter="ebeam_bdc_te1550",
                                combiner="ebeam_bdc_te1550")


def pdk_chip():
    return cells.add_fiber_array_pads_rf(core_mzi(), orientation=90, username=LAB_USERNAME)


def chip():
    """The PDK-generated chip plus the two DRC additions (floorplan, M2 extensions)."""
    inner = pdk_chip()
    c = gf.Component(TOP_NAME)
    ref = c << inner
    c.add_ports(ref.ports)
    m1 = kdb.Region(inner.begin_shapes_rec(inner.kcl.layer(*M1)))
    m2 = kdb.Region(inner.begin_shapes_rec(inner.kcl.layer(*M2)))
    dbu = inner.kcl.dbu
    ext = round(M2_EXTENSION / dbu)
    for contact in (m1 & m2).merged().each():
        c.shapes(c.kcl.layer(*M2)).insert(contact.bbox().enlarged(ext, ext))
    box = c.dbbox().enlarged(FLOORPLAN_MARGIN, FLOORPLAN_MARGIN)       # um
    c.shapes(c.kcl.layer(*FLOORPLAN)).insert(box)
    return c


def count_cells(component):
    """Count instances of every cell in the full hierarchy."""
    counts = {}

    def walk(cell, multiplier):
        for inst in cell.insts:
            name = inst.cell.name
            counts[name] = counts.get(name, 0) + multiplier
            walk(inst.cell, multiplier)

    walk(component, 1)
    return counts


def matching(counts, prefix):
    return sum(n for name, n in counts.items() if name.startswith(prefix))


def arm_lengths(core):
    """Optical length of each MZI arm, traced through the netlist between the couplers."""
    netlist = core.get_netlist()
    links = {}
    for net in netlist["nets"]:
        links[net["p1"]] = net["p2"]
        links[net["p2"]] = net["p1"]
    names = list(netlist["instances"])
    splitters = sorted(n for n in names if "bdc" in netlist["instances"][n]["component"])
    first, last = splitters[0], splitters[-1]
    if core.insts[first].dcenter[0] > core.insts[last].dcenter[0]:
        first, last = last, first
    starts = [f"{first},{p.name}" for p in core.insts[first].ports
              if p.port_type == "optical" and f"{first},{p.name}" in links
              and links[f"{first},{p.name}"].split(",")[0] != last
              and p.dcenter[0] > core.insts[first].dcenter[0]]
    lengths = {}
    for start in starts:
        total, here, path = 0.0, start, []
        while True:
            name, port = links[here].split(",")
            if name == last:
                break
            inst = core.insts[name]
            info = inst.cell.info
            total += float(info.get("length", info.get("route_info_length", 0.0)))
            other = [p.name for p in inst.ports if p.port_type == "optical" and p.name != port]
            path.append(name)
            here = f"{name},{other[0]}"
        lengths[start] = {"length_um": total, "instances": path}
    return lengths


def gds_texts(path):
    layout = kdb.Layout()
    layout.read(str(path))
    texts, layers = [], set()
    top = layout.top_cells()[0]
    for li in layout.layer_indexes():
        info = layout.get_info(li)
        it = top.begin_shapes_rec(li)
        while not it.at_end():
            layers.add((info.layer, info.datatype))
            if it.shape().is_text():
                texts.append(it.shape().text_string)
            it.next()
    return texts, layers


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = chip()
    gds = OUT / "mzi_2x2_siepic.gds"
    c.write_gds(gds, with_metadata=False)
    sha = hashlib.sha256(gds.read_bytes()).hexdigest()
    checks, failures = {}, []

    def check(name, ok, detail):
        checks[name] = {"passed": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    optical = sorted((p for p in c.ports if p.port_type == "optical"), key=lambda p: -p.dcenter[1])
    ys = [p.dcenter[1] for p in optical]
    pitches = [round(a - b, 6) for a, b in zip(ys, ys[1:])]
    check("four_fiber_ports",
          len(optical) == 4 and len({p.orientation for p in optical}) == 1
          and all(abs(d - FIBER_PITCH) < TOL for d in pitches),
          f"{len(optical)} optical ports, pitches {pitches} um (expected 4 at {FIBER_PITCH} um)")
    electrical = [p for p in c.ports if p.port_type == "electrical"]
    check("heater_pads", len(electrical) == 2,
          f"{len(electrical)} electrical pad ports (expected 2, one per heater terminal)")

    counts = count_cells(c)
    n_bdc = matching(counts, "ebeam_bdc_te1550")
    n_gc = matching(counts, "ebeam_gc_te1550")
    n_heater = matching(counts, "straight_heater_metal")
    check("pdk_cells", n_bdc == 2 and n_gc == 4 and n_heater == 1,
          f"{n_bdc} ebeam_bdc_te1550, {n_gc} ebeam_gc_te1550, {n_heater} heater "
          f"(expected 2, 4, 1)")

    arms = arm_lengths(core_mzi())
    lengths = [a["length_um"] for a in arms.values()]
    check("balanced_arms", len(lengths) == 2 and abs(lengths[0] - lengths[1]) < TOL,
          f"arm lengths {[round(x, 3) for x in lengths]} um")

    texts, layers = gds_texts(gds)
    check("lab_measurement_label",
          any(LAB_USERNAME in t for t in texts) and not any("JoaquinMatres" in t for t in texts),
          f"labels: {texts}")
    pdk_root = Path(ubcpdk.__file__).parent
    pdk_layers = {(layer.layer, layer.datatype) for layer in PDK.layers}
    pdk_layers |= {tuple(v["layer"]) for v in
                   yaml.safe_load((pdk_root / "layers.yaml").read_text()).values()
                   if isinstance(v, dict) and "layer" in v}
    fixed_cell_layers = set()
    for name in ("ebeam_gc_te1550.gds", "ebeam_bdc_te1550.gds"):
        _, fixed = gds_texts(pdk_root / "gds" / "EBeam" / name)
        fixed_cell_layers |= fixed
    unknown = sorted(layers - pdk_layers - fixed_cell_layers)
    only_fixed = sorted((layers - pdk_layers) & fixed_cell_layers)
    check("only_pdk_layers", not unknown,
          f"layers used {sorted(layers)}; outside the PDK layer map but inside the PDK's own "
          f"fixed cells: {only_fixed}; unexplained: {unknown}")

    png = OUT / "mzi_2x2_siepic.png"
    fig = c.plot()
    import matplotlib.pyplot as plt
    (fig if fig is not None and hasattr(fig, "savefig") else plt.gcf()).savefig(
        png, dpi=150, bbox_inches="tight")
    footprint = [round(c.dxsize, 3), round(c.dysize, 3)]

    # Regenerate in a fresh Python process and compare the bytes.
    regenerated = OUT / "mzi_2x2_siepic.check.gds"
    subprocess.run([sys.executable, __file__, "--write-gds", str(regenerated)], check=True,
                   capture_output=True)
    same = hashlib.sha256(regenerated.read_bytes()).hexdigest() == sha
    regenerated.unlink()
    check("gds_reproducible", same,
          "a fresh Python process regenerates a byte-identical GDS file")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import siepic_drc
    drc = siepic_drc.run(gds)
    check("siepic_ebeam_drc_clean",
          drc["total_violations"] == 0 and drc["klayout"] == siepic_drc.EXPECTED_KLAYOUT,
          f"{drc['total_violations']} violations of {len(drc['rules'])} rules "
          f"({drc['klayout']}, {drc['pdk_wheel']}): "
          f"{ {k: v['count'] for k, v in drc['violations'].items()} }")
    m2_added = [[round(v * c.kcl.dbu, 3) for v in (b.left, b.bottom, b.right, b.top)]
                for b in (p.bbox() for p in kdb.Region(c.shapes(c.kcl.layer(*M2))).each())]

    report = {
        "experiment": "OPA-LAYOUT-002",
        "goal": "Programmable 2x2 MZI with broadband couplers, grating couplers and bond "
                "pads in the open SiEPIC EBeam PDK",
        "pdk": f"ubcpdk {ubcpdk.__version__} (SiEPIC EBeam, MIT licence)",
        "gdsfactory_version": gf.__version__,
        "python_version": sys.version.split()[0],
        "gds_file": gds.name,
        "gds_sha256": sha,
        "footprint_um": footprint,
        "fiber_ports_um": [[round(p.dcenter[0], 3), round(p.dcenter[1], 3)] for p in optical],
        "arms": arms,
        "cell_counts": {"ebeam_bdc_te1550": n_bdc, "ebeam_gc_te1550": n_gc,
                        "straight_heater_metal": n_heater},
        "labels": texts,
        "layers": sorted(layers),
        "drc": drc,
        "drc_additions": {
            "floorplan_um": [round(c.dxsize, 3), round(c.dysize, 3)],
            "m2_extensions": m2_added,
            "why": "floorplan: the deck requires all Si inside FLOORPLAN; M2 extensions: the "
                   "PDK route leaves each heater contact at an angle at the M1 edge, which "
                   "fails the 3 um M2-over-M1 overlap rule",
        },
        "checks": checks,
        "failures": failures,
        "limitations": [
            "DRC covers the SiEPIC EBeam deck's geometric rules only; SiEPIC's functional "
            "verification (waveguide connectivity, pins, component models) has not been run",
            "The broadband coupler's split has not been verified; ubcpdk has no compact "
            "model for it",
            "Only one arm has a heater, so only theta is tunable; there are no phi, a or b "
            "phase shifters as in OPA-LAYOUT-001",
            "The grating-coupler model in ubcpdk is a generic placeholder (6 dB, 35 nm), "
            "not measured data",
            "Not submitted to or checked by the foundry",
        ],
    }
    (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sheet = {
        "id": "OPA-LAYOUT-002",
        "title": "2x2 MZI with broadband couplers, fiber array and pads (SiEPIC EBeam)",
        "function": "tunable 2x2 MZI switch / splitter (theta only)",
        "status": "drc-clean" if not failures else "exploratory",
        "pdk": {"name": "SiEPIC EBeam (ubcpdk)", "version": ubcpdk.__version__,
                "open_source": True, "platform": "Si 220 nm SOI, electron-beam lithography"},
        "wavelength_um": {"design": 1.55},
        "footprint_um": footprint,
        "optical_ports": {"inputs": 2, "outputs": 2, "type": "TE grating coupler",
                          "pitch_um": FIBER_PITCH},
        "controls": {"heaters": 1, "bond pads": 2},
        "files": {"gds": gds.name, "preview": png.name},
        "generator": {"script": "layout/mzi_2x2_ubc_v002.py",
                      "environment": "layout/requirements-lock-ubc.txt"},
        "checks": {"passed": len(checks) - len(failures), "total": len(checks)},
        "key_results": [
            {"name": "Splitters", "value": "2 x ebeam_bdc_te1550 broadband directional "
             "coupler (PDK fixed cell, not verified here)", "source": "OPA-LAYOUT-002"},
            {"name": "Fiber I/O", "value": f"4 TE grating couplers at {FIBER_PITCH:g} um pitch",
             "source": "OPA-LAYOUT-002"},
            {"name": "Arm balance", "value": f"arms {round(lengths[0], 3)} / "
             f"{round(lengths[1], 3)} um", "source": "OPA-LAYOUT-002"},
            {"name": "Grating coupler", "value": "PDK placeholder model: 6 dB, 35 nm "
             "bandwidth (not measured)", "source": "ubcpdk.models.gc_te1550"},
            {"name": "SiEPIC EBeam DRC", "value": f"{drc['total_violations']} violations of "
             f"{len(drc['rules'])} rules ({drc['klayout']})", "source": "tools/siepic_drc.py"},
        ],
        "limitations": ["SiEPIC functional verification not run", "broadband coupler not verified",
                        "theta only (no phi, a, b)", "not submitted"],
        "tags": ["mzi", "2x2", "phase-shifter", "broadband-coupler", "grating-coupler",
                 "bond-pads", "siepic", "ebeam", "silicon", "open-pdk"],
    }
    (OUT / "design.json").write_text(json.dumps(sheet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit("OPA-LAYOUT-002 failed checks: " + ", ".join(failures))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--write-gds":
        chip().write_gds(sys.argv[2], with_metadata=False)
    else:
        main()
