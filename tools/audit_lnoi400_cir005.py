"""OPA-CIR-005: two PDK meshes and ideal singular-value attenuation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from scipy.optimize import least_squares
from audit_lnoi400_cir004 import (ROOT, COMMIT, WL, VPI, TOL, topology,
                                  cascade, shape, clements_decompose, assemble,
                                  reciprocal_transmission, lnoi400, error)
from mesh import svd_layer, layer_matrix

OUT=ROOT/"results/opa-cir-005"
SEED=20261120
PORTS=tuple(f"in{i}" for i in range(4))+tuple(f"out{i}" for i in range(4))

def encode(a):
    return np.stack((a.real,a.imag),axis=-1).tolist()

def calibrate(u):
    ops, phases=clements_decompose(u)
    initial=np.array([(v*VPI/np.pi,p*2*VPI/np.pi) for _,v,p in ops]).ravel()
    initial=np.clip(np.r_[initial,phases*2*VPI/np.pi],-26.4,26.4)
    def network(x):
        return topology(ops,x[:12].reshape(6,2),x[12:])
    def residual(x):
        t=cascade(ops,x[:12].reshape(6,2),x[12:])
        g=np.vdot(t,u)/np.vdot(t,t)
        d=(g*t-u).ravel()
        return np.r_[d.real,d.imag]
    naive=network(initial)
    fit=least_squares(residual,initial,bounds=(-26.4,26.4),max_nfev=40)
    x=fit.x
    s=network(x)
    if shape(s[4:,:4],u)[0]>shape(naive[4:,:4],u)[0]:
        x=initial
        s=naive
    return s,naive,dict(settings_v=x.tolist(),shape_error=shape(s[4:,:4],u)[0],
                        naive_shape_error=shape(naive[4:,:4],u)[0],nfev=fit.nfev)

def join(left,right,amplitudes):
    atten=reciprocal_transmission(np.diag(amplitudes))
    blocks={"v":(PORTS,left),"a":(PORTS,atten),"u":(PORTS,right)}
    links=[(("v",f"out{i}"),("a",f"in{i}")) for i in range(4)]
    links += [(("a",f"out{i}"),("u",f"in{i}")) for i in range(4)]
    boundary=[("v",f"in{i}") for i in range(4)]+[("u",f"out{i}") for i in range(4)]
    return assemble(blocks,links,boundary)

def metrics(s,w,scale,x):
    t=s[4:,:4]
    raw=scale*t
    if scale==0:
        gain=0j
        normalized=raw
        rel=None
        mvm=None
    else:
        gain=np.vdot(raw,w)/np.vdot(raw,raw)
        normalized=gain*raw
        rel=float(np.linalg.norm(normalized-w)/np.linalg.norm(w))
        mvm=float(np.linalg.norm(x@(normalized-w).T)/np.linalg.norm(x@w.T))
    return dict(shape_error=rel,heldout_mvm_error=mvm,
                absolute_error=float(np.linalg.norm(normalized-w)),
                uncalibrated_scale_absolute_error=float(np.linalg.norm(raw-w)),
                common_complex_gain=encode(np.asarray(gain)),
                mean_transmission=float(np.linalg.norm(t)**2/4),
                min_transmission=float(np.min(np.sum(abs(t)**2,axis=0))),
                mean_reflection=float(np.linalg.norm(s[:4,:4])**2/4),
                sigma_max=float(np.linalg.svd(s,compute_uv=False)[0]),
                reciprocity_error=error(s,s.T))

def main():
    checkout=Path(os.environ["LXT_PDK_DIR"]).resolve()
    assert Path(lnoi400.__file__).resolve().is_relative_to(checkout)
    assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==COMMIT
    assert not subprocess.check_output(["git","-C",str(checkout),"status","--porcelain","--untracked-files=no"],text=True).strip()
    data=checkout/"lnoi400/data/mmi_2x2_optimized_1550.json"
    assert hashlib.sha256(data.read_bytes()).hexdigest()=="f9016f890543146e1438836da2adb84fc2b14c9a8500311f34bcc640747acb36"
    rng=np.random.default_rng(SEED)
    weights=[("zero",np.zeros((4,4))),("identity",np.eye(4)),
             ("rank_one",np.outer([1,-2,0,1],[.5,0,1,-1])),
             ("signed_diagonal",np.diag([3.,-1.,0.,.25])),
             ("dense_real",rng.normal(size=(4,4))),
             ("dense_complex",rng.normal(size=(4,4))+1j*rng.normal(size=(4,4)))]
    rows=[]
    ideal_max=0.
    for name,w in weights:
        u,singular,vh=np.linalg.svd(w.astype(complex))
        scale=float(singular.max())
        amps=singular/scale if scale else np.zeros(4)
        v_ideal=reciprocal_transmission(vh)
        u_ideal=reciprocal_transmission(u)
        ideal=join(v_ideal,u_ideal,amps)
        ideal_max=max(ideal_max,error(scale*ideal[4:,:4],w),error(layer_matrix(svd_layer(w)),w))
        v,v_naive,v_meta=calibrate(vh)
        u_s,u_naive,u_meta=calibrate(u)
        full=join(v,u_s,amps)
        naive=join(v_naive,u_naive,amps)
        x=rng.normal(size=(32,4))+1j*rng.normal(size=(32,4))
        # Independent direct forward-only product is diagnostic, not reference
        # for the reflected network. Internal feedback is retained in join().
        forward=u_s[4:,:4]@np.diag(amps)@v[4:,:4]
        rows.append(dict(target=name,weight=encode(w.astype(complex)),
                         scale=scale,attenuator_amplitudes=amps.tolist(),
                         input_mesh=v_meta,output_mesh=u_meta,
                         calibrated=metrics(full,w,scale,x),naive=metrics(naive,w,scale,x),
                         reflectionless_difference=error(full[4:,:4],forward),
                         full_scattering=encode(full),heldout_inputs=encode(x)))
    valid=[r for r in rows if r["scale"]>0]
    allmetrics=[r[k] for r in rows for k in ("naive","calibrated")]
    max_sigma=max(m["sigma_max"] for m in allmetrics)
    checks={"ideal_svd_reference":ideal_max<=1e-12,
            "complete_targets":len(rows)==6,
            "zero_target_blocks_light":rows[0]["calibrated"]["mean_transmission"]<=TOL,
            "reciprocity":max(m["reciprocity_error"] for m in allmetrics)<=TOL,
            "attenuation_range":all(all(0<=a<=1 for a in r["attenuator_amplitudes"]) for r in rows),
            "finite_metrics":all(np.isfinite(m["mean_transmission"]) and 0<=m["mean_transmission"]<=1+TOL for m in allmetrics)}
    failures=[k for k,v in checks.items() if not v]
    report=dict(experiment="OPA-CIR-005",pdk_commit=COMMIT,wavelength_um=WL,seed=SEED,
                mesh_count=2,mzi_count=12,mmi_count=24,phase_controls=32,
                ideal_attenuator_count=4,targets=len(rows),checks=checks,failures=failures,
                ideal_max_error=ideal_max,passivity_excess=max(0.,max_sigma-1),
                passivity_eligible=not failures and max_sigma<=1+TOL,
                median_naive_shape_error=float(np.median([r["naive"]["shape_error"] for r in valid])),
                median_calibrated_shape_error=float(np.median([r["calibrated"]["shape_error"] for r in valid])),
                max_calibrated_shape_error=max(r["calibrated"]["shape_error"] for r in valid),
                median_heldout_mvm_error=float(np.median([r["calibrated"]["heldout_mvm_error"] for r in valid])),
                median_nonzero_transmission=float(np.median([r["calibrated"]["mean_transmission"] for r in valid])),
                cases=rows,limitations=["Four attenuators are ideal reflectionless amplitude controls, not PDK devices.",
                "Independent mesh calibration; no joint layer optimization or guaranteed precision.",
                "Scale and fitted complex gain are electronic/coherent readout assumptions, not optical gain.",
                "Single wavelength and deterministic PDK core models; no bypass routing, geometry extraction, driver, DAC/ADC, noise or measurement.",
                "Zero target has undefined relative errors; absolute and optical power reported instead."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},indent=2,allow_nan=False))
    if failures: raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
