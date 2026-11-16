"""Independent execution and validation of the archived Antigravity MPB model."""
import json
import math
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def run_case(gap, res, sx, sy):
    cmd = ["mpb", f"gap={gap/1000}", f"res={res}", f"sx={sx}", f"sy={sy}", str(HERE/"original/coupler.ctl")]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode:
        raise RuntimeError(p.stderr[-2000:])
    bands = {}
    for line in p.stdout.splitlines():
        if line.startswith("RESULT:,"):
            values = {k.strip():float(v) for k,v in (part.strip().split("=") for part in line.split(",")[1:])}
            band = int(values["band"])
            if band in bands or not all(math.isfinite(v) for v in values.values()):
                raise ValueError("Invalid band output")
            bands[band] = values
    if set(bands) != {1,2}:
        raise ValueError("Missing modes")
    even, odd = sorted(bands.values(), key=lambda b:b["|Ex(0)|"], reverse=True)
    for b in (even,odd):
        if not 1.44 < b["neff"] < 3.48 or not b["|Ex(x0)|"] > b["|Ey(x0)|"]:
            raise ValueError("Expected guided TE-like mode")
    if not even["|Ex(0)|"] > 10*odd["|Ex(0)|"]:
        raise ValueError("Midpoint parity diagnostic failed")
    delta = even["neff"]-odd["neff"]
    if delta <= 0:
        raise ValueError("Nonpositive splitting")
    return dict(command=cmd, gap_nm=gap, resolution=res, supercell_um=[sx,sy],
                neff_even=even["neff"], neff_odd=odd["neff"], delta_neff=delta,
                Lc_um=1.55/(2*delta), L50_um=1.55/(4*delta), bands=bands)

def main():
    ref = json.loads((HERE/"reference.json").read_text())
    results = []
    for kind, cases in ref.items():
        for case in cases:
            if kind == "sweep":
                gap,e,o,l = case
                res,sx,sy = 96,5,3
            else:
                res,sx,sy,e,o,l = case
                gap = 200
            r = run_case(gap,res,sx,sy)
            r["reference"] = dict(neff_even=e,neff_odd=o,L50_um=l)
            r["passed"] = abs(r["neff_even"]-e)<=0.0002 and abs(r["neff_odd"]-o)<=0.0002 and abs(r["L50_um"]/l-1)<=0.01
            r["kind"] = kind
            results.append(r)
            print(json.dumps(r),flush=True)
    sweep = [r for r in results if r["kind"]=="sweep"]
    monotonic = all(a["L50_um"]<b["L50_um"] for a,b in zip(sweep,sweep[1:]))
    version = subprocess.run(["mpb","--version"],capture_output=True,text=True,check=True)
    report = dict(mpb_version=version.stdout+version.stderr, results=results, monotonic=monotonic,
                  passed=monotonic and all(r["passed"] for r in results))
    Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+"\n")
    return 0 if report["passed"] else 1

if __name__=="__main__":
    sys.exit(main())
