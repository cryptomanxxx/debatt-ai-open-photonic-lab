"""OPA-SYS-003: controlled receiver and amplifier accounting audit."""
import csv
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys

ROOT = Path("antigravity/reproduction/AG-PHOTONIC-003")
OUT = Path("results/opa-sys-003")

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def snr(p_w, r, b, tia, rin, cmrr, ase_w, bopt, q):
    # Legacy signal-current convention; explicit rectangular noise bandwidth.
    i = r*p_w
    ia = r*ase_w
    ratio = b/bopt
    terms = dict(tia=(tia*1e-12)**2*b, shot=2*q*(i+ia)*b,
                 rin=i*i*10**((rin-cmrr)/10)*b,
                 signal_ase=4*i*ia*ratio, ase_ase=ia*ia*ratio)
    return i*i/sum(terms.values()), terms

def solve(target, r, b, tia, rin, cmrr, ase_w, bopt, q):
    # Independent monotonic bisection; no arbitrary 5% RIN margin.
    if target*10**((rin-cmrr)/10)*b >= 1:
        return None
    lo, hi = 0., 1e-12
    while snr(hi,r,b,tia,rin,cmrr,ase_w,bopt,q)[0] < target:
        hi *= 2
        if hi > 1e6:
            raise ValueError("unexpected numerical bracket")
    for _ in range(100):
        mid=(lo+hi)/2
        if snr(mid,r,b,tia,rin,cmrr,ase_w,bopt,q)[0] < target:
            lo=mid
        else:
            hi=mid
    return hi

def main():
    sys.dont_write_bytecode=True
    verifier=load("ag003_verify",ROOT/"import_snapshot.py")
    files=verifier.verify(ROOT/"original")
    p=load("params",ROOT/"original/params.py")
    model=load("ag003_stage1",ROOT/"corrected/physics_model.py")
    o=p.OPTICAL_PARAMS
    v=lambda k:o[k].val
    r,tia,rin,xtalk=(v(k) for k in ("pd_responsivity","tia_noise_pa_rt_hz","laser_rin_db_hz","xtalk_penalty_db"))
    q=p.Q_E
    rows=[]
    checks={}
    legacy_matches=[]
    root_matches=[]
    for bits,rate,cmrr,bopt_ghz,ase_uw in itertools.product(
            (4,6,8,12),(5.,10.,25.),(0.,10.,20.,30.),(25.,50.,100.),(0.,1.,10.)):
        b=.7*rate*1e9
        bopt=bopt_ghz*1e9
        target_db=6.02*(bits+.5)+1.76+xtalk
        target=10**(target_db/10)
        ase=ase_uw*1e-6
        power=solve(target,r,b,tia,rin,cmrr,ase,bopt,q)
        legacy,_=model.solve_min_rx_power_mw(bits,rate,r,tia,rin,xtalk,ase*1e3)
        # Legacy formula corresponds to ratio 0.2 (not fixed optical bandwidth).
        compat=solve(target,r,b,tia,rin,20.,ase,b/.2,q)
        margin=1-target*10**((rin-20)/10)*b
        if margin>.05:
            legacy_matches.append(legacy is not None and math.isclose(legacy,compat*1e3,rel_tol=1e-10))
        else:
            legacy_matches.append(legacy is None)
        if power is not None:
            actual,terms=snr(power,r,b,tia,rin,cmrr,ase,bopt,q)
            root_matches.append(math.isclose(actual,target,rel_tol=1e-9))
        else:
            terms={}
        rows.append(dict(bits=bits,rate_ghz=rate,cmrr_db=cmrr,optical_bandwidth_ghz=bopt_ghz,
            ase_uw=ase_uw,target_snr_db=target_db,required_rx_mw=None if power is None else power*1e3,
            legacy_rx_mw=legacy,rin_ceiling_db=-10*math.log10(10**((rin-cmrr)/10)*b),
            **{k+"_a2":terms.get(k) for k in ("tia","shot","rin","signal_ase","ase_ase")}))
    checks["legacy_compatibility"]=all(legacy_matches)
    checks["independent_snr_roots"]=all(root_matches)
    checks["row_count"]=len(rows)==432
    # Fixed receiver reference plane: compare per-laser and aggregate limits,
    # plus booster gain and saturation including in-band ASE. No system ranking.
    links=[]
    for arch,loss,n,branches,bits,gain in itertools.product(
            ("comb","independent"),(15.,20.,25.,30.),(8,16),(1,4),(4,6,8),(0.,10.,20.,25.)):
        if arch=="independent" and branches!=1:
            continue
        b=.7*10e9
        bopt=v("comb_channel_spacing_ghz")*1e9
        g=10**(gain/10)
        trans=10**(-loss/10)
        # Reference plane immediately before booster; downstream loss only.
        ase_out=10**(v("amp_nf_db")/10)*p.H_PLANCK*p.NU_0*(g-1)*bopt
        target=10**((6.02*(bits+.5)+1.76+xtalk)/10)
        rx=solve(target,r,b,tia,rin,20.,ase_out*trans,bopt,q)
        row=dict(architecture=arch,downstream_loss_db=loss,wavelengths=n,branches=branches,bits=bits,gain_db=gain,
                 ase_output_per_line_mw=ase_out*1e3,rx_signal_mw=None if rx is None else rx*1e3)
        if rx is not None:
            signal_out=rx/trans
            signal_in=signal_out/g
            # Comb conversion and equal branch loss upstream of booster.
            coupling=10**(v("coupler_il_db")/10)
            if arch=="comb":
                split=branches*10**(math.ceil(math.log2(branches))*v("splitter_excess_db")/10)
                launch=max(n*signal_in/v("comb_eff"),1.5*v("comb_threshold_mw")*1e-3)*split*coupling
                bank=launch
            else:
                launch=signal_in*coupling
                bank=n*launch
            total_out=n*(signal_out+ase_out)
            added_signal=n*(signal_out-signal_in)
            # Lower bound, not amplifier electrical prediction; ASE outside the
            # selected channels, idle power and threshold excess are unknown.
            amp_lower=(added_signal+n*ase_out)/v("amp_wpe") if gain else 0.
            row.update(source_unit_mw=launch*1e3,source_bank_mw=bank*1e3,
                source_electric_w=bank/v("laser_wpe"),amp_output_mw=total_out*1e3,
                amp_electric_lower_bound_w=amp_lower,
                per_source_pass=launch*1e3<=v("laser_max_power_mw"),
                aggregate_source_pass=bank*1e3<=v("laser_max_power_mw"),
                amp_pass=(gain==0 or total_out*1e3<=v("amp_psat_mw")))
        links.append(row)
    checks["link_count"]=len(links)==288
    checks["zero_gain_zero_ase"]=all(x["ase_output_per_line_mw"]==0 for x in links if x["gain_db"]==0)
    checks["source_unit_not_above_bank"]=all(x["source_unit_mw"]<=x["source_bank_mw"] for x in links if "source_unit_mw" in x)
    checks["amp_nonnegative"]=all(x["amp_electric_lower_bound_w"]>=0 for x in links if "amp_electric_lower_bound_w" in x)
    checks["original_immutable"]=verifier.verify(ROOT/"original")==files
    # Explicit balanced coherent receiver illustration, separate from legacy
    # current convention. Ideal 50:50 hybrid, total signal and LO at hybrid.
    # Difference current = 2R sqrt(Ps Plo), independent PD shot variances add.
    coherent=[]
    for bits,lo_mw in itertools.product((4,6,8,12),(.1,1.,10.)):
        b=7e9
        lo=lo_mw*1e-3
        target=10**((6.02*(bits+.5)+1.76+xtalk)/10)
        slope=4*r*r*lo-target*2*q*r*b
        ps=None if slope<=0 else target*(2*q*r*lo*b+(tia*1e-12)**2*b)/slope
        coherent.append(dict(bits=bits,lo_mw=lo_mw,signal_mw=None if ps is None else ps*1e3,
            lo_electric_lower_bound_w=lo/v("laser_wpe"),ideal_only=True))
    checks["coherent_root"]=all(math.isclose(4*r*r*(x["signal_mw"]*1e-3)*(x["lo_mw"]*1e-3)/(2*q*r*(x["signal_mw"]+x["lo_mw"])*1e-3*7e9+(tia*1e-12)**2*7e9),10**((6.02*(x["bits"]+.5)+1.76+xtalk)/10),rel_tol=1e-9) for x in coherent if x["signal_mw"] is not None)
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in (("receiver",rows),("link",links),("coherent",coherent)):
        fields=list(dict.fromkeys(k for row in data for k in row))
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
    nominal=[x for x in rows if x["rate_ghz"]==10 and x["cmrr_db"]==20 and x["optical_bandwidth_ghz"]==50]
    result=dict(experiment="OPA-SYS-003",checks=checks,failures=[k for k,v in checks.items() if not v],
        receiver_cases=len(rows),link_cases=len(links),coherent_cases=len(coherent),
        nominal_receiver=nominal,ideal_coherent=coherent,
        link_summary=[dict(architecture=a,bits=b,feasible=sum(
            bool(x.get("per_source_pass") and x.get("amp_pass")) for x in links if x["architecture"]==a and x["bits"]==b),
            tested=sum(x["architecture"]==a and x["bits"]==b for x in links)) for a,b in itertools.product(("comb","independent"),(4,6,8))],
        limitations=["Rectangular bandwidth and legacy current convention are conditional assumptions, not a calibrated detector model.",
            "ASE uses retained approximate noise figure formula, explicit in-band power only.",
            "Ideal coherent control excludes RIN, imbalance, ASE, saturation, distribution and phase tracking; LO energy lower bound only.",
            "Fixed downstream loss scenarios are not full configurations; no throughput, architecture ranking or convergence inference.",
            "Comb threshold excess output and amplifier idle/total spectrum power unknown; amplifier lower bound is not total energy.",
            "No corrected architecture model deployed; this is a diagnostic audit."])
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if result["failures"]:
        raise SystemExit("failed checks: "+", ".join(result["failures"]))

if __name__=="__main__":
    main()
