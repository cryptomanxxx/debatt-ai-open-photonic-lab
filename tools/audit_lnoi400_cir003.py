"""OPA-CIR-003: four-port EO MZI core, using pinned upstream component models."""
import csv
import hashlib
import json
import os
from pathlib import Path
from functools import partial
import numpy as np
from audit_lnoi400_cir002 import (ROOT, COMMIT, PORTS, TOL, dense, error,
                                  assemble, models, sax, lnoi400)
import subprocess

OUT=ROOT/"results/opa-cir-003"
# Native splitter input o1/o2; branch top o3, bottom o4 in upstream layout.
# Combiner is reversed; external native o1/o2 become output o4/o3.
# This reproduces the topology, not the flattened route geometry.
EXT=("in1","in2","out1","out2")
CONNECTIONS={"left,o3":"eo_top,o1","left,o4":"eo_bottom,o1",
             "eo_top,o2":"ht_top,o1","eo_bottom,o2":"ht_bottom,o1",
             "ht_top,o2":"right,o3","ht_bottom,o2":"right,o4"}
BOUNDARY=dict(zip(EXT,("left,o1","left,o2","right,o1","right,o2")))
LINKS=[(tuple(a.split(",")),tuple(b.split(","))) for a,b in CONNECTIONS.items()]
EXTERNAL=[tuple(BOUNDARY[k].split(",")) for k in EXT]

def core(wl,v,ht,length,bias):
    funcs={"mmi":partial(models.mmi2x2_optimized1550,wl=wl),
           "et":partial(models.eo_phase_shifter,wl=wl,length=length,V_dc=v),
           "eb":partial(models.eo_phase_shifter,wl=wl,length=length,V_dc=-v),
           "ht":partial(models.to_phase_shifter,wl=wl,heater_length=bias,V_dc=ht),
           "hb":partial(models.to_phase_shifter,wl=wl,heater_length=bias,V_dc=0.)}
    instances={"left":"mmi","right":"mmi","eo_top":"et","eo_bottom":"eb",
               "ht_top":"ht","ht_bottom":"hb"}
    blocks={}
    for n,m in instances.items():
        ports=PORTS if m=="mmi" else ("o1","o2")
        blocks[n]=(ports,dense(funcs[m](),ports))
    s=assemble(blocks,LINKS,EXTERNAL)
    circuit,_=sax.circuit(netlist={"instances":instances,"connections":CONNECTIONS,"ports":BOUNDARY},models=funcs,backend="default")
    return s,dense(circuit(),EXT),max(np.linalg.svd(b[1],compute_uv=False)[0] for b in blocks.values())

def main():
    checkout=Path(os.environ["LXT_PDK_DIR"]).resolve()
    assert Path(lnoi400.__file__).resolve().is_relative_to(checkout)
    assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==COMMIT
    assert not subprocess.check_output(["git","-C",str(checkout),"status","--porcelain","--untracked-files=no"],text=True).strip()
    source=checkout/"lnoi400/data/mmi_2x2_optimized_1550.json"
    assert hashlib.sha256(source.read_bytes()).hexdigest()=="f9016f890543146e1438836da2adb84fc2b14c9a8500311f34bcc640747acb36"
    ref=json.loads((ROOT/"results/opa-layout-005/result.json").read_text())
    assert ref["experiment"]=="OPA-LAYOUT-005" and not ref["failures"]
    length=ref["modulator"]["modulation_length"]
    assert length==5000. and ref["modulator"]["length_imbalance"]==0.
    assert ref["modulator"]["splitter"]=="mmi2x2_optimized1550"
    assert ref["modulator"]["with_heater"] is True
    bias=700. # upstream mzm_unbalanced layout default
    vpi=ref["vpi"]["pdk_model_V"]
    assert vpi==6.6
    rows=[]
    maxima={"sax_error":0.,"reciprocity_error":0.,"component_passivity_excess":0.,"core_passivity_excess":0.}
    def record(k,x):
        maxima[k]=max(maxima[k],float(x))
    for wl in (1.54,1.545,1.55,1.555,1.56):
        for ht in (0.,1.):
            for v in np.linspace(0,2*vpi,33):
                s,expected,component_sigma=core(wl,float(v),ht,length,bias)
                sigma=np.linalg.svd(s,compute_uv=False)[0]
                record("sax_error",error(s,expected))
                record("reciprocity_error",error(s,s.T))
                record("component_passivity_excess",max(0.,component_sigma-1))
                record("core_passivity_excess",max(0.,sigma-1))
                row=dict(wavelength_um=wl,eo_voltage_v=float(v),heater_voltage_v=ht,
                         heater_power_w=ht**2/25.,sigma_max=float(sigma))
                for j in range(2):
                    p=abs(s[:,j])**2
                    row.update({f"in{j+1}_out1_power":float(p[2]),f"in{j+1}_out2_power":float(p[3]),
                                f"in{j+1}_reflection":float(sum(p[:2])),
                                f"in{j+1}_unaccounted_power":float(1-sum(p))})
                for i,a in enumerate(EXT):
                    for j,b in enumerate(EXT):
                        row[f"S_{a}_{b}_real"]=float(s[i,j].real)
                        row[f"S_{a}_{b}_imag"]=float(s[i,j].imag)
                rows.append(row)
    central=[r for r in rows if r["wavelength_um"]==1.55 and r["heater_voltage_v"]==0.]
    transfer=[r["in1_out1_power"] for r in central]
    contrast=max(transfer)-min(transfer)
    checks={k:bool(np.isfinite(v) and v<=TOL) for k,v in maxima.items() if "passivity" not in k}
    checks["complete_grid"]=len(rows)==330
    checks["eo_modulation_observed"]=bool(contrast>.5)
    checks["finite_rows"]=all(np.isfinite(list(r.values())).all() for r in rows)
    failures=[k for k,v in checks.items() if not v]
    eligible=not failures and all(v<=TOL for k,v in maxima.items() if "passivity" in k)
    report=dict(experiment="OPA-CIR-003",pdk_commit=COMMIT,source_mmi_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                layout_reference="OPA-LAYOUT-005",modulation_length_um=length,heater_length_um=bias,
                nominal_push_pull_vpi_v=vpi,port_order=list(EXT),cases=len(rows),checks=checks,failures=failures,
                metrics=maxima,passivity_eligible=eligible,central_in1_out1_power_range=[min(transfer),max(transfer)],
                central_contrast=contrast,limitations=["Topology-level core only; excludes layout bends, tapers, extra bias routing and facet edge couplers.",
                "5 mm EO length and 700 um thermal section match layout settings, not full optical reference-plane distances.",
                "No RF response, driver, noise, thermal crosstalk or measured model calibration.",
                "Heater power is conditional upstream 25 ohm resistance, not measured or wall-plug power.",
                "Only differential theta and bias tuning; no arbitrary 2x2 unitary claim.",
                "No physical throughput or fabrication qualification."])
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"sweep.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))
    if failures: raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
