"""OPA-CIR-006: frozen CIR005 SVD voltage settings across equal-frequency channels."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile
import numpy as np
from audit_lnoi400_cir005 import ROOT, COMMIT, WL, TOL, topology, join, clements_decompose, encode, error, lnoi400

OUT=ROOT/"results/opa-cir-006"
ZIP_SHA="0cd9d5eacdf5be4fcf4481809a5a96e1391aef40a9d0862d0d450dddb06f8dff"
C=299792458.
F0=C/(WL*1e-6)
SPACINGS=(25,50,100)
OFFSETS=tuple(range(-8,9))
# Predeclared engineering screen, not ENOB or AI accuracy.
ERROR_LIMIT=.05

def decode(a):
    a=np.asarray(a,dtype=float)
    return a[...,0]+1j*a[...,1]

def frozen_mesh(target, settings, wl):
    ops,_=clements_decompose(target)
    x=np.asarray(settings,dtype=float)
    assert x.shape==(16,) and np.isfinite(x).all() and np.max(abs(x))<=26.4+TOL
    return topology(ops,x[:12].reshape(6,2),x[12:],wl=wl)

def main():
    checkout=Path(os.environ["LXT_PDK_DIR"]).resolve()
    assert Path(lnoi400.__file__).resolve().is_relative_to(checkout)
    assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==COMMIT
    assert not subprocess.check_output(["git","-C",str(checkout),"status","--porcelain","--untracked-files=no"],text=True).strip()
    assert hashlib.sha256((checkout/"lnoi400/data/mmi_2x2_optimized_1550.json").read_bytes()).hexdigest()=="f9016f890543146e1438836da2adb84fc2b14c9a8500311f34bcc640747acb36"
    raw=Path(os.environ["CIR005_ZIP"]).read_bytes()
    assert len(raw)==31925 and hashlib.sha256(raw).hexdigest()==ZIP_SHA
    with zipfile.ZipFile(Path(os.environ["CIR005_ZIP"])) as z:
        assert sorted(z.namelist())==["environment-lock.txt","installed-packages.json","result.json"]
        assert z.testzip() is None
        ref=json.loads(z.read("result.json"))
    assert ref["experiment"]=="OPA-CIR-005" and ref["pdk_commit"]==COMMIT and ref["passivity_eligible"] and not ref["failures"]
    cases=[r for r in ref["cases"] if r["scale"]>0]
    assert [r["target"] for r in cases]==["identity","rank_one","signed_diagonal","dense_real","dense_complex"]
    rows=[]; central_error=0.; reciprocity=0.; passivity=0.
    for case in cases:
        w=decode(case["weight"])
        u,s,vh=np.linalg.svd(w)
        scale=case["scale"]; amps=np.asarray(case["attenuator_amplitudes"])
        assert np.allclose(s/scale,amps,rtol=0,atol=TOL)
        x=decode(case["heldout_inputs"])
        assert x.shape==(32,4)
        gain0=complex(decode(case["calibrated"]["common_complex_gain"]))
        frozen_v=case["input_mesh"]["settings_v"]; frozen_u=case["output_mesh"]["settings_v"]
        cache={}
        for spacing in SPACINGS:
            for offset in OFFSETS:
                delta=spacing*offset
                if delta not in cache:
                    f=F0+delta*1e9
                    wl=C/f*1e6 if delta else WL
                    assert 1.54<=wl<=1.56
                    left=frozen_mesh(vh,frozen_v,wl)
                    right=frozen_mesh(u,frozen_u,wl)
                    full=join(left,right,amps)
                    t=full[4:,:4]; a=scale*t
                    g=np.vdot(a,w)/np.vdot(a,a)
                    if delta==0:
                        central_error=max(central_error,error(full,decode(case["full_scattering"])))
                    err=lambda b:float(np.linalg.norm(b-w)/np.linalg.norm(w))
                    mvm=lambda b:float(np.linalg.norm(x@(b-w).T)/np.linalg.norm(x@w.T))
                    sigma=float(np.linalg.svd(full,compute_uv=False)[0])
                    rec=error(full,full.T)
                    reciprocity=max(reciprocity,rec);passivity=max(passivity,max(0.,sigma-1))
                    cache[delta]=dict(wavelength_um=wl,frequency_thz=f/1e12,
                        fixed_gain_matrix_error=err(gain0*a),channel_gain_matrix_error=err(g*a),
                        fixed_gain_mvm_error=mvm(gain0*a),channel_gain_mvm_error=mvm(g*a),
                        channel_gain=encode(np.asarray(g)),mean_transmission=float(np.linalg.norm(t)**2/4),
                        mean_reflection=float(np.linalg.norm(full[:4,:4])**2/4),sigma_max=sigma,
                        reciprocity_error=rec,scattering=encode(full))
                rows.append(dict(target=case["target"],spacing_ghz=spacing,offset=offset,**cache[delta]))
    summaries=[]
    for spacing in SPACINGS:
        group=[r for r in rows if r["spacing_ghz"]==spacing]
        for radius in (0,1,2,4,8):
            window=[r for r in group if abs(r["offset"])<=radius]
            fixed=max(r["fixed_gain_matrix_error"] for r in window)
            per=max(r["channel_gain_matrix_error"] for r in window)
            summaries.append(dict(spacing_ghz=spacing,channels=2*radius+1,
                worst_fixed_gain_error=fixed,worst_channel_gain_error=per,
                fixed_gain_screen_passed=fixed<=ERROR_LIMIT,
                channel_gain_screen_passed=per<=ERROR_LIMIT,
                min_mean_transmission=min(r["mean_transmission"] for r in window)))
    checks={"central_reproduces_frozen_scattering":central_error<=TOL,
            "complete_grid":len(rows)==255 and len(summaries)==15,
            "reciprocity":reciprocity<=TOL,
            "finite_metrics":all(np.isfinite(r[k]) for r in rows for k in ("fixed_gain_matrix_error","channel_gain_matrix_error","fixed_gain_mvm_error","channel_gain_mvm_error","mean_transmission","sigma_max")),
            "gain_fit_never_worse":all(r["channel_gain_matrix_error"]<=r["fixed_gain_matrix_error"]+TOL for r in rows)}
    failures=[k for k,v in checks.items() if not v]
    report=dict(experiment="OPA-CIR-006",pdk_commit=COMMIT,source_run=44516404174,source_artifact=14524868669,source_zip_sha256=ZIP_SHA,
                carrier_model="independent ideal frequency lines; no comb generation or mux hardware",
                spacings_ghz=list(SPACINGS),offsets=list(OFFSETS),targets=len(cases),cases=len(rows),
                center_error=central_error,reciprocity_error=reciprocity,passivity_excess=passivity,
                passivity_eligible=not failures and passivity<=TOL,engineering_error_screen=ERROR_LIMIT,
                checks=checks,failures=failures,windows=summaries,rows=rows,
                limitations=["Frozen CIR005 voltages and ideal attenuators, no per-channel weight reprogramming.",
                "Per-channel complex gain is a diagnostic requiring coherent calibration, not optical gain.",
                "No comb efficiency, line noise, mux/demux crosstalk, beating or modulation sidebands; linear independent-frequency approximation.",
                "No geometry-extracted routing, measured parameters, ENOB, throughput or energy claim."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    # Include the exact predecessor ZIP in the new artifact for reproducibility.
    (OUT/"cir005-source.zip").write_bytes(raw)
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},indent=2,allow_nan=False))
    if failures: raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
