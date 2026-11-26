"""C3A stage 2: independent exact geometry on immutable C2 inputs.

Cramer's rule for triangles; rational interval intersection for boxes.
No imports from C1/C2 geometry, no optical model rerun, no timing.
"""
import argparse
import csv
import hashlib
import itertools
import json
from collections import Counter
from fractions import Fraction as F
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def vec(v):
    require(len(v) == 3, "expected 3D vector")
    return tuple(F(float(x)) for x in v)


def sub(a, b):
    return tuple(x-y for x, y in zip(a,b))


def det(a,b,c):
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def triangle(o,d,v):
    a,b,c = v
    e,f = sub(b,a),sub(c,a)
    # Detect rank-deficient triangles before testing coplanarity.
    if all(e[i]*f[j] == e[j]*f[i] for i,j in ((0,1),(0,2),(1,2))):
        return 0,None
    rhs = sub(o,a)
    nd = tuple(-x for x in d)
    denominator = det(e,f,nd)
    if not denominator:
        return (-1 if det(e,f,rhs) == 0 else 0),None
    u = det(rhs,f,nd)/denominator
    w = det(e,rhs,nd)/denominator
    t = det(e,f,rhs)/denominator
    return (1,t) if u >= 0 and w >= 0 and u+w <= 1 and t >= 0 else (0,None)


def box(o,d,lo,hi):
    lower,upper = F(0),None
    for p,q,a,b in zip(o,d,lo,hi):
        if q == 0:
            if not a <= p <= b:
                return False
            continue
        x,y = sorted(((a-p)/q,(b-p)/q))
        lower = max(lower,x)
        upper = y if upper is None else min(upper,y)
        if lower > upper:
            return False
    return True


def topology(scene):
    tris = [tuple(vec(v) for v in tri) for tri in scene["triangles"]]
    require(all(len(t)==3 for t in tris), "triangle vertex count")
    nodes = scene["nodes"]
    bounds = [(vec(n["lo"]),vec(n["hi"])) for n in nodes]
    seen,leaves = set(),[]
    def inside(p,lo,hi):
        return all(a<=x<=b for x,a,b in zip(p,lo,hi))
    def visit(i):
        require(type(i) is int and 0<=i<len(nodes) and i not in seen,"invalid topology")
        seen.add(i)
        lo,hi = bounds[i]
        require(all(a<=b for a,b in zip(lo,hi)), "inverted bounds")
        n = nodes[i]
        if n["children"]:
            require(len(n["children"])==2 and not n["primitives"],"invalid internal node")
            for j in n["children"]:
                require(type(j) is int and 0<=j<len(nodes),"invalid child")
                require(all(inside(p,lo,hi) for p in bounds[j]),"child outside parent")
                visit(j)
        else:
            require(1<=len(n["primitives"])<=4,"invalid leaf")
            for j in n["primitives"]:
                require(type(j) is int and 0<=j<len(tris),"invalid primitive")
                require(all(inside(p,lo,hi) for p in tris[j]),"triangle outside leaf")
                leaves.append(j)
    visit(0)
    require(len(seen)==len(nodes) and sorted(leaves)==list(range(len(tris))),"topology coverage")
    return tris,bounds


def closest(hits, ids):
    return min(((j,hits[j][1]) for j in ids if hits[j][0]==1),
               key=lambda p:(p[1],p[0]),default=(-1,None))


def walk(nodes, boxes):
    stack,vis,tests = [0],[],[]
    while stack:
        i=stack.pop()
        vis.append(i)
        if boxes[i]:
            n=nodes[i]
            stack.extend(reversed(n["children"]))
            tests.extend(n["primitives"])
    return vis,tests


def audit(root, diffs):
    manifest=json.loads((root/"archive-provenance.json").read_text())
    names={"audit.csv","calibration.json","environment-lock.txt","installed-packages.json",
           "labels.json","node-results.csv","result.json","results.csv","workload.json"}
    require(set(manifest["files"])==names,"manifest file set")
    for name in sorted(names):
        data=(root/name).read_bytes()
        meta=manifest["files"][name]
        require(len(data)==meta["bytes"] and hashlib.sha256(data).hexdigest()==meta["sha256"]
                and hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==meta["git_blob_sha1"],
                "archive integrity: "+name)
    report=json.loads((root/"result.json").read_text())
    for name in ("workload","labels"):
        require(report[name+"_sha256"]==manifest["files"][name+".json"]["sha256"],"frozen digest "+name)
    labels=json.loads((root/"labels.json").read_text())
    bylabel={(l["scene"],l["ray"]):l for l in labels}
    require(len(bylabel)==len(labels),"duplicate label")
    cache,seen={},set()
    counts=Counter()
    def compare(kind,k,index,expected,observed):
        if expected!=observed:
            diffs.append(dict(kind=kind,scene=k[0],ray=k[1],index=index,
                              expected=str(expected),observed=str(observed)))
    for scene in json.loads((root/"workload.json").read_text())["scenes"]:
        tris,bounds=topology(scene)
        for i,(o,d) in enumerate(scene["rays"]):
            k=(scene["name"],i)
            require(k not in seen and k in bylabel,"label coverage")
            seen.add(k)
            o,d=vec(o),vec(d)
            require(any(d),"zero direction")
            hits=[triangle(o,d,v) for v in tris]
            cop=[j for j,(s,t) in enumerate(hits) if s==-1]
            truth=closest(hits,range(len(tris)))
            l=bylabel[k]
            compare("coplanar",k,"",cop,l["coplanar"])
            compare("excluded",k,"",bool(cop),l["excluded"])
            compare("nearest_label",k,"",truth,(l["exact_id"],F(l["exact_t"]) if l["exact_t"] is not None else None))
            counts["rays"]+=1
            counts["triangle_pairs"]+=len(tris)
            if cop:
                counts["excluded"]+=1
                continue
            boxes=[box(o,d,*b) for b in bounds]
            counts["box_pairs"]+=len(boxes)
            vis,tests=walk(scene["nodes"],boxes)
            compare("exact_bvh",k,"",truth,closest(hits,tests))
            cache[k]=(hits,boxes,truth,vis,tests)
    require(seen==set(bylabel) and len(cache)==249 and counts["excluded"]==1,"ray coverage")
    scenarios=("scale_only","large_scale","noise_only","combined","drift_quantization")
    policies=("electronic_only","all_optical_fallback","raw","max_min_125")
    expected=set(itertools.product(scenarios,range(10),cache,policies))
    def rowkey(row):
        return (row["scenario"],int(row["repeat"]),(row["scene"],int(row["ray"])),row["policy"])
    seenrows=set()
    with (root/"node-results.csv").open(newline="") as f, (root/"results.csv").open(newline="") as g:
        groups=iter(itertools.groupby(csv.DictReader(f),key=rowkey))
        for row in csv.DictReader(g):
            rk=rowkey(row)
            require(rk in expected and rk not in seenrows,"ray row identity")
            seenrows.add(rk)
            k=rk[2]
            hits,boxes,truth,vis,tests=cache[k]
            group=next(groups,None)
            require(group is not None and group[0]==rk,"node group identity")
            for n in group[1]:
                j=int(n["node"])
                require(0<=j<len(boxes),"node index")
                compare("node_exact",k,(rk,j),int(boxes[j]),int(n["exact"]))
                compare("node_cpu",k,(rk,j),int(boxes[j]),int(n["cpu"]))
                counts["node_rows"]+=1
            rv=json.loads(row["visited_ids"])
            rt=json.loads(row["tested_ids"])
            require(all(type(j) is int and 0<=j<len(hits) for j in rt),"tested primitive ID")
            if rk[3]=="electronic_only":
                compare("electronic_visits",k,rk,vis,rv)
                compare("electronic_tests",k,rk,tests,rt)
            predicted=closest(hits,rt)
            pid=int(row["pred_id"])
            compare("replayed_id",k,rk,predicted[0],pid)
            t=F(float(row["pred_t"])) if row["pred_t"] else None
            if predicted[1] is None or t is None:
                compare("replayed_t_presence",k,rk,predicted[1] is None,t is None)
            else:
                tol=F("1e-10")*(1+abs(predicted[1]))
                compare("replayed_t_tolerance",k,rk,True,abs(t-predicted[1])<=tol)
            tid,tt=truth
            fields={"final_fp":int(tid<0<=pid),"final_fn":int(pid<0<=tid),
                    "wrong_id":int(tid>=0 and pid>=0 and tid!=pid),
                    "nearest_not_tested":int(tid>=0 and tid not in rt),
                    "extra_nodes":len(set(rv)-set(vis)),"missing_nodes":len(set(vis)-set(rv)),
                    "extra_triangles":len(set(rt)-set(tests)),"missing_triangles":len(set(tests)-set(rt))}
            for field,value in fields.items():
                compare(field,k,rk,value,int(row[field]))
            counts["ray_rows"]+=1
        require(next(groups,None) is None,"extra node groups")
    require(seenrows==expected and counts["ray_rows"]==49800 and counts["node_rows"]==664870,"CSV coverage")
    return dict(counts)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    diffs=[]
    try:
        counts=audit(a.archive,diffs)
        report={"passed":True,"scientific_gate":not diffs,"counts":counts,
                "discrepancies":len(diffs)}
    except Exception as exc:
        report={"passed":False,"scientific_gate":False,"error":str(exc),"discrepancies":len(diffs)}
    report.update(stage="C3A independent exact geometry and archived replay",
                  compiled_benchmark="not_run",energy="not_measured",
                  limitations=["Exact replay of archived tested IDs, not independent optical decisions",
                               "No timing or physical performance claims"])
    with (a.output/"discrepancies.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["kind","scene","ray","index","expected","observed"])
        w.writeheader()
        w.writerows(diffs)
    (a.output/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
