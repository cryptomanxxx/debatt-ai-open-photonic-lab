"""Independent apparent optical notch analysis, Wei et al. supplementary 4a.

Source data CC BY 4.0. No isolated ring assignment or inferred phase.
"""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/experimentally_validated/Twente-TFLN-Wei-2025"
OUT=ROOT/"results/opa-lib004-tfln-ring"
SOURCE=BASE/"archive/original/source data/Sup fig 4/Supplementary fig 4a.csv"
SHA="448402f57041b484fb1ead4b85977b1b0cef07416b812345a327f9e49ff08886"
C=299792458.0 # GHz nm
CENTERS=[1549.46741,1549.82723,1550.1877,1550.54785]
POWERS=[-77.806,-77.312,-75.736,-77.224]
WIDTHS=[1.235212589308094,1.21903859798348,1.3474450394868993,1.2852207900197254]
def require(ok,msg):
    if not ok: raise ValueError(msg)
def power(db): return 10**(db/10)
def crossing(a,b,target):
    return a[0]+(b[0]-a[0])*(target-power(a[1]))/(power(b[1])-power(a[1]))
def measure(rows,i,inner,outer):
    center,dip=rows[i]
    wings=[r[1] for r in rows if inner<=abs(r[0]-center)<=outer]
    require(len(wings)>100,"baseline samples")
    baseline=statistics.median(wings)
    target=(power(baseline)+power(dip))/2
    l=r=i
    while l>0 and power(rows[l][1])<target: l-=1
    while r<len(rows)-1 and power(rows[r][1])<target: r+=1
    require(l<i<r and power(rows[l][1])>=target and power(rows[r][1])>=target,"bracket half depth")
    left=crossing(rows[l],rows[l+1],target)
    right=crossing(rows[r-1],rows[r],target)
    require(center-outer<left<center<right<center+outer,"local crossings")
    width=C*(1/left-1/right)
    return dict(center_nm=center,center_ghz=C/center,dip_dbm=dip,baseline_dbm=baseline,apparent_extinction_db=baseline-dip,
                half_depth_dbm=10*math.log10(target),left_nm=left,right_nm=right,width_nm=right-left,
                apparent_width_ghz=width,apparent_q=(C/center)/width,baseline_samples=len(wings))
def main():
    raw=SOURCE.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==SHA,"original identity")
    with SOURCE.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.reader(f)
        require(next(reader)==["Wavelength (nm)","Optical power (dBm)"],"header")
        rows=[tuple(map(float,r)) for r in reader]
    require(len(rows)==10001 and all(len(r)==2 and all(map(math.isfinite,r)) for r in rows),"shape finite")
    require(all(a[0]>b[0] for a,b in zip(rows,rows[1:])),"descending source grid")
    rows.reverse()
    require(all(.00015<=b[0]-a[0]<=.00018 for a,b in zip(rows,rows[1:])),"sample spacing")
    candidates=[i for i in range(100,len(rows)-100) if rows[i][1]<-72 and rows[i][1]==min(r[1] for r in rows[i-100:i+101])]
    require(len(candidates)==4,"four resolved candidate minima")
    results=[]
    for k,i in enumerate(candidates):
        r=measure(rows,i,.05,.08)
        require(abs(r["center_nm"]-CENTERS[k])<1e-9 and abs(r["dip_dbm"]-POWERS[k])<1e-9,"independent minima readback")
        require(abs(r["apparent_width_ghz"]-WIDTHS[k])<1e-8,"independent linewidth readback")
        r["baseline_window_sensitivity"]=[dict(inner_nm=a,outer_nm=b,metrics=measure(rows,i,a,b)) for a,b in ((.04,.07),(.05,.08),(.06,.09))]
        results.append(r)
    spacings=[a["center_ghz"]-b["center_ghz"] for a,b in zip(results,results[1:])]
    require(all(44<s<46 for s in spacings),"periodicity screen")
    # Check exact frequency transform against independent difference formula.
    for a,b,s in zip(results,results[1:],spacings):
        require(abs(s-C*(b["center_nm"]-a["center_nm"])/(a["center_nm"]*b["center_nm"]))<1e-8,"frequency difference crosscheck")
    report=dict(experiment="OPA-LIB-004-TFLN-RING",source_doi="10.5281/zenodo.14065933",article_doi="10.1038/s41467-025-57441-1",
                source_path=SOURCE.relative_to(BASE).as_posix(),source_sha256=SHA,rows=len(rows),resonance_candidates=results,
                adjacent_spacing_ghz=spacings,median_spacing_ghz=statistics.median(spacings),literature_fsr_ghz=44,
                scope="apparent optical notch metrics from one archived circuit spectrum; no isolated resonator assignment",
                isolated_ring_fsr_ghz=None,intrinsic_q=None,calibrated_loaded_q=None,complex_s=None,coupling_state=None,geometry_match=None,measurement_uncertainty=None,qualification=None,
                checks=dict(source_identity=True,shape_grid=True,minima_readback=True,width_readback=True,periodicity=True,frequency_crosscheck=True),
                limitations=["Absolute dBm, not normalized transmission; local baseline estimated from median wings.",
                             "Half-depth is midpoint in linear power, not 3 dB above dip minimum.",
                             "Apparent widths/Q include instrument response and circuit context; no deconvolution or isolated-ring fit.",
                             "Spacing is consistent with reported 44 GHz FSR, not exact independent attribution to a specific ring.",
                             "No phase, under/overcoupling discrimination, intrinsic Q or exact LNOI400 calibration."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    with (OUT/"notches.csv").open("w",newline="") as f:
        keys=[k for k in results[0] if k!="baseline_window_sensitivity"]
        w=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore");w.writeheader();w.writerows(results)
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__": main()
