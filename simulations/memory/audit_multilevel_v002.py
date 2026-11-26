"""Read-only W-002A archive audit; no rerun of the source experiment."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
from collections import defaultdict

RUN = 45900743025
ARTIFACT = 15156101360
SOURCE = "3c88d19e6f658a2d7f72b459e2a429c0d8473c5d"
DIGEST = "24864a7e0a125c59f55937e07796db6c1231c97c5cd08f61f59e751970cbe896"
SEEDS = (1027,2039,3049,4057,5069,6073,7087,8093)
SIGMAS = (0.,.002,.005,.01,.02)
DRIFTS = (0.,.005,.02)
ADCS = (6,8,12)
FIELDS = ("bits","seed","program_sigma","read_sigma","drift_sigma","adc_bits")
FILES = {"result.json","panels.csv","confusion.csv","calibration.json",
         "environment-lock.txt","installed-packages.json"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify(root):
    p=json.loads((root/"archive-provenance.json").read_text())
    require((p["workflow_run_id"],p["artifact_id"],p["source_head_sha"],p["artifact_sha256"])
            ==(RUN,ARTIFACT,SOURCE,DIGEST),"archive identity")
    require(set(p["files"])==FILES,"archive file set")
    for name,f in p["files"].items():
        b=(root/name).read_bytes()
        require(len(b)==f["bytes"],name+" length")
        require(hashlib.sha256(b).hexdigest()==f["sha256"],name+" SHA256")
        require(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
                ==f["git_blob_sha1"],name+" git blob")
    return p


def key(r):
    return (int(r["bits"]),int(r["seed"]),float(r["program_sigma"]),
            float(r["read_sigma"]),float(r["drift_sigma"]),int(r["adc_bits"]))


def close(a,b):
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-12)


def analyze(root,out):
    verify(root)
    report=json.loads((root/"result.json").read_text())
    require(report["passed"] is True and report["physical_measurement"] is False
            and report["material_fit"] is False,"source scope")
    expected=set(itertools.product((1,4),SEEDS,SIGMAS,SIGMAS,DRIFTS,ADCS))
    panels={}
    with (root/"panels.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            k=key(r)
            require(k in expected and k not in panels,"panel identity")
            require(r["calibration_valid"]=="True","unexpected invalid calibration")
            panels[k]=r
    require(set(panels)==expected,"panel coverage")
    # Read every confusion row, not just source summary.
    matrices=defaultdict(dict)
    with (root/"confusion.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            k=key(r); i,j,n=int(r["true"]),int(r["predicted"]),int(r["count"])
            require(k in panels and 0<=i<2**k[0] and 0<=j<2**k[0] and n>=0,"confusion row")
            require((i,j) not in matrices[k],"duplicate confusion row")
            matrices[k][i,j]=n
    require(set(matrices)==expected,"confusion panel coverage")
    require(sum(map(len,matrices.values()))==report["confusion_rows"]==468000,"confusion coverage")
    groups=defaultdict(list)
    for k,r in panels.items():
        bits,seed,ps,rs,ds,adc=k; levels=2**bits; m=matrices[k]
        require(len(m)==levels**2,"matrix size")
        require(all(sum(m[i,j] for j in range(levels))==4096 for i in range(levels)),"state count")
        total=4096*levels
        se=sum(n for (i,j),n in m.items() if i!=j)
        be=sum((i^j).bit_count()*n for (i,j),n in m.items())
        worst=max(1-m[i,i]/4096 for i in range(levels))
        passed=worst<=.001
        require(int(r["samples"])==total and int(r["symbol_errors"])==se
                and int(r["bit_errors"])==be and close(r["ser"],se/total)
                and close(r["ber"],be/(total*bits)) and close(r["worst_state_ser"],worst)
                and r["point_screen"]==str(passed),"metric mismatch")
        groups[bits,ps,rs,ds,adc].append((passed,worst,se/total,be/(total*bits)))
    rows=[]
    for k,values in sorted(groups.items()):
        require(len(values)==8,"seed coverage")
        rows.append(dict(zip(("bits","program_sigma","read_sigma","drift_sigma","adc_bits"),k),
                         seeds=8,passing_seeds=sum(x[0] for x in values),
                         worst_seed_state_ser=max(x[1] for x in values),
                         mean_seed_ser=sum(x[2] for x in values)/8,
                         mean_seed_ber=sum(x[3] for x in values)/8))
    summary={}
    for bits in (1,4):
        subset=[r for r in rows if r["bits"]==bits]
        passing=sum(r["passing_seeds"] for r in subset)
        require(passing==report["summary"][str(bits)]["point_screen_pass"],"summary mismatch")
        summary[str(bits)]=dict(panels=1800,passing_panels=passing,
            combinations=len(subset),all_eight_pass=sum(r["passing_seeds"]==8 for r in subset),
            zero_pass=sum(r["passing_seeds"]==0 for r in subset),
            by_adc={str(a):sum(r["passing_seeds"] for r in subset if r["adc_bits"]==a) for a in ADCS},
            by_drift={str(d):sum(r["passing_seeds"] for r in subset if r["drift_sigma"]==d) for d in DRIFTS})
    with (out/"combinations.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return dict(passed=True,experiment="OPA-W-002B",source_run=RUN,artifact_id=ARTIFACT,
                verified_files=len(FILES),panel_count=len(panels),confusion_rows=468000,
                summary=summary,physical_measurement=False,material_fit=False,
                interpretation="All-eight pass is descriptive over fixed seeds, not qualification or a reliability probability.")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    try:
        result=analyze(a.archive,a.output)
    except Exception as e:
        result=dict(passed=False,error=str(e))
    (a.output/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    return 0 if result["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
