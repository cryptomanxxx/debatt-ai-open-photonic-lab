"""G-004A: frozen pairwise ray/AABB workload and resident CPU timing.

No GPU or energy measurement. Exact labels are generated outside timing.
"""
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from ray_box_v001 import face_oracle
from side_test_v002 import side_test
from boundary_readout_v005 import boundary, exact_geometry

OUT = Path(__file__).resolve().parents[2] / "results" / "opa-g-004a"
SEEDS = {"calibration": 20261201, "development": 20261202, "heldout": 20261203}
BATCHES = (32, 256, 1024)
REPEATS = 21
WARMUPS = 3


def panels(seed):
    rng = np.random.default_rng(seed)
    n = 2048
    o = rng.integers(-768, 769, (n, 3))/256
    d = rng.integers(-256, 257, (n, 3))/256
    yield "uniform", np.stack((o, d, np.full_like(o,-1), np.full_like(o,1)),axis=1)
    lo = rng.integers(-512,513,(n,3))/256
    hi = lo + rng.integers(0,513,(n,3))/256
    yield "translated", np.stack((o,d,lo,hi),axis=1)
    cases, _ = boundary(seed+100)
    yield "boundary", np.asarray(cases)
    # A synthetic camera/grid of boxes: correlated rays and shared boxes.
    # No BVH traversal, triangle shading or claim of production representativeness.
    centers = rng.integers(-32,33,(32,3))/4
    centers[:,2] += 12
    half = rng.integers(1,9,(32,3))/4
    origin = np.zeros((64,3))
    origin[:,:2] = rng.integers(-4,5,(64,2))/16
    direction = np.column_stack((rng.integers(-64,65,(64,2))/64,np.ones(64)))
    yield "scene_like", np.stack((np.repeat(origin,32,axis=0),
        np.repeat(direction,32,axis=0),np.tile(centers-half,(64,1)),
        np.tile(centers+half,(64,1))),axis=1)


def controls():
    lo,hi=(-1,-1,-1),(1,1,1)
    return [
        ("parallel_hit",(-2,0,0),(1,0,0),lo,hi,True),
        ("parallel_miss",(-2,2,0),(1,0,0),lo,hi,False),
        ("inside",(0,0,0),(0,1,0),lo,hi,True),
        ("behind",(2,0,0),(1,0,0),lo,hi,False),
        ("negative",(2,0,0),(-1,0,0),lo,hi,True),
        ("tangent",(-2,0,0),(1,1,0),lo,hi,True),
        ("point",(-2,0,0),(1,0,0),(0,0,0),(0,0,0),True),
        ("plane",(-2,0,0),(1,0,0),(0,-1,-1),(0,1,1),True),
        ("stationary_hit",(0,0,0),(0,0,0),lo,hi,True),
        ("stationary_miss",(2,0,0),(0,0,0),lo,hi,False),
        ("near_miss",(-2,2**-40,0),(1,1,0),lo,hi,False),
    ]


def slab_numpy(a):
    o,d,lo,hi = a.transpose(1,0,2)
    parallel = d == 0
    reject = np.any(parallel & ((o<lo)|(o>hi)),axis=1)
    t0 = np.full_like(o,-np.inf)
    t1 = np.full_like(o,np.inf)
    np.divide(lo-o,d,out=t0,where=~parallel)
    np.divide(hi-o,d,out=t1,where=~parallel)
    near = np.maximum(0,np.max(np.minimum(t0,t1),axis=1))
    far = np.min(np.maximum(t0,t1),axis=1)
    return (~reject) & (near<=far)


def errors(pred, truth):
    fp=int(np.sum(pred & ~truth))
    fn=int(np.sum(~pred & truth))
    hits=int(np.sum(truth))
    misses=len(truth)-hits
    return dict(samples=len(truth),hits=hits,misses=misses,fp=fp,fn=fn,
                fpr=fp/misses if misses else None,fnr=fn/hits if hits else None)


def digest(a):
    return hashlib.sha256(a.tobytes(order="C")).hexdigest()


def cpu_info():
    path=Path("/proc/cpuinfo")
    model=next((l.split(":",1)[1].strip() for l in path.read_text().splitlines()
                if l.startswith("model name")),None) if path.exists() else None
    return dict(model=model,machine=platform.machine(),platform=platform.platform(),
                python=sys.version,numpy=np.__version__,logical_cpus=os.cpu_count(),
                affinity_cpus=len(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None,
                thread_env={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")})


def compile_kernel(directory):
    """Independent C scalar slab loop; no fast-math or parallel execution."""
    import ctypes
    compiler=shutil.which("cc")
    if compiler is None:
        return None, {"status":"not_run","reason":"cc unavailable"}
    source=Path(__file__).with_name("ray_box_cpu_v006.c")
    lib=Path(directory)/"raybox.so"
    flags=["-O3","-std=c11","-fPIC","-shared","-fno-fast-math","-ffp-contract=off"]
    version=subprocess.run([compiler,"--version"],check=True,capture_output=True,text=True).stdout.splitlines()[0]
    subprocess.run([compiler,*flags,str(source),"-o",str(lib)],check=True,capture_output=True)
    library=ctypes.CDLL(str(lib))
    func=library.raybox
    func.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_uint8),ctypes.c_size_t]
    func.restype=None
    def run(a):
        if a.dtype!=np.float64 or not a.flags.c_contiguous:
            raise ValueError("compiled CPU requires contiguous native float64")
        result=np.empty(len(a),dtype=np.uint8)
        func(a.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
             result.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),len(a))
        return result.view(np.bool_)
    return run,dict(status="executed",compiler=version,flags=flags)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checks={}
    manifest=[]
    frozen=[]
    seen=set()
    # Persist complete represented inputs, labels, stable pair IDs and guard counts.
    # Deduplicate across partitions on exact represented numeric tuples, including signed zero.
    path=OUT/"workload.csv"
    with path.open("w",newline="") as stream:
        writer=csv.writer(stream)
        writer.writerow(["split","panel","pair_id",*[f"{v}_{ax}" for v in ("o","d","lo","hi") for ax in "xyz"],
                         "hit","active_axes","guard","side_tests"])
        for split,seed in SEEDS.items():
            for name,a in panels(seed):
                generated=len(a)
                keep=[]
                for case in a:
                    key=tuple(float(v) for v in case.flat)
                    if key not in seen:
                        seen.add(key)
                        keep.append(case)
                a=np.ascontiguousarray(keep,dtype="<f8").reshape(-1,4,3)
                truth=np.array([face_oracle(*case) for case in a],dtype=bool)
                side=[side_test(*case)[0] for case in a]
                exact=[exact_geometry(case) for case in a]
                guard=np.array([g for g,_ in exact])
                sides=np.array([len(m) for _,m in exact])
                active=np.count_nonzero(a[:,1,:],axis=1)
                checks[f"{split}_{name}_oracle_agreement"]=bool(np.array_equal(side,truth))
                checks[f"{split}_{name}_guard_agreement"]=all(bool(t)==(g>0 if g else min(m)>=0) for t,(g,m) in zip(truth,exact))
                checks[f"{split}_{name}_side_counts"]=bool(np.all(sides==np.where(guard==0,active*(active-1),0)))
                checks[f"{split}_{name}_nonempty"]=len(a)>=max(BATCHES)
                for i,(case,t,k,g,s) in enumerate(zip(a,truth,active,guard,sides)):
                    writer.writerow([split,name,i,*map(repr,map(float,case.flat)),int(t),int(k),int(g),int(s)])
                manifest.append(dict(split=split,panel=name,seed=seed,generated=generated,samples=len(a),removed_duplicates=generated-len(a),
                    input_sha256=digest(a),label_sha256=digest(truth.astype("u1")),
                    hits=int(np.sum(truth)),misses=int(np.sum(~truth)),optical=int(np.sum(guard==0)),
                    guard_accept=int(np.sum(guard==1)),guard_reject=int(np.sum(guard==-1)),side_tests=int(np.sum(sides))))
                frozen.append((split,name,a,truth))
    # Verify decimal CSV round trip and ordering before any performance timing.
    with path.open(newline="") as stream:
        reader=csv.reader(stream)
        next(reader)
        for split,name,a,t in frozen:
            for i,(case,label) in enumerate(zip(a,t)):
                row=next(reader)
                assert row[:3]==[split,name,str(i)]
                assert np.array_equal(np.array(row[3:15],float),case.ravel())
                assert int(row[15])==int(label)
        assert next(reader,None) is None
    checks["csv_roundtrip"]=True
    checks["unique_pairs"]=len(seen)==sum(len(a) for _,_,a,_ in frozen)
    workload=dict(schema=1,layout="C-order little-endian float64 [pair, o/d/lo/hi, xyz]; labels uint8",seeds=SEEDS,
        csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),panels=manifest)
    (OUT/"workload-manifest.json").write_text(json.dumps(workload,indent=2)+"\n")
    rows=[]; timing=[]
    with tempfile.TemporaryDirectory() as tmp:
        compiled,compiler=compile_kernel(tmp)
        methods={"numpy_f64":slab_numpy,"numpy_f32":slab_numpy}
        if compiled is not None:
            methods["compiled_f64"]=compiled
        for name,o,d,lo,hi,expected in controls():
            a=np.array([[o,d,lo,hi]],dtype=np.float64)
            checks["control_"+name]=face_oracle(o,d,lo,hi)==expected and all(
                bool(method(a)[0])==expected for key,method in methods.items() if key!="numpy_f32")
        for split,panel,a,truth in frozen:
            for name,method in methods.items():
                resident=np.ascontiguousarray(a,dtype=np.float32 if name=="numpy_f32" else np.float64)
                # Isolate input rounding from computation on rounded inputs.
                rounded_truth=(np.array([face_oracle(*case) for case in resident],bool)
                               if name=="numpy_f32" else truth)
                pred=method(resident)
                base=errors(pred,truth)
                rnd=errors(rounded_truth,truth)
                arithmetic=errors(pred,rounded_truth)
                rows.append(dict(split=split,panel=panel,method=name,**base,
                    input_fp=rnd["fp"],input_fn=rnd["fn"],
                    arithmetic_fp=arithmetic["fp"],arithmetic_fn=arithmetic["fn"],
                    changed_pairs=int(np.sum(np.any(resident.astype(np.float64)!=a,axis=(1,2))))))
                checks[f"{split}_{panel}_{name}_counts"]=bool(pred.shape==truth.shape and
                    base["fp"]<=base["misses"] and base["fn"]<=base["hits"])
                # Accuracy is reported, not silently imposed on floating point.
                # Timing only held-out, resident CPU inputs, includes output allocation
                # and NumPy temporaries / ctypes call overhead. Same contiguous prefixes.
                if split!="heldout":
                    continue
                for batch in (*BATCHES,len(a)):
                    x=resident[:batch]
                    expect=pred[:batch]
                    for _ in range(WARMUPS):
                        method(x)
                    samples=[]
                    for rep in range(REPEATS):
                        start=time.perf_counter_ns()
                        y=method(x)
                        elapsed=time.perf_counter_ns()-start
                        assert np.array_equal(y,expect)
                        samples.append(elapsed)
                        timing.append(dict(panel=panel,method=name,batch=batch,repeat=rep,elapsed_ns=elapsed))
                    p50,p95=np.quantile(samples,[.5,.95])
                    rows.append(dict(split=split,panel=panel,method=name,
                        **errors(expect,truth[:batch]),batch=batch,p50_ns=float(p50),
                        p95_ns=float(p95),tests_per_second=float(batch/(p50*1e-9))))
    checks["positive_timing"]=all(t["elapsed_ns"]>0 for t in timing)
    checks["timing_count"]=len(timing)==4*len(methods)*4*REPEATS
    result=dict(experiment="opa-g-004a",checks=checks,passed=all(checks.values()),
        workload_panels=len(manifest),workload_pairs=len(seen),workload_manifest_sha256=hashlib.sha256((OUT/"workload-manifest.json").read_bytes()).hexdigest(),
        timing_rows=len(timing),summary_rows=len(rows),warmups=WARMUPS,repeats=REPEATS,
        cpu=cpu_info(),compiled_cpu=compiler,gpu={"status":"not_run","reason":"no GPU backend configured"},
        energy={"status":"not_measured"},limitations=[
            "Synthetic paired AABB tests, not BVH traversal or rendering",
            "Exact reference on represented inputs; floating precision errors reported",
            "Resident CPU batch latency includes Python dispatch and output allocation; no DMA or GPU timing",
            "Shared CI timings descriptive, not device performance guarantees",
            "No optical performance or energy comparison"])
    def write_csv(name,data):
        fields=list(dict.fromkeys(k for row in data for k in row))
        with (OUT/name).open("w",newline="") as stream:
            w=csv.DictWriter(stream,fieldnames=fields)
            w.writeheader();w.writerows(data)
    write_csv("results.csv",rows)
    write_csv("timings.csv",timing)
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise SystemExit("G-004A numerical gate failed")


if __name__=="__main__":
    main()
