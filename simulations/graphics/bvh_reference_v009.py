"""G-004C1: frozen synthetic BVH, exact plane/edge oracle, compiled FP64 kernels.
No timing, GPU or photonic measurement. Coplanar rays excluded at ray level.
"""
import csv
import ctypes
import hashlib
import json
import shutil
import subprocess
import tempfile
from fractions import Fraction as F
from pathlib import Path
import numpy as np
from ray_box_v001 import face_oracle

OUT=Path(__file__).resolve().parents[2]/"results/opa-g-004c1"
SEED=20261401
ATOL=1e-10
RTOL=1e-10
LEAF=4

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def rational(v):return tuple(F(float(x)) for x in v)

def exact_triangle(o,d,v):
    a,b,c=v
    n=cross(sub(b,a),sub(c,a))
    if not any(n):return 0,None
    den=dot(n,d);num=dot(n,sub(a,o))
    if not den:return (-1 if not num else 0),None
    t=num/den
    if t<0:return 0,None
    p=tuple(x+t*y for x,y in zip(o,d))
    for u,w in ((a,b),(b,c),(c,a)):
        if dot(n,cross(sub(w,u),sub(p,u)))<0:return 0,None
    return 1,t

def build(tris):
    nodes=[]
    def visit(ids):
        v=tris[ids].reshape(-1,3)
        lo=v.min(axis=0);hi=v.max(axis=0)
        i=len(nodes);nodes.append(dict(lo=lo.tolist(),hi=hi.tolist(),children=[],primitives=[]))
        if len(ids)<=LEAF:nodes[i]["primitives"]=sorted(ids)
        else:
            axis=int(np.argmax(hi-lo))
            ids=sorted(ids,key=lambda j:(float(tris[j,:,axis].mean()),j))
            mid=len(ids)//2
            nodes[i]["children"]=[visit(ids[:mid]),visit(ids[mid:])]
        return i
    assert visit(list(range(len(tris))))==0
    return nodes

def validate(tris,nodes):
    seen=set();primitives=[]
    def visit(i):
        assert 0<=i<len(nodes) and i not in seen
        seen.add(i);n=nodes[i];lo=np.array(n["lo"]);hi=np.array(n["hi"])
        assert np.all(lo<=hi)
        if n["children"]:
            assert len(n["children"])==2 and not n["primitives"]
            for j in n["children"]:
                child=nodes[j]
                assert np.all(np.array(child["lo"])>=lo) and np.all(np.array(child["hi"])<=hi)
                visit(j)
        else:
            assert 0<len(n["primitives"])<=LEAF
            for j in n["primitives"]:
                assert 0<=j<len(tris)
                assert np.all(tris[j]>=lo) and np.all(tris[j]<=hi)
                primitives.append(j)
    visit(0)
    assert len(seen)==len(nodes) and sorted(primitives)==list(range(len(tris)))

def scenes():
    rng=np.random.default_rng(SEED)
    for name in ("distributed","clustered","anisotropic"):
        n=48
        centers=rng.integers(-32,33,(n,3))/4
        centers[:,2]+=12
        if name=="clustered":centers/=4
        offsets=rng.integers(-8,9,(n,3,3))/8
        tris=centers[:,None,:]+offsets
        rays=np.zeros((80,2,3))
        rays[:,0,:]=rng.integers(-8,9,(80,3))/8
        rays[:,1,:]=rng.integers(-8,9,(80,3))/8
        rays[:,1,2]=1
        # Aim half the rays at an existing vertex or interior dyadic point.
        for i in range(40):
            v=tris[i%n]
            target=(v[0]+v[1]+2*v[2])/4
            rays[i,1]=target-rays[i,0]
        if name=="anisotropic":
            scale=np.array([2.**-12,2.**10,2.**4])
            tris*=scale;rays*=scale
        yield name,tris,rays
    tris=np.array([[[0,0,1],[1,0,1],[0,1,1]],
        [[1,1,1],[0,1,1],[1,0,1]],
        [[0,0,1+2**-40],[1,0,1+2**-40],[0,1,1+2**-40]],
        [[0,0,2],[0,0,2],[1,0,2]],
        [[0,0,3],[1,0,3],[0,1,3]],
        [[0,0,1],[1,0,1],[0,1,1]]],float)
    rays=np.array([[[.5,.5,0],[0,0,1]],[[0,0,0],[0,0,1]],
        [[1,1,0],[0,0,1]],[[2,2,0],[0,0,1]],
        [[.25,.25,1],[0,0,1]],[[.25,.25,2],[0,0,-1]],
        [[.25,.25,1],[1,0,0]],[[.25,.25,0],[1,0,0]],
        [[.25,.25,1+2**-41],[0,0,1]],[[1+2**-40,0,0],[0,0,1]]],float)
    yield "boundary_controls",tris,rays

def compile_kernels(tmp):
    cc=shutil.which("cc")
    if not cc:raise RuntimeError("C compiler required")
    base=Path(__file__).parent
    so=Path(tmp)/"kernels.so"
    flags=["-O3","-std=c11","-fPIC","-shared","-fno-fast-math","-ffp-contract=off"]
    subprocess.run([cc,*flags,str(base/"ray_box_cpu_v006.c"),
        str(base/"ray_triangle_cpu_v009.c"),"-o",str(so)],check=True)
    lib=ctypes.CDLL(str(so));ptr=ctypes.POINTER(ctypes.c_double)
    lib.triangle.argtypes=[ptr,ptr,ptr,ptr];lib.triangle.restype=ctypes.c_int
    lib.raybox.argtypes=[ptr,ctypes.POINTER(ctypes.c_uint8),ctypes.c_size_t];lib.raybox.restype=None
    def ptr_of(a):return a.ctypes.data_as(ptr)
    def tri(o,d,v):
        t=ctypes.c_double()
        status=lib.triangle(ptr_of(o),ptr_of(d),ptr_of(v),ctypes.byref(t))
        return status,t.value if status==1 else None
    def box(o,d,lo,hi):
        a=np.array([o,d,lo,hi],dtype=np.float64)
        hit=ctypes.c_uint8()
        lib.raybox(ptr_of(a),ctypes.byref(hit),1)
        return bool(hit.value)
    return tri,box,dict(flags=flags,compiler=subprocess.check_output([cc,"--version"],text=True).splitlines()[0])

def closest(items):
    return min(items,key=lambda p:(p[1],p[0])) if items else (-1,None)

def walk(nodes,box,tri):
    stack=[0];visits=[];tests=[];hits=[];accepted=[]
    while stack:
        i=stack.pop();n=nodes[i];visits.append(i)
        if not box(i,n):continue
        accepted.append(i)
        if n["children"]:stack.extend(reversed(n["children"]))
        else:
            for j in n["primitives"]:
                tests.append(j)
                status,t=tri(j)
                if status==1:hits.append((j,t))
    return closest(hits),visits,tests,accepted

def csv_write(name,rows,fields):
    with (OUT/name).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    frozen=[]
    for name,tris,rays in scenes():
        tris=np.ascontiguousarray(tris,dtype=np.float64);rays=np.ascontiguousarray(rays,dtype=np.float64)
        nodes=build(tris);validate(tris,nodes)
        assert build(tris)==nodes
        frozen.append(dict(name=name,triangles=tris.tolist(),rays=rays.tolist(),nodes=nodes))
    scene_file=OUT/"scenes.json"
    scene_file.write_text(json.dumps(dict(seed=SEED,leaf_size=LEAF,scenes=frozen),indent=2)+"\n")
    # Read back the frozen represented inputs before evaluation.
    frozen=json.loads(scene_file.read_text())["scenes"]
    rows=[];diffs=[];summary=[];checks={"topology_and_freeze":True}
    with tempfile.TemporaryDirectory() as tmp:
        ctri,cbox,compiler=compile_kernels(tmp)
        for scene in frozen:
            name=scene["name"];tris=np.array(scene["triangles"]);nodes=scene["nodes"]
            validate(tris,nodes)
            vt=[tuple(rational(v) for v in tri) for tri in tris]
            count=dict(scene=name,rays=len(scene["rays"]),excluded=0,eligible=0,
                exact_mismatches=0,cpu_mismatches=0,triangle_mismatches=0,box_mismatches=0,
                brute_triangle_tests=0,exact_nodes=0,cpu_nodes=0,exact_triangles=0,cpu_triangles=0)
            for i,ray in enumerate(scene["rays"]):
                o,d=np.array(ray,dtype=np.float64)
                ro,rd=rational(o),rational(d)
                oracle=[exact_triangle(ro,rd,v) for v in vt]
                cpu=[ctri(o,d,v) for v in tris]
                for j,((s,t),(cs,ct)) in enumerate(zip(oracle,cpu)):
                    if s!=cs or (s==1 and not np.isclose(ct,float(t),atol=ATOL,rtol=RTOL)):
                        count["triangle_mismatches"]+=1
                        diffs.append(dict(scene=name,ray=i,kind="triangle",index=j,exact=str((s,t)),compiled=str((cs,ct))))
                coplanar=[j for j,(s,_) in enumerate(oracle) if s==-1]
                if coplanar:
                    count["excluded"]+=1
                    rows.append(dict(scene=name,ray=i,status="excluded_coplanar",coplanar_ids=json.dumps(coplanar)))
                    continue
                count["eligible"]+=1
                count["brute_triangle_tests"]+=len(tris)
                truth=closest([(j,t) for j,(s,t) in enumerate(oracle) if s==1])
                eb=[face_oracle(o,d,n["lo"],n["hi"]) for n in nodes]
                cb=[cbox(o,d,n["lo"],n["hi"]) for n in nodes]
                for j,(x,y) in enumerate(zip(eb,cb)):
                    if x!=y:
                        count["box_mismatches"]+=1
                        diffs.append(dict(scene=name,ray=i,kind="box",index=j,exact=str(x),compiled=str(y)))
                ex,ev,et,ea=walk(nodes,lambda j,n:eb[j],lambda j:oracle[j])
                cp,cv,ct,ca=walk(nodes,lambda j,n:cb[j],lambda j:cpu[j])
                # Validate actual traversed work, not the counterfactual all-node audit.
                good=cp[0]==truth[0] and (truth[1] is None or np.isclose(cp[1],float(truth[1]),atol=ATOL,rtol=RTOL))
                count["exact_mismatches"]+=int(ex!=truth)
                count["cpu_mismatches"]+=int(not good)
                count["exact_nodes"]+=len(ev);count["cpu_nodes"]+=len(cv)
                count["exact_triangles"]+=len(et);count["cpu_triangles"]+=len(ct)
                if ex!=truth or not good:
                    diffs.append(dict(scene=name,ray=i,kind="nearest",index=-1,exact=str(truth),compiled=str(cp)))
                rows.append(dict(scene=name,ray=i,status="evaluated",coplanar_ids="[]",
                    exact_id=truth[0],exact_t=str(truth[1]) if truth[1] is not None else "",
                    exact_bvh_id=ex[0],exact_bvh_t=str(ex[1]) if ex[1] is not None else "",
                    cpu_id=cp[0],cpu_t=cp[1],cpu_match=bool(good),
                    exact_nodes=json.dumps(ev),cpu_nodes=json.dumps(cv),
                    exact_accepted=json.dumps(ea),cpu_accepted=json.dumps(ca),
                    exact_triangles=json.dumps(et),cpu_triangles=json.dumps(ct),
                    distance_error=abs(cp[1]-float(truth[1])) if cp[1] is not None and truth[1] is not None else ""))
            summary.append(count)
            checks[name+"_exact_bvh"]=count["exact_mismatches"]==0
            checks[name+"_accounting"]=count["rays"]==count["eligible"]+count["excluded"]
    controls={x["ray"]:x for x in rows if x["scene"]=="boundary_controls"}
    expected={0:0,1:0,2:1,3:-1,4:0,5:2,7:-1,8:2,9:-1}
    checks["boundary_known_answers"]=all(controls[i].get("exact_id")==j for i,j in expected.items()) and controls[6]["status"]=="excluded_coplanar"
    fields=list(dict.fromkeys(k for row in rows for k in row))
    csv_write("results.csv",rows,fields)
    csv_write("discrepancies.csv",diffs,["scene","ray","kind","index","exact","compiled"])
    report=dict(experiment="opa-g-004c1",checks=checks,passed=all(checks.values()),
        scientific_gate=all(checks.values()) and all(s["cpu_mismatches"]==s["triangle_mismatches"]==s["box_mismatches"]==0 for s in summary),
        scenes=summary,seed=SEED,scene_sha256=hashlib.sha256(scene_file.read_bytes()).hexdigest(),
        distance_tolerance=dict(abs=ATOL,rel=RTOL,quantity="ray parameter t, not Euclidean distance"),
        compiler=compiler,energy="not_measured",gpu="not_run",
        limitations=["Synthetic scenes, no nearest-distance pruning",
            "Coplanar nondegenerate ray/triangle pairs exclude whole ray from nearest-hit comparison",
            "FP64 C kernels called via Python traversal; not compiled whole traversal or timing benchmark",
            "All-node and all-triangle audit outside counted traversal work",
            "No optical performance or physical hardware claims"])
    (OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not report["passed"]:raise SystemExit("C1 reference gate failed")

if __name__=="__main__":
    main()
