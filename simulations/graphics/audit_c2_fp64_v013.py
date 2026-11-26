"""C3A stage 3: compiled FP64 and archived guard/operation audit.

No optical model rerun. Frozen C2 inputs and decisions are read only.
"""
import argparse
import csv
import ctypes as C
import hashlib
import itertools
import json
import math
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from audit_c2_geometry_v012 import vec, triangle, box, topology, require

SCENARIOS=("scale_only","large_scale","noise_only","combined","drift_quantization")
POLICIES=("electronic_only","all_optical_fallback","raw","max_min_125")
FLAGS=["-O3","-std=c11","-fPIC","-shared","-fno-fast-math","-ffp-contract=off"]
TOL=1e-10


def guard_sides(o,d,lo,hi):
    """Use exact forward intervals, not reflected floating-point operands."""
    active=0
    for p,q,a,b in zip(o,d,lo,hi):
        if q==0:
            if not a<=p<=b:
                return -1,0
        else:
            active+=1
            if (max((a-p)/q,(b-p)/q))<0:
                return -1,0
    return (1,0) if active<2 else (0,active*(active-1))


def decisions(policy,guard,cpu,minimum,threshold):
    if policy=="electronic_only":
        require(minimum is None,"electronic minimum")
        return cpu,0,cpu
    if guard:
        require(minimum is None,"guard minimum")
        raw=int(guard>0)
        return raw,0,raw
    require(minimum is not None and math.isfinite(minimum),"invalid optical minimum")
    raw=int(minimum>=0)
    fallback=int(policy=="all_optical_fallback" or
                 (policy=="max_min_125" and abs(minimum)<=threshold))
    return raw,fallback,cpu if fallback else raw


def kernels(directory):
    base=Path(__file__).parent
    so=Path(directory)/"kernels.so"
    subprocess.run(["cc",*FLAGS,str(base/"ray_box_cpu_v006.c"),
                    str(base/"ray_triangle_cpu_v009.c"),"-o",str(so)],check=True)
    lib=C.CDLL(str(so))
    ptr=C.POINTER(C.c_double)
    lib.triangle.argtypes=[ptr,ptr,ptr,ptr]
    lib.triangle.restype=C.c_int
    lib.raybox.argtypes=[ptr,C.POINTER(C.c_uint8),C.c_size_t]
    lib.raybox.restype=None
    def arr(xs):
        return (C.c_double*len(xs))(*map(float,xs))
    def tri(o,d,v):
        t=C.c_double()
        status=lib.triangle(arr(o),arr(d),arr([x for p in v for x in p]),C.byref(t))
        return status,t.value if status==1 else None
    def bx(o,d,lo,hi):
        out=C.c_uint8()
        lib.raybox(arr((*o,*d,*lo,*hi)),C.byref(out),1)
        return int(out.value)
    return tri,bx


def near(a,b):
    return math.isfinite(a) and abs(a-b)<=TOL+TOL*abs(b)


def nearest(hits,ids):
    return min(((j,hits[j][1]) for j in ids if hits[j][0]==1),
               key=lambda p:(p[1],p[0]),default=(-1,None))


def walk(nodes,boxes):
    stack=[0]
    visited=[]
    tested=[]
    while stack:
        j=stack.pop()
        visited.append(j)
        if boxes[j]:
            stack.extend(reversed(nodes[j]["children"]))
            tested.extend(nodes[j]["primitives"])
    return visited,tested


def audit(root,ctri,cbox,diffs):
    manifest=json.loads((root/"archive-provenance.json").read_text())
    names={"audit.csv","calibration.json","environment-lock.txt","installed-packages.json",
           "labels.json","node-results.csv","result.json","results.csv","workload.json"}
    require(set(manifest["files"])==names,"archive file set")
    for name in sorted(names):
        b=(root/name).read_bytes()
        m=manifest["files"][name]
        require(len(b)==m["bytes"] and hashlib.sha256(b).hexdigest()==m["sha256"]
                and hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==m["git_blob_sha1"],
                "archive digest "+name)
    original=json.loads((root/"result.json").read_text())
    for name in ("workload","labels"):
        require(original[name+"_sha256"]==manifest["files"][name+".json"]["sha256"],"frozen digest")
    labels=json.loads((root/"labels.json").read_text())
    labelmap={(l["scene"],l["ray"]):l for l in labels}
    require(len(labelmap)==len(labels),"duplicate label")
    cal=json.loads((root/"calibration.json").read_text())
    thresholds={(x["scenario"],x["repeat"]):x["threshold"] for x in cal}
    require(len(cal)==len(thresholds)==50 and set(thresholds)==set(itertools.product(SCENARIOS,range(10)))
            and all(math.isfinite(x) and x>=0 for x in thresholds.values()),"threshold coverage")
    counts=Counter()
    panels=defaultdict(Counter)
    cache={}
    seen=set()
    def compare(kind,k,index,expected,observed):
        if expected!=observed:
            diffs.append(dict(kind=kind,scene=k[0],ray=k[1],index=str(index),
                              expected=str(expected),observed=str(observed)))
    for s in json.loads((root/"workload.json").read_text())["scenes"]:
        tris,bounds=topology(s)
        for ri,(o,d) in enumerate(s["rays"]):
            k=(s["name"],ri)
            require(k in labelmap and k not in seen,"ray identity")
            seen.add(k)
            o,d=vec(o),vec(d)
            exact=[triangle(o,d,v) for v in tris]
            cop=[j for j,(status,t) in enumerate(exact) if status==-1]
            compare("excluded",k,"",bool(cop),labelmap[k]["excluded"])
            if cop:
                counts["excluded"]+=1
                continue
            cpu=[ctri(o,d,v) for v in tris]
            for j,((status,t),(cs,ct)) in enumerate(zip(exact,cpu)):
                compare("triangle_status",k,j,status,cs)
                if status==cs==1:
                    compare("triangle_distance",k,j,True,near(ct,float(t)))
                counts["triangle_pairs"]+=1
            eb=[int(box(o,d,*b)) for b in bounds]
            cb=[cbox(o,d,*b) for b in bounds]
            gs=[guard_sides(o,d,*b) for b in bounds]
            for j,(e,c,(g,ns)) in enumerate(zip(eb,cb,gs)):
                compare("box_status",k,j,e,c)
                if g:
                    compare("guard_geometry",k,j,e,int(g>0))
                counts["box_pairs"]+=1
            cv,ct=walk(s["nodes"],cb)
            cache[k]=(cpu,cb,gs,cv,ct,s["nodes"])
    require(seen==set(labelmap) and len(cache)==249 and counts["excluded"]==1,"ray coverage")
    expected=set(itertools.product(SCENARIOS,range(10),cache,POLICIES))
    def key(r):
        return r["scenario"],int(r["repeat"]),(r["scene"],int(r["ray"])),r["policy"]
    seenrows=set()
    with (root/"node-results.csv").open(newline="") as nf,(root/"results.csv").open(newline="") as rf:
        groups=iter(itertools.groupby(csv.DictReader(nf),key=key))
        for row in csv.DictReader(rf):
            rk=key(row)
            require(rk in expected and rk not in seenrows,"ray row identity")
            seenrows.add(rk)
            scenario,rep,k,policy=rk
            cpu,cb,gs,cv,ct,nodes=cache[k]
            group=next(groups,None)
            require(group is not None and group[0]==rk,"node group identity")
            c=Counter()
            stack=[0]
            vis,accepted,tests=[],[],[]
            for n in group[1]:
                j=int(n["node"])
                require(stack and j==stack.pop() and 0<=j<len(cb),"traversal order")
                vis.append(j)
                g,ns=gs[j]
                compare("guard",k,(rk,j),g,int(n["guard"]))
                compare("cpu_box",k,(rk,j),cb[j],int(n["cpu"]))
                m=float(n["minimum"]) if n["minimum"] else None
                raw,fb,decision=decisions(policy,g,cb[j],m,thresholds[scenario,rep])
                for field,value in (("raw",raw),("fallback",fb),("decision",decision)):
                    compare(field,k,(rk,j),value,int(n[field]))
                if policy!="electronic_only":
                    c["guards"]+=int(g!=0)
                    c["optical"]+=int(g==0)
                    c["sides"]+=ns
                    c["fallback"]+=fb
                if int(n["decision"]):
                    accepted.append(j)
                    stack.extend(reversed(nodes[j]["children"]))
                    tests.extend(nodes[j]["primitives"])
                    c["leaves"]+=int(not nodes[j]["children"])
                counts["node_rows"]+=1
            require(not stack,"incomplete traversal")
            for name,ids in (("visited",vis),("accepted",accepted),("tested",tests)):
                compare(name+"_ids",k,rk,ids,json.loads(row[name+"_ids"]))
            c.update(nodes=len(vis),accepted=len(accepted),triangles=len(tests),
                     driven_operands=4*c["sides"],
                     extra_nodes=len(set(vis)-set(cv)),missing_nodes=len(set(cv)-set(vis)),
                     extra_triangles=len(set(tests)-set(ct)),missing_triangles=len(set(ct)-set(tests)))
            pid,t=nearest(cpu,tests)
            compare("pred_id",k,rk,pid,int(row["pred_id"]))
            observed=float(row["pred_t"]) if row["pred_t"] else None
            if t is None or observed is None:
                compare("pred_t_presence",k,rk,t is None,observed is None)
            else:
                compare("pred_t",k,rk,True,near(observed,t))
            label=labelmap[k]
            tid=label["exact_id"]
            from fractions import Fraction
            truth=float(Fraction(label["exact_t"])) if label["exact_t"] is not None else None
            c["final_fp"]=int(tid<0<=pid)
            c["final_fn"]=int(pid<0<=tid)
            c["wrong_id"]=int(tid>=0 and pid>=0 and tid!=pid)
            c["distance_fail"]=int(tid>=0 and pid>=0 and not near(t,truth))
            c["nearest_not_tested"]=int(tid>=0 and tid not in tests)
            dist=abs(t-truth) if t is not None and truth is not None else None
            recorded=float(row["distance_error"]) if row["distance_error"] else None
            if dist is None or recorded is None:
                compare("distance_error_presence",k,rk,dist is None,recorded is None)
            else:
                compare("distance_error",k,rk,True,near(recorded,dist))
            for field in ("nodes","accepted","triangles","leaves","guards","optical","sides",
                          "fallback","driven_operands","extra_nodes","missing_nodes",
                          "extra_triangles","missing_triangles","final_fp","final_fn","wrong_id",
                          "distance_fail","nearest_not_tested"):
                compare(field,k,rk,c[field],int(row[field]))
            c["rays"]=1
            panels[scenario,rep,k[0],policy].update(c)
            counts["ray_rows"]+=1
        require(next(groups,None) is None,"extra node groups")
    require(seenrows==expected and counts["ray_rows"]==49800 and counts["node_rows"]==664870,"CSV coverage")
    return dict(counts),panels


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    diffs=[]
    panels={}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            counts,panels=audit(a.archive,*kernels(tmp),diffs)
        report=dict(passed=True,scientific_gate=not diffs,counts=counts,discrepancies=len(diffs))
    except Exception as exc:
        report=dict(passed=False,scientific_gate=False,error=str(exc),discrepancies=len(diffs))
    report.update(stage="C3A compiled FP64 and archived guard/operation audit",
                  compiler=subprocess.check_output(["cc","--version"],text=True).splitlines()[0],
                  flags=FLAGS,compiled_benchmark="not_run",energy="not_measured",
                  limitations=["Recompiled FP64 kernels, not historical binary identity",
                               "Archived minima and thresholds replayed, not regenerated optical signals",
                               "No timing or physical performance claims"])
    with (a.output/"discrepancies.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["kind","scene","ray","index","expected","observed"])
        w.writeheader();w.writerows(diffs)
    fields=["rays","nodes","accepted","leaves","triangles","guards","optical","fallback","sides",
            "driven_operands","extra_nodes","missing_nodes","extra_triangles","missing_triangles",
            "final_fp","final_fn","wrong_id","distance_fail","nearest_not_tested"]
    with (a.output/"panels.csv").open("w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["scenario","repeat","scene","policy",*fields])
        for k,c in sorted(panels.items()):
            w.writerow([*k,*[c[x] for x in fields]])
    (a.output/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
