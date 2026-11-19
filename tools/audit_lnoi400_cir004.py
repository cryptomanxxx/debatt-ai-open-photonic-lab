"""OPA-CIR-004: PDK-based four-mode mesh with independent EO phase controls."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from functools import partial
import numpy as np
from scipy.optimize import least_squares
from audit_lnoi400_cir002 import ROOT, COMMIT, PORTS, TOL, dense, error, assemble, models, sax, lnoi400
from audit_lnoi400_cir003 import EXT, CONNECTIONS, BOUNDARY, LINKS, EXTERNAL
from mesh import clements_decompose, mesh_columns, mesh_matrix
from mzi import haar_unitary
from scattering_network import reciprocal_transmission

OUT=ROOT/"results/opa-cir-004"
WL=1.55
LENGTH=5000.
BIAS=700.
VPI=6.6
SEED=20261119
# Cache the native fixed model and obtain voltage dependence directly from
# upstream EO models; no synthetic coupler phase or loss.
MMI=dense(models.mmi2x2_optimized1550(wl=WL),PORTS)
TO=dense(models.to_phase_shifter(wl=WL,heater_length=BIAS,V_dc=0.),("o1","o2"))
EO0=dense(models.eo_phase_shifter(wl=WL,length=LENGTH,V_dc=0.),("o1","o2"))

def eo(v, wl=WL):
    # Upstream EO phase shifter uses voltage/Vpi in gplugins; evaluate
    # its exact native API, never fit a transmission magnitude.
    return dense(models.eo_phase_shifter(wl=wl,length=LENGTH,V_dc=float(v)),("o1","o2"))

def physical_core(theta_voltage, wl=WL):
    mmi=MMI if wl==WL else dense(models.mmi2x2_optimized1550(wl=wl),PORTS)
    to=TO if wl==WL else dense(models.to_phase_shifter(wl=wl,heater_length=BIAS,V_dc=0.),("o1","o2"))
    b={"left":(PORTS,mmi),"right":(PORTS,mmi),
       "eo_top":(("o1","o2"),eo(theta_voltage,wl)),
       "eo_bottom":(("o1","o2"),eo(-theta_voltage,wl)),
       "ht_top":(("o1","o2"),to),"ht_bottom":(("o1","o2"),to)}
    return assemble(b,LINKS,EXTERNAL)

def topology(ops, settings, output, ideal=False, wl=WL):
    eo0=EO0 if wl==WL else eo(0.,wl)
    # Sequential wiring is equivalent to rectangular disjoint-column
    # ordering; physical bypass routing is not yet included.
    blocks={}; links=[]; tails=[None]*4; inputs=[None]*4
    def append(name, ports, s, modes):
        blocks[name]=(ports,s)
        n=len(modes)
        for k,m in enumerate(modes):
            incoming=(name,ports[k])
            if tails[m] is None: inputs[m]=incoming
            else: links.append((tails[m],incoming))
            tails[m]=(name,ports[k+n])
    from mzi import mzi
    for i,((m,_,_), (theta,phi)) in enumerate(zip(ops,settings)):
        if ideal:
            append("m"+str(i),EXT,reciprocal_transmission(mzi(theta,phi)),(m,m+1))
        else:
            # Differential core plus independently controlled input phase.
            # Matched zero-voltage reference on other arm.
            append("p"+str(i),("o1","o2"),eo(phi,wl),(m,))
            append("d"+str(i),("o1","o2"),eo0,(m+1,))
            append("m"+str(i),EXT,physical_core(theta,wl),(m,m+1))
    for i,v in enumerate(output):
        s=reciprocal_transmission([[np.exp(1j*v)]]) if ideal else eo(v,wl)
        append("out"+str(i),("o1","o2"),s,(i,))
    return assemble(blocks,links,inputs+tails)

def cascade(ops, settings, output):
    # Fast reflectionless approximation used ONLY to find initial settings;
    # all reported final metrics use the full reflected network.
    t=np.eye(4,dtype=complex)
    for (m,_,_),(v,p) in zip(ops,settings):
        block=physical_core(v)[2:,:2]@np.diag([eo(p)[1,0],EO0[1,0]])
        full=np.eye(4,dtype=complex);full[m:m+2,m:m+2]=block
        t=full@t
    return np.diag([eo(v)[1,0] for v in output])@t

def shape(t,u):
    # One common complex normalization, reported separately from optical loss.
    g=np.vdot(t,u)/np.vdot(t,t)
    return float(np.linalg.norm(g*t-u)/np.linalg.norm(u)),complex(g)

def main():
    checkout=Path(os.environ["LXT_PDK_DIR"]).resolve()
    assert Path(lnoi400.__file__).resolve().is_relative_to(checkout)
    assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==COMMIT
    assert not subprocess.check_output(["git","-C",str(checkout),"status","--porcelain","--untracked-files=no"],text=True).strip()
    data=checkout/"lnoi400/data/mmi_2x2_optimized_1550.json"
    assert hashlib.sha256(data.read_bytes()).hexdigest()=="f9016f890543146e1438836da2adb84fc2b14c9a8500311f34bcc640747acb36"
    ref=json.loads((ROOT/"results/opa-mzi-003/result.json").read_text())
    assert not ref["failures"] and next(r for r in ref["A_decomposition"] if r["n"]==4)["mzi_count"]==[6]
    rng=np.random.default_rng(SEED)
    targets=[("identity",np.eye(4)),("reverse",np.fliplr(np.eye(4))),("fourier",np.exp(2j*np.pi*np.outer(np.arange(4),np.arange(4))/4)/2)]
    targets += [(f"haar_{i}",haar_unitary(4,rng)) for i in range(5)]
    rows=[]; ideal_max=0.; passivity=0.; reciprocity=0.
    # Cache exact physical core/EO calls only within each objective evaluation.
    # Fixed voltage range covers two full nominal EO phase periods for
    # single-arm controls. Negative voltages are permitted in model only.
    for name,u in targets:
        ops,phases=clements_decompose(u)
        assert len(ops)==6 and max(mesh_columns(ops,4))==3
        ideal=topology(ops,[(t,p) for _,t,p in ops],phases,True)
        ideal_max=max(ideal_max,error(ideal[4:,:4],u),error(ideal[4:,:4],mesh_matrix(ops,phases)))
        initial=np.ravel([(t*VPI/np.pi,p*2*VPI/np.pi) for _,t,p in ops]).tolist()+list(phases*2*VPI/np.pi)
        initial=np.clip(initial,-26.4,26.4)
        def evaluate(x,full=False):
            pairs=np.asarray(x[:12]).reshape(6,2)
            return topology(ops,pairs,x[12:])[4:,:4] if full else cascade(ops,pairs,x[12:])
        def residual(x,full=False):
            t=evaluate(x,full)
            g=np.vdot(t,u)/np.vdot(t,t)
            d=(g*t-u).ravel()
            return np.r_[d.real,d.imag]
        naive=topology(ops,np.asarray(initial[:12]).reshape(6,2),initial[12:])
        # Deterministic bounded calibration; no target fitting on held-out inputs.
        fit=least_squares(residual,initial,bounds=(-26.4,26.4),max_nfev=40)
        candidate=fit.x
        s=topology(ops,candidate[:12].reshape(6,2),candidate[12:])
        if shape(s[4:,:4],u)[0]>shape(naive[4:,:4],u)[0]:
            candidate=np.array(initial);s=naive
        t=s[4:,:4]
        err,g=shape(t,u)
        passivity=max(passivity,max(0.,float(np.linalg.svd(s,compute_uv=False)[0]-1)))
        reciprocity=max(reciprocity,error(s,s.T))
        # Independent unseen complex field vectors; verify calibrated map.
        xs=rng.normal(size=(16,4))+1j*rng.normal(size=(16,4))
        mvm=float(np.linalg.norm(xs@((g*t-u).T))/np.linalg.norm(xs@u.T))
        row=dict(target=name,naive_shape_error=shape(naive[4:,:4],u)[0],calibrated_shape_error=err,
                 heldout_mvm_error=mvm,common_gain_abs=abs(g),common_gain_phase_rad=float(np.angle(g)),
                 mean_transmission=float(np.linalg.norm(t)**2/4),mean_reflection=float(np.linalg.norm(s[:4,:4])**2/4),
                 min_transmission=float(min(np.sum(abs(t)**2,axis=0))),sigma_max=float(np.linalg.svd(s,compute_uv=False)[0]),
                 optimizer_evaluations=fit.nfev,settings_v=candidate.tolist(),
                 target_matrix=[[[float(z.real),float(z.imag)] for z in r] for r in u],
                 scattering_matrix=[[[float(z.real),float(z.imag)] for z in r] for r in s])
        rows.append(row)
    checks={"ideal_mesh_exact":ideal_max<=1e-12,"full_mesh_reciprocal":reciprocity<=TOL,
            "complete_targets":len(rows)==8,"calibration_never_worse":all(r["calibrated_shape_error"]<=r["naive_shape_error"]+1e-12 for r in rows),
            "finite_transmission":all(0<r["mean_transmission"]<=1+TOL for r in rows)}
    failures=[k for k,v in checks.items() if not v]
    report=dict(experiment="OPA-CIR-004",pdk_commit=COMMIT,seed=SEED,wavelength_um=WL,
                mzi_count=6,columns=4,phase_controls=16,targets=len(rows),checks=checks,failures=failures,
                ideal_max_error=ideal_max,reciprocity_error=reciprocity,passivity_excess=passivity,
                passivity_eligible=not failures and passivity<=TOL,
                median_naive_shape_error=float(np.median([r["naive_shape_error"] for r in rows])),
                median_calibrated_shape_error=float(np.median([r["calibrated_shape_error"] for r in rows])),
                median_transmission=float(np.median([r["mean_transmission"] for r in rows])),
                cases=rows,limitations=["Model-level mesh, not geometry-extracted layout; omitted bends, tapers, bypass propagation and facet interfaces.",
                "Single wavelength, known deterministic models; no fabrication spread, RF, driver, noise or drift.",
                "Voltage bounds are numerical study bounds, not rated hardware voltages.",
                "Calibration uses reflectionless initialization and full reflected acceptance; no guaranteed universal accuracy.",
                "Complex common gain requires coherent reference/calibration; not optical amplification.",
                "No physical speed, energy or fabrication qualification."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},indent=2,allow_nan=False))
    if failures: raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
