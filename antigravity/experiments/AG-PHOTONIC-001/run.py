"""Independent autonomous directional coupler pilot."""
import importlib.util
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location(
    "infra_probe", Path(__file__).resolve().parents[1] / "AG-INFRA-001/probe.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

PROMPT = """Independently investigate a silicon directional coupler at 1550 nm.
Use two identical 450 nm wide, 220 nm thick silicon strip waveguides in
silica (constant refractive indices 3.48 and 1.44), TE-like fundamental mode.
Target 50/50 guided power splitting at the end of the straight coupling region.
Choose and justify gaps between 150 and 350 nm and coupling lengths.
You may inspect installed tools and attempt a bounded installation of Meep
or MPB using public package repositories, without credentials or paid services.
Do not access our repository or existing benchmark results. Do not access
secrets, launch background jobs, or use external compute services.
Develop your own executable model, run a small numerical experiment,
and adapt your approach based on observed results. Prefer a vector eigenmode
solver or FDTD. If unavailable, use a clearly labeled approximate model,
not a fabricated full-wave result. Distinguish coupling length for complete
transfer from length for 50/50 splitting. State boundary conditions, mesh,
units, material assumptions, convergence limitations and power normalization.
Return concise JSON with method, commands and exit codes, actual numerical
data, complete reproducible source code as text, dependencies, and limitations.
If unable to execute, report failure explicitly. Never invent measurements.
Do not claim fabrication or experimental validation. Keep the task small;
stop if installation or computation is infeasible."""
PAYLOAD = dict(probe.PAYLOAD, input=PROMPT)

if __name__ == "__main__":
    sys.exit(probe.main(payload=PAYLOAD, result_prefix="AG-PHOTONIC-001"))
