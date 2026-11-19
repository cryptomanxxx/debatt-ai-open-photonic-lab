"""LIB003: preserve and sample native simulated complex coefficients, never repair nonpassive fits."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import jax
jax.config.update("jax_enable_x64", True)
import numpy as np
import lnoi400
from lnoi400 import models

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/external/Luxtelligence/lnoi400/s_parameters"
GEOM=BASE.parent/"archive"
OUT=ROOT/"results/opa-lib-003"
REV="d16db6a4882657feb1ce696c16c604ff6cb7ccfa"
PORTS=("o1","o2","o3","o4")
TOL=1e-10
GRID=np.linspace(1.54,1.56,201)
MID=(GRID[:-1]+GRID[1:])/2
STEMS=("trans_bar","trans_cross","refl_bar","refl_cross")
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def dense(sd):
    require(set(sd)=={(a,b) for a in PORTS for b in PORTS},"complete four-port SDict")
    s=np.array([[complex(sd[a,b]) for b in PORTS] for a in PORTS])
    require(np.isfinite(s).all(),"finite native matrix")
    return s
def polynomial(data,wl):
    x=wl-data["center_wavelength"]
    def val(k):
        a=np.polyval(data["pol_"+k+"_abs"],x)
        p=np.polyval(data["pol_"+k+"_phase"],x)
        return a*np.exp(1j*p)
    b,c,r,s=map(val,STEMS)
    return np.array([[r,s,c,b],[s,r,b,c],[c,b,r,s],[b,c,s,r]])
def metrics(s):
    sigma=float(np.linalg.svd(s,compute_uv=False)[0])
    power=np.sum(abs(s)**2,axis=0)
    return dict(sigma_max=sigma,reciprocity_error=float(np.max(abs(s-s.T))),
                max_input_power=float(max(power)),bar_power=float(abs(s[3,0])**2),
                cross_power=float(abs(s[2,0])**2),reflection_power=float(sum(abs(s[:2,0])**2)))
def main():
    m=json.loads((BASE/"manifest.json").read_text())
    src=Path(os.environ["LXT_PDK_DIR"]).resolve()
    require(subprocess.check_output(["git","-C",str(src),"rev-parse","HEAD"],text=True).strip()==REV==m["revision"],"source revision")
    require(not subprocess.check_output(["git","-C",str(src),"status","--porcelain","--untracked-files=no"],text=True).strip(),"dirty source")
    require(Path(lnoi400.__file__).resolve()==src/"lnoi400/__init__.py","source module")
    require(blob(src/"lnoi400/models.py")==m["source_model_git_blob_sha1"] and blob(src/"_utils/models.py")==m["source_evaluator_git_blob_sha1"],"model source identity")
    require((src/"LICENSE").read_bytes()==(BASE.parent/"LICENSE").read_bytes() and blob(src/"LICENSE")==m["license_git_blob_sha1"],"license identity")
    require(m["port_order"]==list(PORTS) and m["wavelength_grid_nm"]==dict(start=1540,stop=1560,step=.1,count=201),"grid and ports")
    require(len(m["components"])==2 and {e["id"] for e in m["components"]}=={"mmi-2x2","directional-coupler"},"component selection")
    OUT.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for e in m["components"]:
        ident=e["id"]
        p=BASE/e["local_source"]
        require(p.read_bytes()==(src/e["source_path"]).read_bytes() and blob(p)==e["source_git_blob_sha1"],"exact original "+ident)
        data=json.loads(p.read_text())
        require(data["center_wavelength"]==1.55 and "simulation results" in data["doc"],"simulated source")
        gds=GEOM/"gds"/(ident+".gds")
        geom=json.loads((GEOM/"ports"/(ident+".json")).read_text())
        require(sha(gds)==e["gds_sha256"]==geom["gds_sha256"] and geom["source_revision"]==REV and geom["factory"]==e["model"] and geom["kwargs"]=={},"geometry link")
        require([p["name"] for p in geom["ports"]]==list(PORTS),"geometry port order")
        require(e["measurement"] is None and e["qualification"] is None,"evidence scope")
        # Original native polynomial, signed amplitudes preserved exactly.
        native=getattr(models,e["model"])
        matrices=[]; rows=[]; errs=[]; midpoint_err=[]
        for wl in GRID:
            s=dense(native(wl=float(wl)))
            expected=polynomial(data,float(wl))
            errs.append(float(np.max(abs(s-expected))))
            matrices.append(s)
            rows.append(dict(wavelength_nm=float(wl*1000),**metrics(s)))
        matrices=np.array(matrices)
        # Validate the proposed complex-linear interpolator, not phase unwrapping.
        # The published dataset is sampled; exact polynomial remains preferred.
        for i,wl in enumerate(MID):
            s=dense(native(wl=float(wl)))
            errs.append(float(np.max(abs(s-polynomial(data,float(wl))))))
            midpoint_err.append(float(np.max(abs(s-(matrices[i]+matrices[i+1])/2))))
        require(max(errs)<=TOL,"native polynomial mismatch "+ident)
        require(max(r["reciprocity_error"] for r in rows)<=TOL,"reciprocity "+ident)
        fail=sum(r["sigma_max"]>1+TOL for r in rows)
        peak=max(r["sigma_max"] for r in rows)
        eligible=fail==0
        # Do not promote even an eligible numerical fit to measured validity.
        expected_fail=0 if ident=="mmi-2x2" else 201
        require(fail==expected_fail,"frozen passivity finding changed "+ident)
        record=dict(component=ident,source_git_blob_sha1=e["source_git_blob_sha1"],source_sha256=sha(p),
                    gds_sha256=sha(gds),revision=REV,port_order=list(PORTS),matrix_convention=m["matrix_convention"],
                    complex_encoding=m["complex_encoding"],wavelength_nm=[r["wavelength_nm"] for r in rows],
                    scattering=np.stack((matrices.real,matrices.imag),axis=-1).tolist(),
                    normalization=m["normalization"],reference_planes=m["reference_planes"],phase=m["phase"],
                    validity=m["validity"],polarization=m["polarization"],bias_temperature=m["bias_temperature"],
                    geometry_scope=e["geometry_scope"],source_type=e["source_type"],measurement=None,qualification=None,
                    passivity_screen_eligible=eligible,usage="conditional_numerical_only" if eligible else "quarantined_nonpassive",
                    interpolation="native polynomial preferred; no extrapolation; linear complex midpoint error reported separately")
        fn=OUT/(ident+".s.json")
        fn.write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")
        with (OUT/(ident+".metrics.csv")).open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        summaries.append(dict(component=ident,samples=len(rows),midpoint_samples=len(MID),max_native_polynomial_error=max(errs),
            max_reciprocity_error=max(r["reciprocity_error"] for r in rows),max_sigma=peak,min_sigma=min(r["sigma_max"] for r in rows),
            nonpassive_samples=fail,passivity_screen_eligible=eligible,usage=record["usage"],center=rows[100],
            max_complex_linear_midpoint_error=max(midpoint_err),dataset_sha256=sha(fn),source_sha256=sha(p),gds_sha256=sha(gds)))
    report=dict(experiment="OPA-LIB-003",revision=REV,components=summaries,checks=dict(source_identity=True,geometry_link=True,full_complex_grid=True,native_polynomial_agreement=True,reciprocity=True,passivity_classification=True),
                limitations=["Original upstream coefficients are simulated polynomial fits, not raw measured data.",
                "Passivity assumes compatible power-normalized ports; no physical reference plane calibration.",
                "Directional coupler original fit is quarantined, not clipped, renormalized or interpreted as physical gain.",
                "Sampled passivity does not certify continuous-band passivity or device performance.",
                "No circuit substitution or WDM claim in LIB003; no cross-platform mixing."])
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__":
    main()
