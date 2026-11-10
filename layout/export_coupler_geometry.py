"""Export the OPA-LAYOUT-001 directional coupler geometry for Meep (OPA-COUPLER-002).

Writes the waveguide polygons of gdsfactory's coupler (generic PDK, gap
0.236 um) for several straight lengths to
simulations/meep/geometry/coupler_gap0.236.json, so the 3D FDTD simulates
exactly the shape that is in the GDS. The layout workflow regenerates this file
and fails if the committed copy differs.
"""
import json
from pathlib import Path

import gdsfactory as gf

GAP = 0.236
LENGTHS = (0.0, 8.0, 16.0)
OUT = Path("simulations/meep/geometry/coupler_gap0.236.json")

gf.gpdk.PDK.activate()
data = {"source": "gdsfactory.components.coupler (generic PDK)",
        "gdsfactory_version": gf.__version__, "gap_um": GAP, "units": "um",
        "waveguide_layer": "WG (1, 0)", "lengths": {}}
for length in LENGTHS:
    c = gf.components.coupler(gap=GAP, length=length).copy()
    polygons = c.get_polygons_points(merge=True)
    wg = polygons[gf.get_layer((1, 0))]
    data["lengths"][f"{length:g}"] = {
        "polygons": [[[round(float(x), 6), round(float(y), 6)] for x, y in p] for p in wg],
        "ports": {p.name: [round(float(v), 6) for v in p.dcenter] for p in c.ports},
    }
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
print(f"wrote {OUT} with lengths {list(data['lengths'])}")
