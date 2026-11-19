"""Independent analysis of Wei et al. Supplementary Figure 1, CC BY 4.0 source data.

Optical powers from separate bias scans, not optical S parameters.
Figure 1c is a theoretical reference curve, not a measurement.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/experimentally_validated/Twente-TFLN-Wei-2025"
OUT=ROOT/"results/opa-lib004-tfln-modulator"
PINS={
    "1a":("2eaab62a46d5602d340cfdf38fa285e4d2837921c5bd5a7081f991c09b65ef99",10001,["Frequency (GHz)","Optical power (dBm)"]),
    "1b":("cafbf3676703360c9a4965f0ffba8352ce8948c08baa32e324aaac47059892d8",1001,["Frequency (GHz)","Optical power carrier max (dBm)","Optical power sideband max (dBm)"]),
    "1c":("26b49de6c0b7f3e2bee16ee57bfd2d0915f837b4d0a5bf62477d02b95b550519",400,["Modulation depth (rad)","Ratio of sideband and carrier (dB)"]),
}
def require(ok,msg):
    if not ok: raise ValueError(msg)
def read(key):
    digest,n,header=PINS[key]
    path=BASE/"archive/original/source data/Sup fig 1"/f"Supplementary fig {key}.csv"
    require(hashlib.sha256(path.read_bytes()).hexdigest()==digest,"original hash "+key)
    with path.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.reader(f)
        require(next(reader)==header,"exact header "+key)
        rows=[tuple(map(float,r)) for r in reader]
    require(len(rows)==n and all(len(r)==len(header) and all(map(math.isfinite,r)) for r in rows),"shape/finite "+key)
    sign=-1 if key=="1a" else 1
    require(all(sign*(b[0]-a[0])>0 for a,b in zip(rows,rows[1:])),"monotonic axis "+key)
    if key!="1c":
        require(all(abs(abs(b[0]-a[0])-.02)<1e-8 for a,b in zip(rows,rows[1:])),"frequency step "+key)
    return rows
def bessel(n,x):
    require(n in (0,1) and 0<=x<=2,"Bessel domain")
    term=1.0 if n==0 else x/2
    terms=[term]
    for k in range(1,30):
        term*=-x*x/(4*k*(k+n))
        terms.append(term)
    return math.fsum(terms)
def ratio(m):
    return 20*math.log10(bessel(1,m)/bessel(0,m))
def invert(db):
    lo,hi=.01,2.
    require(ratio(lo)<=db<=ratio(hi),"ratio domain")
    for _ in range(60):
        mid=(lo+hi)/2
        if ratio(mid)<db: lo=mid
        else: hi=mid
    return (lo+hi)/2
def main():
    a,b,c=map(read,("1a","1b","1c"))
    carrier=max(b,key=lambda r:r[1])
    f0,p0=carrier[:2]
    require(abs(f0-193317.08)<1e-8 and abs(p0+16.15772)<1e-8,"independent carrier readback")
    peaks=[]
    for direction in (-1,1):
        # 5 GHz drive stated in supplementary text, +/-0.5 GHz search.
        window=[r for r in b if abs(r[0]-f0-direction*5)<=.5]
        peak=max(window,key=lambda r:r[2])
        require(peak!=window[0] and peak!=window[-1],"interior sideband peak")
        db=peak[2]-p0
        depth=invert(db)
        require(abs(ratio(depth)-db)<1e-10,"inverse residual")
        # Interpolate tabulated theoretical curve independently of Bessel inversion.
        left,right=next((l,r) for l,r in zip(c,c[1:]) if l[1]<=db<=r[1])
        interp=left[0]+(right[0]-left[0])*(db-left[1])/(right[1]-left[1])
        require(abs(interp-depth)<5e-5,"table inverse crosscheck")
        sensitivity=[]
        for halfwidth in (.25,.5,.75):
            q=max((r for r in b if abs(r[0]-f0-direction*5)<=halfwidth),key=lambda r:r[2])
            sensitivity.append({"halfwidth_ghz":halfwidth,"peak_ghz":q[0],"power_dbm":q[2]})
        peaks.append(dict(side="lower" if direction<0 else "upper",frequency_ghz=peak[0],offset_ghz=peak[0]-f0,power_dbm=peak[2],relative_db=db,modulation_depth_rad=depth,table_interpolated_depth_rad=interp,window_sensitivity=sensitivity))
    require(abs(peaks[0]["relative_db"]+26.86816)<1e-8 and abs(peaks[1]["relative_db"]+26.51264)<1e-8,"independent sideband readback")
    require(abs(peaks[0]["modulation_depth_rad"]-.0906099541179797)<1e-10 and abs(peaks[1]["modulation_depth_rad"]-.09438737462908176)<1e-10,"independent depth readback")
    require(all(r[1]<s[1] for r,s in zip(c,c[1:])),"monotone reference curve")
    residual=[(m,db,ratio(m),db-ratio(m)) for m,db in c]
    maxerr=max(abs(r[3]) for r in residual)
    require(maxerr<.0002,"theoretical table consistency")
    # Maxhold spectrum is not a calibrated EO transfer-function sweep.
    maxhold=max(a,key=lambda r:r[1])
    require(abs(maxhold[0]-193399.8)<1e-8 and abs(maxhold[1]+19.10201)<1e-8,"maxhold readback")
    report=dict(experiment="OPA-LIB-004-TFLN-MOD",source_doi="10.5281/zenodo.14065933",article_doi="10.1038/s41467-025-57441-1",
                source_files={k:{"sha256":v[0],"data_rows":v[1],"columns":v[2]} for k,v in PINS.items()},
                carrier=dict(frequency_ghz=f0,power_dbm=p0),sidebands=peaks,
                sideband_asymmetry_db=peaks[1]["power_dbm"]-peaks[0]["power_dbm"],
                maxhold=dict(samples=len(a),frequency_span_ghz=[a[-1][0],a[0][0]],peak_frequency_ghz=maxhold[0],peak_power_dbm=maxhold[1]),
                theoretical_curve=dict(samples=len(c),max_abs_error_db=maxerr,rmse_db=math.sqrt(math.fsum(r[3]**2 for r in residual)/len(residual))),
                literature=dict(rf_ghz=5,modulation_depth_rad=.095,vpi_rf_v=3.5,electrode_length_cm=1),
                independently_extracted_vpi_v=None,delivered_rf_peak_voltage_v=None,eo_bandwidth_ghz=None,measurement_uncertainty=None,complex_s=None,geometry_match=None,qualification=None,
                checks=dict(source_identity=True,shape_grid=True,peak_readback=True,bessel_table=True,inversion_crosscheck=True,maxhold_readback=True),
                limitations=["Separate bias scans; not simultaneous power ratios or complex optical S.","Figure 1c theoretical reference only; not 400 independent measurements.","Delivered RF amplitude not established by these CSVs; no independent Vpi.","Maxhold optical spectrum not calibrated EO frequency response; no bandwidth inferred.","Window sensitivity is not measurement uncertainty.","Different TFLN process from lnoi400; no model calibration."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    with (OUT/"theory-replay.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["depth_rad","source_theory_db","independent_bessel_db","residual_db"]);w.writerows(residual)
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__": main()
