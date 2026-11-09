"""OPA-FDTD-001: small free-space Meep smoke simulation (not a chip model)."""
import json
import math
from pathlib import Path

import meep as mp

OUT = Path("results/meep-smoke-v001")
OUT.mkdir(parents=True, exist_ok=True)

simulation = mp.Simulation(
    cell_size=mp.Vector3(8, 4, 0),
    resolution=15,
    boundary_layers=[mp.PML(1.0)],
    sources=[
        mp.Source(
            mp.GaussianSource(frequency=1.0, fwidth=0.2),
            component=mp.Ez,
            center=mp.Vector3(-2.0, 0),
        )
    ],
    dimensions=2,
)
monitor = simulation.add_flux(
    1.0,
    0,
    1,
    mp.FluxRegion(center=mp.Vector3(1.5, 0), size=mp.Vector3(0, 2)),
)
simulation.run(until=80)
flux = float(mp.get_fluxes(monitor)[0])
result = {
    "test_id": "OPA-FDTD-001",
    "purpose": "Meep free-space solver and flux-monitor smoke test",
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "resolution_pixels_per_meep_unit": 15,
    "flux": flux,
    "scope": "No LNOI, MMI, GDSII, reflection or loss validation performed",
}
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
if not math.isfinite(flux) or flux <= 0:
    raise SystemExit(f"Smoke test failed: expected finite positive transmitted flux, got {flux}")
