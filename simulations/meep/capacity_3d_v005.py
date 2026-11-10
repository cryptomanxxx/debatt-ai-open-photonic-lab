"""OPA-FDTD-005: bounded 3D Meep resource benchmark.

A short 3D dielectric waveguide test, not a whole-chip simulation or loss model.
One Meep unit is interpreted as one micrometre for geometry bookkeeping only.
"""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import time

import meep as mp

PROFILES = {
    "small": {"cell_um": (8.0, 8.0, 3.0), "resolution_per_um": 10, "duration_meep": 12},
    "medium": {"cell_um": (20.0, 20.0, 4.0), "resolution_per_um": 10, "duration_meep": 12},
}
MAX_GRID_CELLS = 2_000_000
MAX_THEORETICAL_BYTES = 96 * MAX_GRID_CELLS
OUTPUT = Path("results/opa-fdtd-005")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, default="small")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    config = PROFILES[args.profile]
    sx, sy, sz = config["cell_um"]
    resolution = config["resolution_per_um"]
    estimated_cells = math.prod(math.ceil(length * resolution) for length in (sx, sy, sz))
    estimated_min_bytes = 96 * estimated_cells
    if estimated_cells > MAX_GRID_CELLS or estimated_min_bytes > MAX_THEORETICAL_BYTES:
        raise ValueError("Refusing to run a profile beyond the fixed resource guard")
    source_x = -sx / 2 + 1.7
    detector_x = sx / 2 - 1.7
    start = time.perf_counter()
    sim = mp.Simulation(
        cell_size=mp.Vector3(sx, sy, sz),
        dimensions=3,
        resolution=resolution,
        boundary_layers=[mp.PML(1.0)],
        geometry=[mp.Block(
            size=mp.Vector3(mp.inf, 0.55, 0.25),
            material=mp.Medium(index=1.8),
        )],
        sources=[mp.Source(
            mp.GaussianSource(frequency=0.8, fwidth=0.25),
            component=mp.Ez,
            center=mp.Vector3(source_x, 0, 0),
            size=mp.Vector3(0, 0.55, 0.25),
        )],
    )
    detector = sim.add_flux(
        0.8, 0, 1,
        mp.FluxRegion(
            center=mp.Vector3(detector_x, 0, 0),
            size=mp.Vector3(0, 1.2, 1.2),
            direction=mp.X,
        ),
    )
    sim.run(until=config["duration_meep"])
    flux = float(mp.get_fluxes(detector)[0])
    elapsed = time.perf_counter() - start
    peak_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    sim.reset_meep()
    report = {
        "experiment": "OPA-FDTD-005",
        "profile": args.profile,
        "geometry": "3D illustrative index-guided waveguide, no bend",
        "interpretation_of_length_unit": "micrometre, illustrative only",
        "cell_um": config["cell_um"],
        "resolution_pixels_per_um": resolution,
        "estimated_grid_cells": estimated_cells,
        "theoretical_lower_bound_memory_bytes": estimated_min_bytes,
        "measured_peak_process_rss_bytes": peak_rss_kb * 1024,
        "measured_wall_seconds": elapsed,
        "measured_output_aperture_flux": flux,
        "meep_version": str(getattr(mp, "__version__", "unknown")),
        "runner_cpu_count": os.cpu_count(),
        "limitations": [
            "Peak RSS includes Python process but not all runner system processes",
            "Meep theoretical memory is a lower bound; observed memory is profile-specific",
            "Only a short run, not convergence, physical loss, or maximum capacity proof",
            "Longer runs and physical 3D component calculations may require much more compute",
        ],
    }
    output_path = OUTPUT / f"benchmark-{args.profile}.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not math.isfinite(flux) or elapsed <= 0 or peak_rss_kb <= 0:
        raise SystemExit("Invalid benchmark telemetry")


if __name__ == "__main__":
    main()
