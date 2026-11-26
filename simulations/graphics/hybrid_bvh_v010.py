"""G-004C2: frozen hybrid BVH, matched traversal and counterfactual node audit."""
import csv
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
import bvh_reference_v009 as ref
from robustness_v008 import SCENARIOS, REPEATS, COLS, extra
from electronic_baseline_v006 import panels
from photonic_side_v004 import operands, optical, ideal
from boundary_readout_v005 import exact_geometry

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"results/opa-g-004c2"
ARCH=ROOT/"results/ci-originals"
OLD_A=ARCH/"opa-g-004a/45841325612-15128251841"
OLD_B=ARCH/"opa-g-004b2/45858488663-15136519355"
OLD_C=ARCH/"opa-g-004c1/45862577503-15137988857"
SCENE_SEED=20261402
CAL_SEED=20261403
NOISE_SEED=20261404
POLICIES=("electronic_only","all_optical_fallback","raw","max_min_125")

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verified(root,name):
    p=root/name
    m=json.loads((root/"archive-provenance.json").read_text())["files"][name]
    assert p.stat().st_size==m["bytes"] and sha(p)==m["sha256"]
    return p

def key(case):return tuple(float(v) for a in case for v in a)
def pairs(scene):
    for o,d in scene["rays"]:
        for node in scene["nodes"]:
            yield (o,d,node["lo"],node["hi"])

def freeze():
    old=set()
    for root in (OLD_A,OLD_B):
        with verified(root,"workload.csv").open(newline="") as f:
            old.update(tuple(float(row[c]) for c in COLS) for row in csv.DictReader(f))
    previous=json.loads(verified(OLD_C,"scenes.json").read_text())["scenes"]
    for s in previous:old.update(key(p) for p in pairs(s))
    seen=set(old);scenes=[]
    # Reuse C1 generator without changing historical source.
    original=ref.SEED
    try:
        ref.SEED=SCENE_SEED
        for name,tris,rays in ref.scenes():
            if name=="boundary_controls":
                # Translate exact dyadic fixture, with historical fixture retained only as diagnostic.
                # This is not an independent boundary distribution.
                shift=np.array([17.,-11.,8.])
                tris=tris+shift;rays=rays.copy();rays[:,0]+=shift
                name="translated_boundary"
            nodes=ref.build(tris);ref.validate(tris,nodes)
            s=dict(name=name,triangles=tris.tolist(),rays=rays.tolist(),nodes=nodes)
            keys={key(p) for p in pairs(s)}
            assert not keys & old, "historical scene pair overlap"
            assert not keys & (seen-old), "cross-scene overlap"
            seen.update(keys)
            scenes.append(s)
    finally:ref.SEED=original
    cal=[];meta=[]
    for name,cases in (*panels(CAL_SEED),*extra(CAL_SEED)):
        kept=[]
        for case in cases:
            k=key(case)
            if k not in seen:
                seen.add(k);kept.append(case.tolist())
        assert kept
        cal.append(dict(panel=name,cases=kept))
        meta.append(dict(panel=name,generated=len(cases),kept=len(kept)))
    frozen=dict(scene_seed=SCENE_SEED,calibration_seed=CAL_SEED,scenes=scenes,calibration=cal,
        calibration_counts=meta,historical_unique_pairs=len(old),
        historical_boundary_fixture="C1 archive only; not evaluated or pooled")
    path=OUT/"workload.json"
    path.write_text(json.dumps(frozen,separators=(",",":"))+"\n")
    return json.loads(path.read_text())

def precompute(frozen,ctri,cbox):
    audits=[];data=[];labels=[]
    for si,s in enumerate(frozen["scenes"]):
        tris=np.array(s["triangles"],dtype=float);nodes=s["nodes"]
        ref.validate(tris,nodes)
        vt=[tuple(ref.rational(v) for v in tri) for tri in tris]
        for ri,ray in enumerate(s["rays"]):
            o,d=np.array(ray,dtype=float)
            ro,rd=ref.rational(o),ref.rational(d)
            exact=[ref.exact_triangle(ro,rd,v) for v in vt]
            cop=[i for i,(status,_) in enumerate(exact) if status==-1]
            truth=ref.closest([(i,t) for i,(status,t) in enumerate(exact) if status==1])
            labels.append(dict(scene=s["name"],ray=ri,excluded=bool(cop),coplanar=cop,
                exact_id=truth[0],exact_t=str(truth[1]) if truth[1] is not None else None))
            if cop:continue
            cpu=[ctri(o,d,v) for v in tris]
            for i,((a,t),(b,u)) in enumerate(zip(exact,cpu)):
                if a!=b or (a==1 and not np.isclose(u,float(t),atol=ref.ATOL,rtol=ref.RTOL)):
                    audits.append(dict(scene=s["name"],ray=ri,kind="triangle",index=i,exact=str((a,t)),observed=str((b,u))))
            eb=[];cb=[];ops=[]
            for ni,n in enumerate(nodes):
                case=(o,d,n["lo"],n["hi"])
                e=ref.face_oracle(*case);c=cbox(*case);op=operands(case)
                guard=-1 if op is None else 1 if not op else 0
                eg,ms=exact_geometry(case)
                eb.append(e);cb.append(c);ops.append((guard,np.asarray(op or [],float).reshape(-1,4)))
                if c!=e:audits.append(dict(scene=s["name"],ray=ri,kind="cpu_box",index=ni,exact=str(e),observed=str(c)))
                if guard!=eg or (guard and (guard>0)!=e):
                    audits.append(dict(scene=s["name"],ray=ri,kind="guard",index=ni,exact=str((eg,e)),observed=str(guard)))
                assert (eg>0 if eg else min(ms)>=0)==e
            ex,ev,et,ea=ref.walk(nodes,lambda j,n:eb[j],lambda j:exact[j])
            assert ex==truth
            cp,cv,ct,ca=ref.walk(nodes,lambda j,n:cb[j],lambda j:cpu[j])
            data.append((si,ri,s["name"],nodes,truth,cpu,eb,cb,ops,cv,ct,ca))
    (OUT/"labels.json").write_text(json.dumps(labels,indent=2)+"\n")
    return data,audits,labels

def calibration(frozen):
    out=[]
    for panel in frozen["calibration"]:
        x=[];groups=[];mins=[]
        for case in panel["cases"]:
            op=operands(case);eg,ms=exact_geometry(case)
            if eg==0:
                assert op and len(op)==len(ms)
                groups.append((len(x),len(x)+len(op)));x.extend(op);mins.append(float(min(ms)))
            else:assert op is None if eg<0 else op==[]
        out.append((np.asarray(x,float).reshape(-1,4),groups,np.array(mins)))
    return out

def model(j,rep,cal):
    name,s,b,p,l,n=SCENARIOS[j]
    rng=np.random.default_rng(np.random.SeedSequence([NOISE_SEED,j,rep,0]))
    bias=rng.uniform(-b,b,4)
    def read(x,stage,scene,ray=0,node=0):
        gen=np.random.default_rng(np.random.SeedSequence([NOISE_SEED,j,rep,stage,scene,ray,node]))
        drift=np.zeros(4)
        if name=="drift_quantization":
            x=np.rint(x*2047)/2047
            if stage==2:
                drift=np.random.default_rng(np.random.SeedSequence([NOISE_SEED,j,rep,3,scene])).uniform(-.002,.002,4)
        return optical(x,s,bias+drift,np.array([0.,p]),np.array([0.,l]),gen.normal(0,n,len(x)))
    u=rng.uniform(-1,1,(8192,4));y=read(u,0,0)
    gain,offset=np.linalg.lstsq(np.column_stack([y,np.ones(len(y))]),ideal(u),rcond=None)[0]
    assert np.isfinite(gain) and gain>0 and np.isfinite(offset)
    residual=[]
    for i,(x,groups,mins) in enumerate(cal):
        y=gain*read(x,1,i)+offset
        residual.extend(abs(np.array([min(y[a:b]) for a,b in groups])-mins))
    q=1.25*max(residual)
    assert np.isfinite(q) and q>=0
    return read,float(gain),float(offset),float(q)

def write_csv(name,rows,fields=None):
    with (OUT/name).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        w.writeheader();w.writerows(rows)

def evaluate(data,models):
    rows=[];node_rows=[]
    for (j,rep),(read,gain,offset,q) in models.items():
        name=SCENARIOS[j][0]
        for si,ri,scene,nodes,truth,cpu,eb,cb,ops,cv,ct,ca in data:
            # Cache counterfactual readouts for paired policy replay, never count unvisited work.
            raw=[];amb=[];mins=[]
            for ni,(guard,x) in enumerate(ops):
                m=None if guard else float(min(gain*read(x,2,si,ri,ni)+offset))
                raw.append(guard>0 if guard else m>=0)
                amb.append(not guard and abs(m)<=q)
                mins.append(m)
            for policy in POLICIES:
                fb=[not g and (policy=="all_optical_fallback" or (policy=="max_min_125" and a))
                    for (g,_),a in zip(ops,amb)]
                pred=cb if policy=="electronic_only" else [c if f else r for c,f,r in zip(cb,fb,raw)]
                hit,vis,tests,accepted=ref.walk(nodes,lambda i,n:pred[i],lambda i:cpu[i])
                opt=[i for i in vis if not ops[i][0] and policy!="electronic_only"]
                fallback=sum(fb[i] for i in opt)
                sides=sum(len(ops[i][1]) for i in opt)
                fp=sum(pred[i] and not eb[i] for i in vis)
                fn=sum(not pred[i] and eb[i] for i in vis)
                rawfp=sum(raw[i] and not eb[i] for i in vis) if policy!="electronic_only" else fp
                rawfn=sum(not raw[i] and eb[i] for i in vis) if policy!="electronic_only" else fn
                tid,t=truth;pid,u=hit
                dist=abs(u-float(t)) if t is not None and u is not None else None
                bad_distance=tid>=0 and pid>=0 and not np.isclose(u,float(t),atol=ref.ATOL,rtol=ref.RTOL)
                rows.append(dict(scenario=name,repeat=rep,scene=scene,ray=ri,policy=policy,
                    exact_id=tid,exact_t=str(t) if t is not None else "",pred_id=pid,pred_t=u,
                    final_fp=int(tid<0<=pid),final_fn=int(pid<0<=tid),
                    wrong_id=int(tid>=0 and pid>=0 and tid!=pid),distance_error=dist,
                    distance_fail=int(bad_distance),nearest_not_tested=int(tid>=0 and tid not in tests),
                    node_fp=fp,node_fn=fn,raw_fp=rawfp,raw_fn=rawfn,
                    nodes=len(vis),accepted=len(accepted),leaves=sum(not nodes[i]["children"] for i in accepted),
                    triangles=len(tests),extra_nodes=len(set(vis)-set(cv)),missing_nodes=len(set(cv)-set(vis)),
                    extra_triangles=len(set(tests)-set(ct)),missing_triangles=len(set(ct)-set(tests)),
                    guards=len(vis)-len(opt) if policy!="electronic_only" else 0,
                    optical=len(opt),fallback=fallback,sides=sides,driven_operands=4*sides,
                    visited_ids=json.dumps(vis),accepted_ids=json.dumps(accepted),tested_ids=json.dumps(tests)))
                for i in vis:
                    node_rows.append(dict(scenario=name,repeat=rep,scene=scene,ray=ri,policy=policy,node=i,
                        exact=int(eb[i]),cpu=int(cb[i]),guard=ops[i][0],raw=int(raw[i] if policy!="electronic_only" else cb[i]),
                        decision=int(pred[i]),fallback=int(fb[i]),minimum=mins[i] if policy!="electronic_only" else None))
    return rows,node_rows

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    frozen=freeze();cal=calibration(frozen)
    with tempfile.TemporaryDirectory() as tmp:
        ctri,cbox,compiler=ref.compile_kernels(tmp)
        data,audits,labels=precompute(frozen,ctri,cbox)
        models={(j,k):model(j,k,cal) for j in range(len(SCENARIOS)) for k in range(REPEATS)}
        params=[dict(scenario=SCENARIOS[j][0],repeat=k,gain=g,offset=o,threshold=q)
                for (j,k),(_,g,o,q) in models.items()]
        (OUT/"calibration.json").write_text(json.dumps(params,indent=2)+"\n")
        rows,nodes=evaluate(data,models)
    write_csv("results.csv",rows)
    write_csv("node-results.csv",nodes)
    write_csv("audit.csv",audits,["scene","ray","kind","index","exact","observed"])
    checks=dict(frozen_and_disjoint=True,exact_bvh_oracle=True,
        row_count=len(rows)==len(data)*len(POLICIES)*len(SCENARIOS)*REPEATS,
        node_count=len(nodes)==sum(r["nodes"] for r in rows),
        accounting=all(0<=r["fallback"]<=r["optical"] and r["driven_operands"]==4*r["sides"]
            and (r["policy"]=="electronic_only" or r["guards"]+r["optical"]==r["nodes"]) for r in rows),
        control_fallback=all(r["fallback"]==r["optical"] for r in rows if r["policy"]=="all_optical_fallback"))
    metrics=("final_fp","final_fn","wrong_id","distance_fail","nearest_not_tested","node_fp","node_fn",
        "raw_fp","raw_fn","nodes","accepted","leaves","triangles","extra_nodes","missing_nodes",
        "extra_triangles","missing_triangles","guards","optical","fallback","sides","driven_operands")
    summary=[]
    for name,*_ in SCENARIOS:
        for policy in POLICIES:
            rs=[r for r in rows if r["scenario"]==name and r["policy"]==policy]
            summary.append(dict(scenario=name,policy=policy,rays=len(rs),
                **{k:sum(r[k] for r in rs) for k in metrics}))
    def gate(policy,fields):
        return all(not any(r[k] for k in fields) for r in rows if r["policy"]==policy)
    final_fields=("final_fp","final_fn","wrong_id","distance_fail")
    node_fields=("node_fp","node_fn")
    gates={p:dict(final=gate(p,final_fields),node=gate(p,node_fields)) for p in POLICIES}
    useful=all(s["optical"]>s["fallback"] for s in summary if s["policy"]=="max_min_125")
    report=dict(experiment="opa-g-004c2",checks=checks,passed=all(checks.values()),
        scientific_gate=not audits and gates["electronic_only"]["final"] and gates["electronic_only"]["node"]
            and gates["max_min_125"]["final"] and gates["max_min_125"]["node"] and useful,
        gates=gates,useful_every_scenario=useful,audit_discrepancies=len(audits),
        eligible_rays=len(data),excluded_rays=len(labels)-len(data),rows=len(rows),node_rows=len(nodes),
        summary=summary,compiler=compiler,workload_sha256=sha(OUT/"workload.json"),
        labels_sha256=sha(OUT/"labels.json"),repeats=REPEATS,noise_seed=NOISE_SEED,
        gpu="not_run",energy="not_measured",limitations=[
            "Synthetic scenes; translated boundary fixture correlated with C1",
            "Counterfactual cache for paired replay, only visited operations counted; not implementation timing",
            "Electronic guards and compiled fallback audited independently, no oracle substitution",
            "No physical speed or energy measurement; normalized optical model"])
    (OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not report["passed"]:raise SystemExit("C2 implementation gate failed")

if __name__=="__main__":
    main()
