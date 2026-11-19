"""OPA-CIR-002: audit pinned lnoi400 MMI complex model and compare network solvers."""
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from functools import partial

import jax
jax.config.update("jax_enable_x64", True)
import numpy as np
import sax
import lnoi400
from lnoi400 import models

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"simulations/circuit"))
from scattering_network import assemble

COMMIT="d16db6a4882657feb1ce696c16c604ff6cb7ccfa"
PORTS=("o1","o2","o3","o4")
WL=np.linspace(1.54,1.56,21)
TOL=1e-10
OUT=ROOT/"results/opa-cir-002"

def dense(sd,ports):
    allowed=set(ports)
    if any(a not in allowed or b not in allowed for a,b in sd):
        raise ValueError("unexpected port")
    # SAX sparse dictionary: absent entries are zero; no inferred phase.
    s=np.zeros((len(ports),len(ports)),complex)
    for (a,b),value in sd.items():
        v=np.asarray(value)
        if v.ndim!=0 or not np.isfinite(v):
            raise ValueError("expected finite scalar S parameter")
        s[ports.index(a),ports.index(b)]=complex(v)
    return s

def polynomial_reference(data,wl):
    def value(stem):
        x=wl-data["center_wavelength"]
        return np.polyval(data[stem+"_abs"],x)*np.exp(1j*np.polyval(data[stem+"_phase"],x))
    bar,cross,rs,rc=[value("pol_"+k) for k in ("trans_bar","trans_cross","refl_bar","refl_cross")]
    return np.array([[rs,rc,cross,bar],[rc,rs,bar,cross],[cross,bar,rs,rc],[bar,cross,rc,rs]])

def error(a,b):
    return float(np.max(np.abs(a-b)))

def main():
    checkout=Path(os.environ["LXT_PDK_DIR"]).resolve()
    assert Path(lnoi400.__file__).resolve().is_relative_to(checkout)
    assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==COMMIT
    assert not subprocess.check_output(["git","-C",str(checkout),"status","--porcelain","--untracked-files=no"],text=True).strip()
    data_path=checkout/"lnoi400/data/mmi_2x2_optimized_1550.json"
    data=json.loads(data_path.read_text())
    assert "FDTD" in data["doc"] and data["center_wavelength"]==1.55
    assert "MIT License" in (checkout/"LICENSE").read_text()
    metrics={"polynomial_error":0.,"reciprocity_error":0.,"sax_network_error":0.,"passivity_excess":0.,"network_passivity_excess":0.}
    rows=[]
    # Connect identical MMI models through two actual PDK straight models.
    # Named port convention: bar o1-o4 and o2-o3, cross o1-o3/o2-o4.
    # Arm lengths are illustrative, not an extracted layout.
    connections={"left,o4":"top,o1","left,o3":"bottom,o1","top,o2":"right,o1","bottom,o2":"right,o2"}
    boundary={"o1":"left,o1","o2":"left,o2","o3":"right,o3","o4":"right,o4"}
    links=[(tuple(k.split(",")),tuple(v.split(","))) for k,v in connections.items()]
    ext=[tuple(boundary[k].split(",")) for k in PORTS]
    def record(name,val):
        metrics[name]=max(metrics[name],float(val))
    for wl in WL:
        wl=float(wl)
        mmi_sd=models.mmi2x2_optimized1550(wl=wl)
        assert set(mmi_sd)=={(a,b) for a in PORTS for b in PORTS}
        s=dense(mmi_sd,PORTS)
        record("polynomial_error",error(s,polynomial_reference(data,wl)))
        record("reciprocity_error",error(s,s.T))
        record("passivity_excess",max(0.,np.linalg.svd(s,compute_uv=False)[0]-1))
        for length in (100.,100.25,110.):
            top=models.straight_rwg1000(wl=wl,length=length)
            bottom=models.straight_rwg1000(wl=wl,length=100.)
            blocks={"left":(PORTS,s),"right":(PORTS,s),"top":(("o1","o2"),dense(top,("o1","o2"))),"bottom":(("o1","o2"),dense(bottom,("o1","o2")))}
            result=assemble(blocks,links,ext)
            circuit,_=sax.circuit(netlist={"instances":{"left":"mmi","right":"mmi","top":"top","bottom":"bottom"},"connections":connections,"ports":boundary},
                                  models={"mmi":partial(models.mmi2x2_optimized1550,wl=wl),"top":partial(models.straight_rwg1000,wl=wl,length=length),"bottom":partial(models.straight_rwg1000,wl=wl,length=100.)},backend="default")
            expected=dense(circuit(),PORTS)
            record("sax_network_error",error(result,expected))
            record("network_passivity_excess",max(0.,np.linalg.svd(result,compute_uv=False)[0]-1))
            rows.append(dict(wavelength_um=wl,top_length_um=length,bar_power=float(abs(s[3,0])**2),cross_power=float(abs(s[2,0])**2),reflection_power=float(sum(abs(s[:2,0])**2)),mmi_sigma_max=float(np.linalg.svd(s,compute_uv=False)[0]),network_sigma_max=float(np.linalg.svd(result,compute_uv=False)[0]),network_error=error(result,expected),output_o3_power=float(abs(result[2,0])**2),output_o4_power=float(abs(result[3,0])**2)))
    # Numerical agreement is a hard gate. Non-passive fits are reported, not
    # silently clipped or mistaken for physical gain; block model promotion.
    checks={k:bool(np.isfinite(metrics[k]) and metrics[k]<=TOL) for k in ("polynomial_error","reciprocity_error","sax_network_error")}
    checks["complete_grid"]=len(rows)==63
    checks["phase_sensitive"]=bool(abs(np.imag(dense(models.mmi2x2_optimized1550(wl=1.55),PORTS)[3,0]))>1e-3)
    failures=[k for k,v in checks.items() if not v]
    eligible=not failures and metrics["passivity_excess"]<=TOL and metrics["network_passivity_excess"]<=TOL
    report=dict(experiment="OPA-CIR-002",pdk_commit=COMMIT,source_data_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(),source_license_sha256=hashlib.sha256((checkout/"LICENSE").read_bytes()).hexdigest(),versions={k:importlib.metadata.version(k) for k in ("sax","jax","numpy","lxt_pdk_gf")},source_type="upstream FDTD polynomial compact model",port_order=list(PORTS),wavelength_um=[1.54,1.56],samples=len(rows),tolerance=TOL,checks=checks,metrics=metrics,failures=failures,passivity_eligible=eligible,limitations=["Narrow exploratory grid, not certified upstream validity range.","No calibrated measurement, process corners, temperature, polarization or reference-plane de-embedding audit.","Assumes compatible fundamental optical modes and native model port reference planes; no geometry-extracted MZI.","SAX agreement verifies numerical connection, not physical model accuracy.","No external model files copied into repository."])
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"sweep.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))
    if failures:
        raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
