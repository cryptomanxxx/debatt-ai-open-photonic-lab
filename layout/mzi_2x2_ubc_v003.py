"""OPA-LAYOUT-003: fully programmable 2x2 MZI (theta, phi, a, b) in SiEPIC EBeam.

OPA-LAYOUT-002 tunes only theta. This version adds the three other phase
shifters of the lab's MZI convention (simulations/circuit/mzi.py):

    U = diag(e^ia, e^ib) . coupler . phase(theta) . coupler . phase(phi)

  - phi: a metal heater on the top input arm, with an unheated straight of the
    same length on the bottom input arm,
  - theta: the PDK's heater inside mzi_heater_2x2 (as in OPA-LAYOUT-002),
  - a, b: metal heaters on both output arms.

The four arms outside the MZI fan out with S-bends to +-25 um, so neighbouring
heaters sit 50 um apart. Each heater terminal gets its own 90 um pad and a
straight tapered M2 lead (eight pads: six on one side for phi, theta and a,
two on the other for b), so no lead crosses another heater. The PDK's
add_fiber_array adds the four TE grating couplers at 127 um pitch and the
measurement label. DRC additions, as in OPA-LAYOUT-002: a floorplan, and M2
extended 3 um beyond M1 at every contact. Each lead starts at the outer edge
of that extension, as wide as it (26 um), so no M2 edge crosses M1 at an angle
(the 3 um M2-over-M1 overlap rule) and the lead's widening sides leave no
narrow notch (the 8 um M2 spacing rule).

Checks:
  1. four optical fiber ports, same orientation, 127 um pitch,
  2. eight electrical pads,
  3. the expected PDK cells: 2 ebeam_bdc_te1550, 4 ebeam_gc_te1550, 4 heaters,
  4. equal optical length in the two MZI arms,
  5. equal optical length in the two input arms and in the two output arms,
  6. a measurement label with the lab's name,
  7. only layers defined by the PDK,
  8. electrical isolation: eight separate M2 nets, each reaching exactly one
     heater, and each heater reached by exactly two nets (no shorts, no opens),
  9. layout hygiene: heaters at least 40 um apart, and no silicon under a pad
     opening,
 10. a byte-for-byte reproducible GDS,
 11. no violations of the official SiEPIC EBeam DRC deck (tools/siepic_drc.py).

Not done: thermal crosstalk between heaters, verification of the broadband
coupler, SiEPIC's functional verification, and any measurement.
"""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
# importing OPA-LAYOUT-002 sets the lab username before ubcpdk loads and
# activates the PDK; its helper functions are reused below
import mzi_2x2_ubc_v002 as v002  # noqa: E402
import gdsfactory as gf  # noqa: E402
import klayout.db as kdb  # noqa: E402
import ubcpdk  # noqa: E402
from ubcpdk import PDK, cells  # noqa: E402
from ubcpdk.cells.containers import add_label_electrical  # noqa: E402
import yaml  # noqa: E402

OUT = Path("results/opa-layout-003")
NAME = "OPA_LAYOUT_003"
FIBER_PITCH = 127.0
TOL = 1e-3
HEATER_L = 200.0            # um, as the theta heater (mzi_heater_2x2 length_x 200)
FAN = 25.0                  # um, arm offset from the MZI axis outside the MZI
SB_L = 60.0                 # um, S-bend length
PAD_GAP = 80.0              # um, heater contact to pad edge
MIN_HEATER_GAP = 40.0       # um, edge to edge
SI, M1, M2, PAD_OPEN, FLOORPLAN = (1, 0), (11, 0), (12, 0), (13, 0), (99, 0)
M2_EXTENSION = 3.0
FLOORPLAN_MARGIN = 5.0


def mzi():
    return cells.mzi_heater_2x2(delta_length=0, splitter="ebeam_bdc_te1550",
                                combiner="ebeam_bdc_te1550")


def core():
    """MZI with phi (input) and a, b (output) heaters; returns (component, parts)."""
    c = gf.Component(f"{NAME}_core")
    m = c << mzi()
    dy = FAN - abs(m.ports["o2"].dcenter[1])

    def sbend(sign):
        return gf.components.bend_s(size=(SB_L, sign * dy), cross_section="strip")

    s_in_top, s_in_bot = c << sbend(-1), c << sbend(+1)
    s_in_top.connect("o2", m.ports["o2"])
    s_in_bot.connect("o2", m.ports["o1"])
    s_out_top, s_out_bot = c << sbend(+1), c << sbend(-1)
    s_out_top.connect("o1", m.ports["o3"])
    s_out_bot.connect("o1", m.ports["o4"])
    h_phi = c << cells.straight_heater_metal(length=HEATER_L)
    h_phi.connect("o2", s_in_top.ports["o1"])
    dummy = c << gf.components.straight(length=HEATER_L, cross_section="strip")
    dummy.connect("o2", s_in_bot.ports["o1"])
    h_a = c << cells.straight_heater_metal(length=HEATER_L)
    h_a.connect("o1", s_out_top.ports["o2"])
    h_b = c << cells.straight_heater_metal(length=HEATER_L)
    h_b.connect("o1", s_out_bot.ports["o2"])
    for name, port in (("o1", dummy.ports["o1"]), ("o2", h_phi.ports["o1"]),
                       ("o3", h_a.ports["o2"]), ("o4", h_b.ports["o2"])):
        c.add_port(name, port=port)
    arms = {"input_top (phi)": [s_in_top, h_phi], "input_bottom": [s_in_bot, dummy],
            "output_top (a)": [s_out_top, h_a], "output_bottom (b)": [s_out_bot, h_b]}
    contacts = {"phi": [h_phi.ports["l_e2"], h_phi.ports["r_e2"]],
                "theta": [m.ports["e3"], m.ports["e4"]],
                "a": [h_a.ports["l_e2"], h_a.ports["r_e2"]],
                "b": [h_b.ports["l_e4"], h_b.ports["r_e4"]]}
    return c, arms, contacts


def lead_start(port):
    """A port at the outer edge of the contact's M2 extension (the lead's start)."""
    start = port.copy()
    angle = math.radians(port.orientation)
    x, y = port.dcenter
    start.dcenter = (x + M2_EXTENSION * round(math.cos(angle)),
                     y + M2_EXTENSION * round(math.sin(angle)))
    return start


def with_pads():
    inner, arms, contacts = core()
    c = gf.Component(f"{NAME}_pads")
    c << inner
    pad = gf.get_component("pad")
    y_top = inner.dymax + PAD_GAP + pad.dysize / 2
    y_bot = inner.dymin - PAD_GAP - pad.dysize / 2
    order = [("phi", 0), ("phi", 1), ("theta", 0), ("theta", 1), ("a", 0), ("a", 1),
             ("b", 0), ("b", 1)]
    pads = {}
    for i, (heater, k) in enumerate(order, start=1):
        port = contacts[heater][k]
        below = heater == "b"
        p = c << pad
        p.dmove((port.dcenter[0], y_bot if below else y_top))
        start = lead_start(port)
        gf.routing.route_quad(c, start, p.ports["e2" if below else "e4"],
                              width1=port.dwidth + 2 * M2_EXTENSION, layer="MTOP")
        c.add_port(f"pad{i}", port=p.ports["e4" if below else "e2"])
        pads[f"pad{i}"] = f"{heater} terminal {k + 1}"
    for port in inner.ports:
        c.add_port(port.name, port=port)
    add_label_electrical(c, text=f"elec_{v002.LAB_USERNAME}-{NAME}_G", port_name="pad1")
    return c, arms, pads


def chip():
    """Pads + fiber array from the PDK, then the two DRC additions."""
    padded, arms, pads = with_pads()
    inner = cells.add_fiber_array(component=padded, component_name=NAME)
    c = gf.Component(NAME)
    ref = c << inner
    c.add_ports(ref.ports)
    m1 = kdb.Region(inner.begin_shapes_rec(inner.kcl.layer(*M1)))
    m2 = kdb.Region(inner.begin_shapes_rec(inner.kcl.layer(*M2)))
    ext = round(M2_EXTENSION / inner.kcl.dbu)
    for contact in (m1 & m2).merged().each():
        c.shapes(c.kcl.layer(*M2)).insert(contact.bbox().enlarged(ext, ext))
    c.shapes(c.kcl.layer(*FLOORPLAN)).insert(
        c.dbbox().enlarged(FLOORPLAN_MARGIN, FLOORPLAN_MARGIN))
    return c, arms, pads


def arm_length(parts):
    total = 0.0
    for inst in parts:
        info = inst.cell.info
        total += float(info.get("length", info.get("route_info_length", 0.0)))
    return total


def region(path, layer):
    layout = kdb.Layout()
    layout.read(str(path))
    top = layout.top_cells()[0]
    li = layout.find_layer(*layer)
    if li is None:
        return kdb.Region(), layout.dbu
    return kdb.Region(top.begin_shapes_rec(li)).merged(), layout.dbu


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c, arms, pads = chip()
    gds = OUT / "mzi_2x2_siepic_full.gds"
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
    pad_open, dbu = region(gds, PAD_OPEN)
    check("eight_pads", pad_open.count() == 8 and len(pads) == 8,
          f"{pad_open.count()} pad openings; pads: {pads}")

    counts = v002.count_cells(c)
    n_bdc = v002.matching(counts, "ebeam_bdc_te1550")
    n_gc = v002.matching(counts, "ebeam_gc_te1550")
    n_heater = v002.matching(counts, "straight_heater_metal")
    check("pdk_cells", n_bdc == 2 and n_gc == 4 and n_heater == 4,
          f"{n_bdc} ebeam_bdc_te1550, {n_gc} ebeam_gc_te1550, {n_heater} heaters "
          f"(expected 2, 4, 4)")

    internal = v002.arm_lengths(mzi())
    lengths = [a["length_um"] for a in internal.values()]
    check("balanced_mzi_arms", len(lengths) == 2 and abs(lengths[0] - lengths[1]) < TOL,
          f"MZI arm lengths {[round(x, 3) for x in lengths]} um")
    outer = {k: round(arm_length(v), 3) for k, v in arms.items()}
    vals = list(outer.values())
    check("balanced_input_output_arms",
          abs(vals[0] - vals[1]) < TOL and abs(vals[2] - vals[3]) < TOL and min(vals) > 0,
          f"arm lengths {outer} um")

    texts, layers = v002.gds_texts(gds)
    check("lab_measurement_label",
          any(v002.LAB_USERNAME in t for t in texts) and not any("JoaquinMatres" in t for t in texts),
          f"labels: {[t for t in texts if v002.LAB_USERNAME in t]}")
    pdk_root = Path(ubcpdk.__file__).parent
    pdk_layers = {(layer.layer, layer.datatype) for layer in PDK.layers}
    pdk_layers |= {tuple(v["layer"]) for v in
                   yaml.safe_load((pdk_root / "layers.yaml").read_text()).values()
                   if isinstance(v, dict) and "layer" in v}
    fixed = set()
    for name in ("ebeam_gc_te1550.gds", "ebeam_bdc_te1550.gds"):
        fixed |= v002.gds_texts(pdk_root / "gds" / "EBeam" / name)[1]
    unknown = sorted(layers - pdk_layers - fixed)
    check("only_pdk_layers", not unknown,
          f"layers used {sorted(layers)}; unexplained: {unknown}")

    m1, _ = region(gds, M1)
    m2, _ = region(gds, M2)
    si, _ = region(gds, SI)
    nets = list(m2.each())
    touches = [(kdb.Region(n) & m1).count() for n in nets]
    heaters = list(m1.each())
    reached = [sum(1 for n in nets if not (kdb.Region(n) & kdb.Region(h)).is_empty())
               for h in heaters]
    pads_per_net = [(kdb.Region(n) & pad_open).count() for n in nets]
    check("heater_isolation",
          len(nets) == 8 and all(t == 1 for t in touches) and len(heaters) == 4
          and all(r == 2 for r in reached) and all(p == 1 for p in pads_per_net),
          f"{len(nets)} M2 nets, M1 pieces per net {touches}, pads per net {pads_per_net}; "
          f"{len(heaters)} heaters, nets per heater {reached}")

    gap = round(MIN_HEATER_GAP / dbu)
    close = m1.space_check(gap).count()
    si_under_pads = (si & pad_open).count()
    check("layout_hygiene", close == 0 and si_under_pads == 0,
          f"{close} heater pairs closer than {MIN_HEATER_GAP} um; "
          f"{si_under_pads} silicon shapes under pad openings")

    png = OUT / "mzi_2x2_siepic_full.png"
    fig = c.plot()
    import matplotlib.pyplot as plt
    (fig if fig is not None and hasattr(fig, "savefig") else plt.gcf()).savefig(
        png, dpi=150, bbox_inches="tight")
    footprint = [round(c.dxsize, 3), round(c.dysize, 3)]

    regenerated = OUT / "mzi_2x2_siepic_full.check.gds"
    subprocess.run([sys.executable, __file__, "--write-gds", str(regenerated)], check=True,
                   capture_output=True)
    same = hashlib.sha256(regenerated.read_bytes()).hexdigest() == sha
    regenerated.unlink()
    check("gds_reproducible", same, "a fresh Python process regenerates a byte-identical GDS file")

    import siepic_drc
    drc = siepic_drc.run(gds)
    check("siepic_ebeam_drc_clean",
          drc["total_violations"] == 0 and drc["klayout"] == siepic_drc.EXPECTED_KLAYOUT,
          f"{drc['total_violations']} violations of {len(drc['rules'])} rules "
          f"({drc['klayout']}, {drc['pdk_wheel']}): "
          f"{ {k: v['count'] for k, v in drc['violations'].items()} }")

    report = {
        "experiment": "OPA-LAYOUT-003",
        "goal": "Fully programmable 2x2 MZI (theta, phi, a, b) with broadband couplers, "
                "grating couplers and eight bond pads in the open SiEPIC EBeam PDK",
        "pdk": f"ubcpdk {ubcpdk.__version__} (SiEPIC EBeam, MIT licence)",
        "gdsfactory_version": gf.__version__,
        "python_version": sys.version.split()[0],
        "gds_file": gds.name,
        "gds_sha256": sha,
        "footprint_um": footprint,
        "phase_shifters": {"phi": "heater on the top input arm", "theta": "PDK heater on the "
                           "top MZI arm", "a": "heater on the top output arm",
                           "b": "heater on the bottom output arm"},
        "heater_length_um": HEATER_L,
        "pads": pads,
        "mzi_arms": internal,
        "outer_arms_um": outer,
        "cell_counts": {"ebeam_bdc_te1550": n_bdc, "ebeam_gc_te1550": n_gc,
                        "straight_heater_metal": n_heater},
        "layers": sorted(layers),
        "drc": drc,
        "checks": checks,
        "failures": failures,
        "limitations": [
            "Thermal crosstalk between heaters is not modelled (50 um centre spacing)",
            "The fiber-array routes to the four grating couplers have different lengths; the "
            "resulting fixed phase between the inputs is absorbed by phi on calibration",
            "DRC covers geometry only; SiEPIC's functional verification has not been run",
            "The broadband coupler's split has not been verified; ubcpdk has no compact "
            "model for it",
            "The grating-coupler model in ubcpdk is a generic placeholder (6 dB, 35 nm), "
            "not measured data",
            "Not submitted to or checked by the foundry",
        ],
    }
    (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sheet = {
        "id": "OPA-LAYOUT-003",
        "title": "Fully programmable 2x2 MZI with fiber array and eight pads (SiEPIC EBeam)",
        "function": "programmable 2x2 MZI (theta, phi, a, b: any 2x2 unitary)",
        "status": "drc-clean" if not failures else "exploratory",
        "pdk": {"name": "SiEPIC EBeam (ubcpdk)", "version": ubcpdk.__version__,
                "open_source": True, "platform": "Si 220 nm SOI, electron-beam lithography"},
        "wavelength_um": {"design": 1.55},
        "footprint_um": footprint,
        "optical_ports": {"inputs": 2, "outputs": 2, "type": "TE grating coupler",
                          "pitch_um": FIBER_PITCH},
        "controls": {"heaters": 4, "bond pads": 8},
        "files": {"gds": gds.name, "preview": png.name},
        "generator": {"script": "layout/mzi_2x2_ubc_v003.py",
                      "environment": "layout/requirements-lock-ubc.txt"},
        "checks": {"passed": len(checks) - len(failures), "total": len(checks)},
        "key_results": [
            {"name": "Phase shifters", "value": "theta, phi, a, b (four 200 um TiN heaters, "
             "50 um apart)", "source": "OPA-LAYOUT-003"},
            {"name": "Electrical", "value": "8 independent pads, each wired to one heater "
             "terminal; no shorts", "source": "OPA-LAYOUT-003 heater_isolation"},
            {"name": "Fiber I/O", "value": f"4 TE grating couplers at {FIBER_PITCH:g} um pitch",
             "source": "OPA-LAYOUT-003"},
            {"name": "SiEPIC EBeam DRC", "value": f"{drc['total_violations']} violations of "
             f"{len(drc['rules'])} rules ({drc['klayout']})", "source": "tools/siepic_drc.py"},
        ],
        "limitations": ["thermal crosstalk not modelled", "SiEPIC functional verification not "
                        "run", "broadband coupler not verified", "not submitted"],
        "tags": ["mzi", "2x2", "programmable", "phase-shifter", "broadband-coupler",
                 "grating-coupler", "bond-pads", "siepic", "ebeam", "silicon", "open-pdk"],
    }
    (OUT / "design.json").write_text(json.dumps(sheet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "drc"}, indent=2))
    if failures:
        raise SystemExit("OPA-LAYOUT-003 failed checks: " + ", ".join(failures))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--write-gds":
        chip()[0].write_gds(sys.argv[2], with_metadata=False)
    else:
        main()
