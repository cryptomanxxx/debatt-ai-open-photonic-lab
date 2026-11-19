"""OPA-CIR-007: sampled coherent I/Q interface on frozen single-carrier SVD."""
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/opa-cir-007"
SHA="0f35693c16434e42d16038aac5bd33fb8d832ba1c9d69b5d85d998a28bae8b05"
PREV="0cd9d5eacdf5be4fcf4481809a5a96e1391aef40a9d0862d0d450dddb06f8dff"
SEED=20261121
R=.9
Q=1.602176634e-19
TIA=15e-12
B=7e9
# Ideal 90-degree hybrid divides both signal and LO between I and Q.
# LO power is TOTAL per output hybrid, not per photodiode.
# Difference current per quadrature = R sqrt(Plo) Re/Im(E).
# Sum of the two diode currents per quadrature = R(Ps+Plo)/2.
def decode(x):
    a=np.asarray(x,dtype=float)
    return a[...,0]+1j*a[...,1]

def quant(x,bits,limit):
    levels=2**(bits-1)-1
    return np.round(np.clip(x/limit,-1,1)*levels)*limit/levels

def qcomplex(x,bits,limit):
    return quant(x.real,bits,limit)+1j*quant(x.imag,bits,limit)

def currents(e,lo):
    # explicit four detector powers, ideal lossless hybrid
    l=np.sqrt(lo)
    powers=np.stack([abs(e+l)**2,abs(e-l)**2,abs(e+1j*l)**2,abs(e-1j*l)**2],axis=-1)/4
    d=R*((powers[...,0]-powers[...,1])+1j*(powers[...,2]-powers[...,3]))
    return d,powers

def rel(a,b):
    return float(np.linalg.norm(a-b)/np.linalg.norm(b))

def main():
    raw=Path(os.environ["CIR006_ZIP"]).read_bytes()
    assert len(raw)==352602 and hashlib.sha256(raw).hexdigest()==SHA
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        assert sorted(z.namelist())==["cir005-source.zip","environment-lock.txt","installed-packages.json","result.json"]
        six=json.loads(z.read("result.json"))
        prev=z.read("cir005-source.zip")
    assert hashlib.sha256(prev).hexdigest()==PREV
    with zipfile.ZipFile(io.BytesIO(prev)) as z:
        assert z.testzip() is None
        five=json.loads(z.read("result.json"))
    assert six["experiment"]=="OPA-CIR-006" and six["passivity_eligible"] and not six["failures"]
    assert five["experiment"]=="OPA-CIR-005" and five["passivity_eligible"] and not five["failures"]
    assert all(r["fixed_gain_screen_passed"]==(r["channels"]==1) for r in six["windows"])
    assert all(r["channel_gain_screen_passed"]==(r["channels"]==1) for r in six["windows"])
    rows=[]; checks={}; controls=[]; energy_excess=0.; hybrid_error=0.; center_error=0.
    cases=[c for c in five["cases"] if c["scale"]>0]
    for idx,c in enumerate(cases):
        w=decode(c["weight"]); s=decode(c["full_scattering"]); t=s[4:,:4]
        central=[r for r in six["rows"] if r["target"]==c["target"] and r["offset"]==0]
        assert len(central)==3
        center_error=max(center_error,max(float(np.max(abs(decode(r["scattering"])-s))) for r in central))
        gain=complex(decode(c["calibrated"]["common_complex_gain"]))
        scale=c["scale"]
        x0=decode(c["heldout_inputs"])
        # Per-vector known digital normalization prevents arbitrary launch power;
        # undo after detection. Not a new fit to test data.
        norms=np.linalg.norm(x0,axis=1,keepdims=True)
        x=x0/norms
        target=x0@w.T
        ideal_core=(x@t.T)*gain*scale*norms
        controls.append(abs(rel(ideal_core,target)-c["calibrated"]["heldout_mvm_error"]))
        # Same random variates across all interface configurations per target.
        rng=np.random.default_rng(np.random.SeedSequence([SEED,idx]))
        noise=rng.normal(size=(64,len(x),4,2))
        for bits,launch_mw,lo_mw in itertools.product((4,6,8,10),(.01,.1,1.),(.1,1.,3.)):
            launch=launch_mw*1e-3; lo=lo_mw*1e-3
            # Ideal linear field encoder with two signed quadrature DACs.
            # Full-scale 1 per quadrature, normalized vector amplitude <=1.
            xq=qcomplex(x,bits,1.)
            # Reserve a deterministic sqrt(2) headroom for all quantized
            # input vectors: fixed bound ||xq|| <= sqrt(2) for these grids.
            # Instead explicitly normalize by max(1, norm) and undo that
            # known digital factor; launch denotes maximum total power.
            head=np.maximum(1.,np.linalg.norm(xq,axis=1,keepdims=True))
            drive=xq/head
            e=np.sqrt(launch)*(drive@t.T)
            reflected=np.sqrt(launch)*(drive@s[:4,:4].T)
            energy_excess=max(energy_excess,float(np.max(np.sum(abs(e)**2+abs(reflected)**2,axis=1)-launch*np.sum(abs(drive)**2,axis=1))))
            d,p=currents(e,lo)
            expected=R*np.sqrt(lo)*e
            hybrid_error=max(hybrid_error,float(np.max(abs(d-expected))),float(np.max(abs(p.sum(-1)-(abs(e)**2+lo)))))
            # Difference shot-noise variances add; independent I/Q
            # TIA noise densities are conditional effective pair values.
            variance=Q*R*(abs(e)**2+lo)*B+TIA**2*B
            noisy=d[None,:,:]+np.sqrt(variance)[None,:,:]*(noise[...,0]+1j*noise[...,1])
            # Fixed ADC current full scale derived before data/noise from
            # passive input power bound, with 20% margin.
            fs=1.2*R*np.sqrt(lo*launch)
            adc=qcomplex(noisy,bits,fs)
            clip=(abs(noisy.real)>fs)|(abs(noisy.imag)>fs)
            factor=gain*scale*norms*head/(R*np.sqrt(lo*launch))
            dac_only=d*factor
            noiseless_adc=qcomplex(d,bits,fs)*factor
            recovered=adc*factor[None,:,:]
            ref=np.broadcast_to(target,recovered.shape)
            rows.append(dict(target=c["target"],bits=bits,launch_max_mw=launch_mw,lo_per_output_mw=lo_mw,
                lo_total_mw=4*lo_mw,core_only_error=rel(ideal_core,target),
                dac_only_error=rel(dac_only,target),noiseless_adc_error=rel(noiseless_adc,target),
                total_relative_error=rel(recovered,ref),adc_clip_fraction=float(clip.mean()),
                mean_launch_mw=float(np.mean(np.sum(abs(drive)**2,axis=1))*launch*1e3),
                mean_detected_signal_mw=float(np.mean(np.sum(abs(e)**2,axis=1))*1e3),
                max_diode_mw=float(p.max()*1e3),adc_fullscale_a=fs))
    checks=dict(central_exact=center_error<=1e-12,core_reproduced=max(controls)<=1e-12,
                hybrid_identity=hybrid_error<=1e-12,passive_power=energy_excess<=1e-12,
                complete_grid=len(rows)==180,
                finite=all(all(np.isfinite(v) for v in r.values() if isinstance(v,(float,int))) for r in rows),
                lo_accounting=all(r["lo_total_mw"]==4*r["lo_per_output_mw"] for r in rows))
    summaries=[]
    for bits,launch,lo in itertools.product((4,6,8,10),(.01,.1,1.),(.1,1.,3.)):
        g=[r for r in rows if (r["bits"],r["launch_max_mw"],r["lo_per_output_mw"])==(bits,launch,lo)]
        worst=max(r["total_relative_error"] for r in g)
        summaries.append(dict(bits=bits,launch_max_mw=launch,lo_per_output_mw=lo,
            worst_error=worst,median_error=float(np.median([r["total_relative_error"] for r in g])),
            worst_clip_fraction=max(r["adc_clip_fraction"] for r in g),
            max_diode_mw=max(r["max_diode_mw"] for r in g),
            provisional_screen_passed=worst<=.05 and all(r["adc_clip_fraction"]==0 for r in g)))
    failures=[k for k,v in checks.items() if not v]
    report=dict(experiment="OPA-CIR-007",source_run=44517897095,source_artifact=14527555003,source_sha256=SHA,
        carrier_nm=1550,channels=1,seed=SEED,checks=checks,failures=failures,rows=len(rows),
        repeats=64,vectors_per_target=32,parameters=dict(responsivity_a_w=R,noise_bandwidth_hz=B,tia_pair_a_rt_hz=TIA,
        electron_charge_c=Q),hybrid_identity_error=hybrid_error,center_error=center_error,
        core_reproduction_error=max(controls),power_excess_w=energy_excess,
        passing_configurations=sum(r["provisional_screen_passed"] for r in summaries),
        summaries=summaries,cases=rows,limitations=["Ideal linear I/Q encoder, not a calibrated EO modulator or DAC driver.",
        "Ideal 90-degree hybrid, external phase-locked LO, balanced Gaussian shot/TIA noise; no RIN, imbalance, phase drift, saturation or bandwidth dynamics.",
        "ADC and DAC same nominal bits, static quantization, no ENOB or sample-rate claim.",
        "No WDM, no amplifier, no physical laser/LO distribution or power consumption model.",
        "Known digital input scale and frozen complex gain assumed; no receiver fit on inference data.",
        "Ideal singular-value attenuators and incomplete layout retained; 5% provisional error screen not AI accuracy."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},indent=2,allow_nan=False))
    if failures: raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
