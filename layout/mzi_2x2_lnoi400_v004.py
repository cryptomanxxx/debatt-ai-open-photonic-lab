"""OPA-LAYOUT-004: passive 2x2 MZI in Luxtelligence lnoi400 (thin-film lithium niobate).

The lab sent OPA 0.24 (gds/opa-p-passive-mzi-v0.24-eurocdp) to EuroCDP: a passive
2x2 MZI in the open lnoi400 PDK (lxt_pdk_gf, MIT), made outside this repository.
This script rebuilds that chip from the PDK so that it can be regenerated and
checked here, and adds what 0.24 lacked:

  - the PDK's chip frame (10 x 5 mm die; contour 6/0 and edge exclusion zone 6/1),
  - port labels at the four facets,
  - the lab's checks, run in CI.

The chip, as in 0.24: four double linear inverse tapers (edge couplers) on two
facets 10 mm apart, 127 um apart on each facet; straights and 1.2 mm S-bends to
the PDK's MZI (_mzm_interferometer with mmi2x2_optimized1550 couplers, 450 um
arms, no electrodes, balanced: length_imbalance = 0).

Everything outside the MZI matches 0.24 exactly (check 7). Inside the MZI the
two bias arms of 0.24 sit about 10 um closer to the axis, and some bend points
differ by tenths of a micron, a result that every PDK release since v1.3.0
and gdsfactory 9.34 and 9.51 reproduce; 0.24 must have used a non-default
MZI parameter that the GDS does not record.

Checks:
  1. four facet ports on the two chip edges, 127 um apart on each,
  2. the expected PDK cells: 4 edge couplers, 1 MZI,
  3. every optical port of every instance connected (layout/port_check.py),
  4. all LN shapes inside the chip frame; only edge couplers in the exclusion zone,
  5. only lnoi400 layers,
  6. a text label at each facet port,
  7. identical to 0.24 outside the MZI (XOR on every LN layer),
  8. a byte-for-byte reproducible GDS.

Not done: the lnoi400 DRC (its runset is distributed by Luxtelligence on
request), optical simulation of the chip, and any foundry review.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import gdsfactory as gf
import klayout.db as kdb
import lnoi400
from lnoi400.cells import _mzm_interferometer
from lnoi400.tech import LAYER

sys.path.insert(0, str(Path(__file__).resolve().parent))
from port_check import optical_port_check  # noqa: E402

OUT = Path("results/opa-layout-004")
NAME = "OPA_LAYOUT_004"
V024 = Path("gds/opa-p-passive-mzi-v0.24-eurocdp/opa_p_four_facet_ports_exploratory.gds")
PDK_COMMIT = "d16db6a4882657feb1ce696c16c604ff6cb7ccfa"
XS = "xs_rwg1000"
DIE = (10_000.0, 5_000.0)
FIBER_PITCH = 127.0
LN_LAYERS = ((2, 0), (3, 0), (3, 1))           # LN_RIDGE, LN_SLAB, SLAB_NEGATIVE
CONTOUR, EXCLUSION, LABELS = (6, 0), (6, 1), (4, 0)
MZI = dict(splitter="mmi2x2_optimized1550", taper_length=100.0, rib_core_width_modulator=2.5,
           modulation_length=450.0, length_imbalance=0.0)
MZI_ORIGIN = (2525.0, 2026.75)
# per input/output pair: facet y, S-bend offset to the MZI input, MZI input port,
# S-bend offset from the MZI output, MZI output port (all from OPA 0.24)
ROUTES = ((1750.0, 275.0, "o1", -320.0, "o2"), (1877.0, 151.5, "in2", -196.5, "out2"))
EC_LENGTH, IN_STRAIGHT, SBEND_LENGTH, OUT_STRAIGHT = 360.0, 940.0, 1200.0, 3552.0
TOL = 1e-3
# reference ports inside the PDK's MZI cell (where electrodes would go), not waveguide ends
MZI_MARKER_PORTS = ("upper_taper_start", "short_bias_branch_start", "long_bias_branch_start")


def chip():
    c = gf.Component(NAME)
    c << gf.get_component("chip_frame", size=DIE, center=(DIE[0] / 2, DIE[1] / 2))
    mzi = c << _mzm_interferometer(**MZI)
    mzi.dmove(MZI_ORIGIN)
    ec = gf.get_component("double_linear_inverse_taper")
    for k, (y, dy_in, port_in, dy_out, port_out) in enumerate(ROUTES, start=1):
        e_in = c << ec
        e_in.dmove((0.0, y))
        s_in = c << gf.components.straight(length=IN_STRAIGHT, cross_section=XS)
        s_in.connect("o1", e_in.ports["o2"])
        b_in = c << gf.components.bend_s(size=(SBEND_LENGTH, dy_in), cross_section=XS)
        b_in.connect("o1", s_in.ports["o2"])
        b_out = c << gf.components.bend_s(size=(SBEND_LENGTH, dy_out), cross_section=XS)
        b_out.connect("o1", mzi.ports[port_out])
        s_out = c << gf.components.straight(length=OUT_STRAIGHT, cross_section=XS)
        s_out.connect("o1", b_out.ports["o2"])
        e_out = c << ec
        e_out.connect("o2", s_out.ports["o2"])
        c.add_port(f"in{k}", port=e_in.ports["o1"])
        c.add_port(f"out{k}", port=e_out.ports["o1"])
        # the input S-bend must land on the MZI port (checked again by port_check)
        assert abs(b_in.ports["o2"].dcenter[1] - mzi.ports[port_in].dcenter[1]) < TOL
    for p in c.ports:
        c.add_label(text=p.name, position=p.dcenter, layer=LABELS)
    return c


def region(layout, cell, layer):
    li = layout.find_layer(*layer)
    if li is None:
        return kdb.Region()
    return kdb.Region(cell.begin_shapes_rec(li)).merged()


def count_cells(component):
    counts = {}

    def walk(cell):
        for inst in cell.insts:
            counts[inst.cell.name] = counts.get(inst.cell.name, 0) + 1
            walk(inst.cell)
    walk(component)
    return counts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = chip()
    gds = OUT / "mzi_2x2_lnoi400.gds"
    c.write_gds(gds, with_metadata=False)
    sha = hashlib.sha256(gds.read_bytes()).hexdigest()
    checks, failures = {}, []

    def check(name, ok, detail):
        checks[name] = {"passed": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    ly = kdb.Layout()
    ly.read(str(gds))
    top = ly.top_cells()[0]
    contour = region(ly, top, CONTOUR)
    exclusion = region(ly, top, EXCLUSION)
    cbox = contour.bbox().to_dtype(ly.dbu)

    ports = {p.name: p for p in c.ports}
    left = sorted(p.dcenter[1] for p in c.ports if abs(p.dcenter[0] - cbox.left) < TOL)
    right = sorted(p.dcenter[1] for p in c.ports if abs(p.dcenter[0] - cbox.right) < TOL)
    check("facet_ports",
          len(ports) == 4 and len(left) == 2 and len(right) == 2
          and abs(left[1] - left[0] - FIBER_PITCH) < TOL
          and abs(right[1] - right[0] - FIBER_PITCH) < TOL,
          f"ports {[(n, [round(v, 3) for v in p.dcenter]) for n, p in sorted(ports.items())]}; "
          f"chip contour x {cbox.left}..{cbox.right} um")

    counts = count_cells(c)
    n_ec = sum(n for k, n in counts.items() if k.startswith("double_linear_inverse_taper"))
    n_mzi = sum(n for k, n in counts.items() if k.startswith("_mzm_interferometer"))
    check("pdk_cells", n_ec == 4 and n_mzi == 1,
          f"{n_ec} double_linear_inverse_taper, {n_mzi} _mzm_interferometer (expected 4, 1)")

    n_ports, port_problems = optical_port_check(c, ignore_ports=MZI_MARKER_PORTS)
    check("optical_ports_connected", n_ports > 0 and not port_problems,
          f"{n_ports} optical instance ports checked in every cell (ignoring the MZI's "
          f"marker ports {list(MZI_MARKER_PORTS)}); problems: {port_problems or 'none'} "
          f"(layout/port_check.py)")

    ln = kdb.Region()
    for layer in LN_LAYERS:
        ln += region(ly, top, layer)
    ln.merge()
    outside_frame = ln - (contour + exclusion).merged()
    ec_boxes = kdb.Region()
    for inst in top.each_inst():
        if inst.cell.name.startswith("double_linear_inverse_taper"):
            ec_boxes.insert(inst.bbox())
    in_exclusion = (ln - contour) - ec_boxes
    check("inside_chip_frame", outside_frame.is_empty() and in_exclusion.is_empty(),
          f"LN area outside the frame {outside_frame.area() * ly.dbu ** 2:.3f} um2; "
          f"non-edge-coupler LN area in the exclusion zone "
          f"{in_exclusion.area() * ly.dbu ** 2:.3f} um2")

    pdk_layers = {(layer.layer, layer.datatype) for layer in LAYER}
    used = sorted({(ly.get_info(i).layer, ly.get_info(i).datatype) for i in ly.layer_indexes()
                   if not top.begin_shapes_rec(i).at_end()})
    unknown = [lay for lay in used if lay not in pdk_layers]
    check("only_lnoi400_layers", not unknown, f"layers used {used}; unknown {unknown}")

    labels = {}
    it = top.begin_shapes_rec(ly.find_layer(*LABELS))
    while not it.at_end():
        if it.shape().is_text():
            t = it.shape().text.transformed(it.trans())
            labels[it.shape().text_string] = (t.x * ly.dbu, t.y * ly.dbu)
        it.next()
    label_ok = all(n in labels and abs(labels[n][0] - p.dcenter[0]) < TOL
                   and abs(labels[n][1] - p.dcenter[1]) < TOL for n, p in ports.items())
    check("port_labels", label_ok, f"labels {labels}")

    ref = kdb.Layout()
    ref.read(str(V024))
    rtop = ref.top_cells()[0]
    mzi_box = [inst.bbox() for inst in top.each_inst()
               if inst.cell.name.startswith("_mzm_interferometer")][0]
    mzi_region = kdb.Region(mzi_box)
    outside, inside = {}, {}
    for layer in LN_LAYERS:
        x = region(ly, top, layer) ^ region(ref, rtop, layer)
        outside[f"{layer[0]}/{layer[1]}"] = round((x - mzi_region).area() * ly.dbu ** 2, 6)
        inside[f"{layer[0]}/{layer[1]}"] = round((x & mzi_region).area() * ly.dbu ** 2, 3)
    check("matches_v024_outside_mzi", all(v == 0 for v in outside.values()),
          f"XOR area outside the MZI (um2) {outside}; inside the MZI {inside}")

    regenerated = OUT / "mzi_2x2_lnoi400.check.gds"
    subprocess.run([sys.executable, __file__, "--write-gds", str(regenerated)], check=True,
                   capture_output=True)
    same = hashlib.sha256(regenerated.read_bytes()).hexdigest() == sha
    regenerated.unlink()
    check("gds_reproducible", same, "a fresh Python process regenerates a byte-identical GDS file")

    png = OUT / "mzi_2x2_lnoi400.png"
    fig = c.plot()
    import matplotlib.pyplot as plt
    (fig if fig is not None and hasattr(fig, "savefig") else plt.gcf()).savefig(
        png, dpi=150, bbox_inches="tight")
    frame = [round(cbox.width(), 3), round(cbox.height(), 3)]

    report = {
        "experiment": "OPA-LAYOUT-004",
        "goal": "Passive 2x2 MZI in Luxtelligence lnoi400, rebuilt from the PDK so that the "
                "chip sent to EuroCDP as OPA 0.24 can be regenerated and checked",
        "pdk": f"lxt_pdk_gf {getattr(lnoi400, '__version__', '2.0')} at commit {PDK_COMMIT} (MIT)",
        "gdsfactory_version": gf.__version__,
        "python_version": sys.version.split()[0],
        "gds_file": gds.name,
        "gds_sha256": sha,
        "chip_frame_um": frame,
        "mzi": MZI,
        "facet_ports_um": {n: [round(v, 3) for v in p.dcenter] for n, p in sorted(ports.items())},
        "cell_counts": {"double_linear_inverse_taper": n_ec, "_mzm_interferometer": n_mzi},
        "layers": used,
        "comparison_with_v024": {"xor_outside_mzi_um2": outside, "xor_inside_mzi_um2": inside,
                                 "reference": str(V024)},
        "checks": checks,
        "failures": failures,
        "limitations": [
            "Not checked against the lnoi400 DRC; Luxtelligence distributes the runset on "
            "request",
            "Inside the MZI the bias arms differ from OPA 0.24 by about 10 um; 0.24 used a "
            "non-default MZI parameter that its GDS does not record",
            "The two input routes and the two output routes differ in length (S-bends of "
            "different offsets), which adds a fixed phase that a passive MZI cannot remove",
            "Passive: no electrodes or heaters",
            "No optical simulation of the chip; the MMI and edge-coupler performance is the "
            "PDK's",
        ],
    }
    (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sheet = {
        "id": "OPA-LAYOUT-004",
        "title": "Passive 2x2 MZI with edge couplers on a 10 x 5 mm die (Luxtelligence lnoi400)",
        "function": "passive 2x2 Mach-Zehnder interferometer (fixed splitting)",
        "status": "exploratory",
        "pdk": {"name": "Luxtelligence lnoi400 (lxt_pdk_gf)", "version": f"2.0 @ {PDK_COMMIT[:7]}",
                "open_source": True, "platform": "X-cut thin-film lithium niobate on insulator"},
        "wavelength_um": {"design": 1.55},
        "footprint_um": frame,
        "optical_ports": {"inputs": 2, "outputs": 2, "type": "edge coupler (inverse taper)",
                          "pitch_um": FIBER_PITCH},
        "controls": {},
        "files": {"gds": gds.name, "preview": png.name},
        "generator": {"script": "layout/mzi_2x2_lnoi400_v004.py",
                      "environment": "layout/requirements-lock-lnoi400.txt"},
        "checks": {"passed": len(checks) - len(failures), "total": len(checks)},
        "key_results": [
            {"name": "Couplers", "value": "2 x mmi2x2_optimized1550 (PDK)", "source": "OPA-LAYOUT-004"},
            {"name": "Fiber I/O", "value": "4 double linear inverse tapers, 127 um pitch on two "
             "facets 10 mm apart", "source": "OPA-LAYOUT-004"},
            {"name": "Optical connectivity", "value": f"{n_ports} instance ports, all connected",
             "source": "layout/port_check.py"},
            {"name": "Relation to OPA 0.24", "value": "identical outside the MZI (XOR 0); bias "
             "arms inside differ", "source": "gds/opa-p-passive-mzi-v0.24-eurocdp"},
        ],
        "limitations": ["lnoi400 DRC not run (runset on request)", "passive", "input and output "
                        "routes unequal in length", "not simulated"],
        "tags": ["mzi", "2x2", "passive", "mmi", "edge-coupler", "lnoi400", "tfln",
                 "lithium-niobate", "luxtelligence", "eurocdp", "open-pdk"],
    }
    (OUT / "design.json").write_text(json.dumps(sheet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "limitations"}, indent=2))
    if failures:
        raise SystemExit("OPA-LAYOUT-004 failed checks: " + ", ".join(failures))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--write-gds":
        chip().write_gds(sys.argv[2], with_metadata=False)
    else:
        main()
