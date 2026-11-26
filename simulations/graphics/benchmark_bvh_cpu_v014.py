"""Matched resident single-thread CPU BVH benchmark on frozen C2 geometry."""
import argparse
import csv
import ctypes as C
import hashlib
import json
import math
import platform
import statistics
import subprocess
import tempfile
from pathlib import Path
from fractions import Fraction
from audit_c2_geometry_v012 import vec, triangle, topology, closest, require

FLAGS=["-O3","-std=c11","-D_POSIX_C_SOURCE=200809L","-fPIC","-shared",
       "-fno-fast-math","-ffp-contract=off"]
REPEATS=40
TARGET_NS=20_000_000
I=C.c_int32
D=C.c_double
IP=C.POINTER(I)
DP=C.POINTER(D)


class Node(C.Structure):
    _fields_=[("lo",D*3),("hi",D*3),("left",I),("right",I),("first",I),("count",I)]


class Hit(C.Structure):
    _fields_=[("id",I),("t",D)]


class Counts(C.Structure):
    _fields_=[("nv",I),("na",I),("nl",I),("nt",I)]


def compile_lib(tmp):
    base=Path(__file__).parent
    so=Path(tmp)/"whole.so"
    sources=["bvh_whole_cpu_v014.c","ray_box_cpu_v006.c","ray_triangle_cpu_v009.c"]
    subprocess.run(["cc",*FLAGS,*[str(base/s) for s in sources],"-o",str(so)],check=True)
    lib=C.CDLL(str(so))
    for name,typ in (("node_size",Node),("hit_size",Hit)):
        fn=getattr(lib,name)
        fn.argtypes=[]
        fn.restype=C.c_size_t
        require(fn()==C.sizeof(typ),"ABI mismatch")
    common=[C.POINTER(Node),I,IP,DP,DP]
    lib.trace_ray.argtypes=common+[IP,C.POINTER(Hit),C.POINTER(Counts),IP,IP,IP]
    lib.fast_batch.argtypes=common+[I,IP,C.POINTER(Hit)]
    lib.time_batches.argtypes=lib.fast_batch.argtypes+[I,DP]
    for name in ("trace_ray","fast_batch","time_batches"):
        getattr(lib,name).restype=C.c_int
    return lib


def verified(root):
    m=json.loads((root/"archive-provenance.json").read_text())
    for name,meta in m["files"].items():
        b=(root/name).read_bytes()
        require(len(b)==meta["bytes"] and hashlib.sha256(b).hexdigest()==meta["sha256"]
                and hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==meta["git_blob_sha1"],
                "archive digest "+name)
    return json.loads((root/"result.json").read_text())


def packed(scene,indices):
    nodes=scene["nodes"]
    ids=[]
    out=[]
    for n in nodes:
        first=len(ids)
        ids.extend(n["primitives"])
        left,right=n["children"] if n["children"] else (-1,-1)
        out.append(Node((D*3)(*n["lo"]),(D*3)(*n["hi"]),left,right,first,len(n["primitives"])))
    tris=[x for tri in scene["triangles"] for p in tri for x in p]
    rays=[x for i in indices for p in scene["rays"][i] for x in p]
    return (Node*len(out))(*out),(I*len(ids))(*ids),(D*len(tris))(*tris),(D*len(rays))(*rays)


def same_hit(a,b):
    return a.id==b.id and a.t==b.t


def match_t(hit,t):
    return math.isinf(hit.t) and hit.t>0 if t is None else (
        math.isfinite(hit.t) and abs(hit.t-t)<=1e-10+1e-10*abs(t))


def percentile(xs,q):
    ys=sorted(xs)
    x=q*(len(ys)-1)
    i=int(x)
    return ys[i]+(ys[min(i+1,len(ys)-1)]-ys[i])*(x-i)


def benchmark(lib,root,prior_roots,diffs,samples,summary,validation):
    original=verified(root)
    manifest=json.loads((root/"archive-provenance.json").read_text())
    for n in ("labels","workload"):
        require(original[n+"_sha256"]==manifest["files"][n+".json"]["sha256"],"frozen digest "+n)
    for p in prior_roots:
        gate=verified(p)
        require(gate["passed"] and gate["scientific_gate"] and gate["discrepancies"]==0,
                "prior scientific gate "+str(p))
    labels=json.loads((root/"labels.json").read_text())
    lm={(l["scene"],l["ray"]):l for l in labels}
    require(len(lm)==len(labels)==250,"label identity")
    expected={}
    repeats={}
    with (root/"results.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            if row["policy"]!="electronic_only":
                continue
            k=(row["scene"],int(row["ray"]))
            fields=("pred_id","pred_t","visited_ids","accepted_ids","tested_ids",
                    "nodes","accepted","leaves","triangles")
            sig=tuple(row[x] for x in fields)
            panel=(row["scenario"],int(row["repeat"]))
            require(panel not in repeats.setdefault(k,set()),"duplicate archived electronic row")
            repeats[k].add(panel)
            if k in expected:
                require(sig==tuple(expected[k][x] for x in fields),"electronic repeat inconsistency")
            else:
                expected[k]=row
    panels={(s,r) for s in ("scale_only","large_scale","noise_only","combined","drift_quantization")
            for r in range(10)}
    require(set(expected)=={k for k,l in lm.items() if not l["excluded"]}
            and len(expected)==249 and all(p==panels for p in repeats.values()),"electronic coverage")
    scenes=json.loads((root/"workload.json").read_text())["scenes"]
    seen=set()
    ready=[]
    def compare(scene,ray,field,want,got):
        if want!=got:
            diffs.append(dict(scene=scene,ray=ray,field=field,expected=str(want),observed=str(got)))
    # Validate all scenes before permitting any timing.
    for scene in scenes:
        name=scene["name"]
        tris,bounds=topology(scene)
        indices=[]
        truths={}
        for ri,(o,d) in enumerate(scene["rays"]):
            k=(name,ri)
            require(k in lm and k not in seen,"scene/ray identity")
            seen.add(k)
            hits=[triangle(vec(o),vec(d),v) for v in tris]
            cop=[j for j,(s,t) in enumerate(hits) if s==-1]
            compare(name,ri,"excluded",lm[k]["excluded"],bool(cop))
            compare(name,ri,"coplanar",lm[k]["coplanar"],cop)
            if cop:
                continue
            indices.append(ri)
            truths[ri]=closest(hits,range(len(tris)))
        require(indices,"no eligible rays")
        nodes,ids,vertices,rays=packed(scene,indices)
        nn,nr=len(nodes),len(indices)
        stack=(I*nn)()
        vis,acc,tested=(I*nn)(),(I*nn)(),(I*len(ids))()
        trace=(Hit*nr)()
        fast=(Hit*nr)()
        totals=dict(nodes=0,accepted=0,leaves=0,triangles=0)
        for i,ri in enumerate(indices):
            counts=Counts()
            ray=C.cast(C.byref(rays,i*6*C.sizeof(D)),DP)
            require(lib.trace_ray(nodes,nn,ids,vertices,ray,stack,C.pointer(trace[i]),C.byref(counts),vis,acc,tested)==0,"trace failure")
            # Array element access above refers to native backing storage.
            h=trace[i]
            row=expected[(name,ri)]
            tid,t=truths[ri]
            l=lm[(name,ri)]
            compare(name,ri,"exact_id",l["exact_id"],tid)
            compare(name,ri,"exact_t",Fraction(l["exact_t"]) if l["exact_t"] is not None else None,t)
            compare(name,ri,"nearest_id",tid,h.id)
            compare(name,ri,"nearest_t",True,match_t(h,float(t) if t is not None else None))
            compare(name,ri,"archived_id",int(row["pred_id"]),h.id)
            compare(name,ri,"archived_t",True,match_t(h,float(row["pred_t"]) if row["pred_t"] else None))
            for field,arr,n in (("visited_ids",vis,counts.nv),("accepted_ids",acc,counts.na),
                                ("tested_ids",tested,counts.nt)):
                compare(name,ri,field,json.loads(row[field]),list(arr[:n]))
            for field,n in (("nodes",counts.nv),("accepted",counts.na),
                            ("leaves",counts.nl),("triangles",counts.nt)):
                compare(name,ri,field,int(row[field]),n)
                totals[field]+=n
            validation.append(dict(scene=name,ray=ri,hit_id=h.id,
                hit_t=h.t if h.id>=0 else "",nodes=counts.nv,accepted=counts.na,
                leaves=counts.nl,triangles=counts.nt))
        args=(nodes,nn,ids,vertices,rays,nr,stack,fast)
        require(lib.fast_batch(*args)==0,"fast batch failure")
        for i,ri in enumerate(indices):
            compare(name,ri,"fast_trace_match",True,same_hit(trace[i],fast[i]))
        ready.append((name,indices,args,trace,totals,
                      dict(nodes=C.sizeof(nodes),primitive_ids=C.sizeof(ids),triangles=C.sizeof(vertices),
                           rays=C.sizeof(rays),stack=C.sizeof(stack),output=C.sizeof(fast))))
    require(seen==set(lm) and len(validation)==249,"validation coverage")
    if diffs:
        return
    for name,indices,args,trace,totals,memory in ready:
        def elapsed(n):
            t=D()
            require(lib.time_batches(*args,n,C.byref(t))==0 and math.isfinite(t.value)
                    and t.value>0,"native timer failure")
            return t.value
        # Warmup and adaptive calibration outside recorded samples.
        n=1
        while elapsed(n)<TARGET_NS and n<65536:
            n*=2
        elapsed(n)
        ns=[]
        for rep in range(REPEATS):
            total=elapsed(n)
            per=total/n
            ns.append(per)
            for i,ri in enumerate(indices):
                compare(name,ri,"timed_trace_match",True,same_hit(trace[i],args[-1][i]))
            samples.append(dict(scene=name,repeat=rep,batches=n,elapsed_ns=total,batch_ns=per,
                                rays_per_batch=len(indices),nodes_per_batch=totals["nodes"]))
        p50=statistics.median(ns)
        summary.append(dict(scene=name,rays=len(indices),repeats=REPEATS,batches_per_sample=n,
                            p50_batch_ns=p50,p95_batch_ns=percentile(ns,.95),
                            rays_per_second=len(indices)*1e9/p50,
                            nodes_per_second=totals["nodes"]*1e9/p50,
                            operations_per_batch=totals,allocated_bytes=memory))


def write_csv(path,fields,rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("--prior",type=Path,nargs=2,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    diffs,samples,summary,validation=[],[],[],[]
    report=dict(stage="C3A whole compiled CPU BVH",passed=False,scientific_gate=False,
                energy="not_measured",gpu="not_run")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            benchmark(compile_lib(tmp),a.archive,a.prior,diffs,samples,summary,validation)
        report.update(passed=True,scientific_gate=not diffs and len(summary)==4,
                      timing_valid=not diffs and len(summary)==4)
    except Exception as exc:
        report.update(error=str(exc),timing_valid=False)
    cpu="unknown"
    if Path("/proc/cpuinfo").exists():
        cpu=next((x.split(":",1)[1].strip() for x in Path("/proc/cpuinfo").read_text().splitlines()
                  if x.startswith("model name")),"unknown")
    report.update(discrepancies=len(diffs),scenes=summary,
                  compiler=subprocess.check_output(["cc","--version"],text=True).splitlines()[0],
                  flags=FLAGS,cpu=cpu,os=platform.platform(),architecture=platform.machine(),
                  threads=1,timer="native CLOCK_MONOTONIC",node_bytes=C.sizeof(Node),hit_bytes=C.sizeof(Hit),
                  layout="contiguous AoS nodes/rays/triangles/hits, separate primitive IDs and reusable stack",
                  timing_boundary="resident native batch, includes output writes and local box packing; excludes host packing, allocation, Python dispatch, oracle and trace",
                  limitations=["Shared CI CPU, no affinity or frequency control",
                               "Small synthetic scenes, warm resident data, no distance pruning",
                               "No GPU, optical latency, host-inclusive or energy measurement"])
    write_csv(a.output/"discrepancies.csv",["scene","ray","field","expected","observed"],diffs)
    write_csv(a.output/"timings.csv",["scene","repeat","batches","elapsed_ns","batch_ns","rays_per_batch","nodes_per_batch"],samples)
    write_csv(a.output/"validation.csv",["scene","ray","hit_id","hit_t","nodes","accepted","leaves","triangles"],validation)
    (a.output/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
