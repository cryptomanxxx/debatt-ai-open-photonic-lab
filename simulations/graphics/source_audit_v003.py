"""Source audit of Zhang et al. Supplementary Note 1, S1-S7."""
import csv
import json
from fractions import Fraction
from itertools import permutations, product
from pathlib import Path

import numpy as np

from ray_box_v001 import face_oracle, workloads
from side_test_v002 import side_test

OUT = Path(__file__).resolve().parents[2] / "results" / "opa-g-002-source"


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def cross(a, b):
    return tuple(a[(i+1)%3]*b[(i+2)%3]-a[(i+2)%3]*b[(i+1)%3]
                 for i in range(3))


def source_edges(case):
    """Independent oriented silhouette edges, after axis reflection.

    Edge i,j fixes exit coordinate i and entry coordinate j. Orient its
    remaining axis so S2/edge length equals the nonnegative overlap margin.
    The orientation is our explicit construction, not supplied author code.
    """
    o,d,lo,hi = [tuple(Fraction(float(x)) for x in v) for v in case]
    o,d,lo,hi = map(list,(o,d,lo,hi))
    for i in range(3):
        if d[i]<0:
            o[i],d[i],lo[i],hi[i]=-o[i],-d[i],-hi[i],-lo[i]
    active = [i for i in range(3) if d[i]!=0]
    if any(not lo[i]<=o[i]<=hi[i] for i in range(3) if not d[i]):
        return False, [], [], [], 0
    if any(hi[i]<o[i] for i in active):
        return False, [], [], [], 0
    s2, reduced, literal = [], [], []
    degenerate = 0
    for i,j in permutations(active,2):
        k = 3-i-j
        a,b = list(lo),list(lo)
        a[i]=b[i]=hi[i]
        a[j]=b[j]=lo[j]
        b[k]=hi[k]
        # S2 = -D dot ((A-O) cross (B-O)).
        # Orient edge so normalized S2 equals d_j*U_i-d_i*L_j.
        if (i,j,k) in ((0,1,2),(1,2,0),(2,0,1)):
            a,b=b,a
        length=abs(b[k]-a[k])
        ri,rj=a[i]-o[i],a[j]-o[j]
        reduced.append(d[j]*ri-d[i]*rj)
        # Literal plus-sign diagnostic after the same orientation normalization.
        # For x-parallel edges this is precisely the S7 sign discrepancy,
        # up to the orientation of the ordered pair; other axes are not
        # claimed to have this typo in the source.
        if k==0:
            literal.append(d[j]*ri+d[i]*rj if (i,j)==(2,1)
                           else -d[j]*ri-d[i]*rj)
        else:
            literal.append(reduced[-1])
        if length:
            s2.append(-dot(d,cross(tuple(x-y for x,y in zip(a,o)),
                                   tuple(x-y for x,y in zip(b,o))))/length)
        else:
            # Zero-length actual edge has no orientation. Use the limiting
            # reduced inequality, explicitly tracked as a fallback.
            degenerate+=1
            s2.append(reduced[-1])
    return all(x>=0 for x in s2),s2,reduced,literal,degenerate


def main():
    rng=np.random.default_rng(20261126)
    translated=[]
    for _ in range(4096):
        lo=rng.integers(-512,513,3)/256
        hi=lo+rng.integers(0,513,3)/256
        o=rng.integers(-1024,1025,3)/256
        d=rng.integers(-256,257,3)/256
        translated.append((o,d,lo,hi))
    lo,hi=(-1,-1,-1),(1,1,1)
    grid=[(o,d,lo,hi) for o in product(range(-2,3),repeat=3)
          for d in product((-1,0,1),repeat=3)]
    # Direct S2 versus printed S7 for A=(2,1,1), B=(1,1,1).
    a,b,o,d=(2,1,1),(1,1,1),(0,0,0),(0,0,1)
    raw=-dot(d,cross(a,b))
    corrected=d[1]*(1-o[2])-d[2]*(1-o[1])
    printed=d[1]*(1-o[2])+d[2]*(1-o[1])
    checks={"s7_counterexample":raw==corrected==-1 and printed==1}
    rows=[]
    for name,cases in [("translated",translated),("integer_grid",grid),*workloads()]:
        row=dict(workload=name,samples=len(cases),fp=0,fn=0,
                 margin_mismatches=0,literal_plus_fp=0,literal_plus_fn=0,
                 degenerate_edge_fallbacks=0,oriented_edges=0)
        for case in cases:
            truth=face_oracle(*case)
            pred,s2,red,lit,deg=source_edges(case)
            prior,prior_sides,reason=side_test(*case)
            row["fp"]+=int(pred and not truth)
            row["fn"]+=int(truth and not pred)
            row["margin_mismatches"]+=int(tuple(s2)!=tuple(red)
                                           or tuple(red)!=prior_sides or pred!=prior)
            literal_pred=all(x>=0 for x in lit) if reason=="side_test" else False
            row["literal_plus_fp"]+=int(literal_pred and not truth)
            row["literal_plus_fn"]+=int(truth and not literal_pred)
            row["degenerate_edge_fallbacks"]+=deg
            row["oriented_edges"]+=len(s2)-deg
        checks[name+"_equivalence"]=not any(row[k] for k in ("fp","fn","margin_mismatches"))
        rows.append(row)
    checks["oriented_edges_exercised"]=sum(r["oriented_edges"] for r in rows)>0
    checks["literal_plus_disagreement"]=sum(r["literal_plus_fp"]+r["literal_plus_fn"] for r in rows)>0
    result=dict(experiment="opa-g-002-source",checks=checks,passed=all(checks.values()),
                rows=rows,counterexample=dict(s2=raw,corrected=corrected,printed=printed),
                limitations=["Source S1/S2 audited; S5-S7 sign discrepancy not author-confirmed",
                             "Our explicit edge orientation and forward/parallel guards",
                             "Degenerate edges use limiting inequality, not zero-length S2",
                             "Literal-plus diagnostic only replaces x-parallel edge tests",
                             "No optical or measured hardware results"])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    with (OUT/"results.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise SystemExit("Source audit failed")


if __name__=="__main__":
    main()
