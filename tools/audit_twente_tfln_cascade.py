"""Compare recurring optical minima in four exact Wei supplementary 4a-d scans."""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/experimentally_validated/Twente-TFLN-Wei-2025"
OUT=ROOT/"results/opa-lib004-tfln-cascade"
C=299792458.
PINS={
"a":"448402f57041b484fb1ead4b85977b1b0cef07416b812345a327f9e49ff08886",
"b":"65d605cd0f3f1eb33aa4290f161c8a318c0bb6f40c34905b895645b5535bee2a",
"c":"062fe853a964851304f199bef4722fa79c9c4e4c9221f45c5efdf85890e6c8be",
"d":"40ab41ca5bcd316ed01fec415091d19594ebd2b8c46d69a2f7e7723fbcf6ec3c"}
CENTERS={
"a":[1549.46741,1549.82723,1550.1877,1550.54785],
"b":[1549.37068,1549.46389,1549.73141,1549.82435,1550.0912,1550.18433,1550.45163,1550.54465],
"c":[1549.36459,1549.40175,1549.46229,1549.72436,1549.76074,1549.82275,1550.08478,1550.12133,1550.18289,1550.44441,1550.48113,1550.5432],
"d":[1549.35723,1549.39102,1549.42321,1549.45764,1549.71715,1549.75032,1549.78333,1549.81762,1550.07741,1550.11091,1550.14345,1550.17664,1550.43848,1550.47071,1550.50375,1550.53759]}
WINDOWS=[(1549.30,1549.60),(1549.66,1549.96),(1550.02,1550.32),(1550.38,1550.68)]
def require(ok,msg):
    if not ok: raise ValueError(msg)
def read(key):
    p=BASE/"archive/original/source data/Sup fig 4"/f"Supplementary fig 4{key}.csv"
    require(hashlib.sha256(p.read_bytes()).hexdigest()==PINS[key],"source identity")
    with p.open(encoding="utf-8-sig",newline="") as f:
        r=csv.reader(f)
        require(next(r)==["Wavelength (nm)","Optical power (dBm)"],"header")
        rows=[tuple(map(float,v)) for v in r]
    require(len(rows)==10001 and all(len(v)==2 and all(map(math.isfinite,v)) for v in rows),"shape")
    rows.reverse()
    require(all(.00015<=b[0]-a[0]<=.00018 for a,b in zip(rows,rows[1:])),"grid")
    return rows
def minima(rows,threshold,radius):
    return [rows[i] for i in range(radius,len(rows)-radius)
            if rows[i][1]<threshold and rows[i][1]==min(r[1] for r in rows[i-radius:i+radius+1])]
def delta(a,b):
    return C*(b-a)/(a*b)
def groups(candidates):
    return [[v for v in candidates if lo<=v[0]<=hi] for lo,hi in WINDOWS]
def main():
    report=[];flat=[];reference=None
    for n,key in enumerate(PINS,1):
        rows=read(key)
        grid=[v[0] for v in rows]
        if reference is None: reference=grid
        require(grid==reference,"common wavelength grid")
        candidates=minima(rows,-72,100)
        require([v[0] for v in candidates]==CENTERS[key],"independent center readback")
        g=groups(candidates)
        require(len(candidates)==4*n and all(len(v)==n for v in g),"repeated count")
        periods=[];spans=[];adj=[]
        for j,group in enumerate(g):
            span=delta(group[0][0],group[-1][0])
            gaps=[delta(a[0],b[0]) for a,b in zip(group,group[1:])]
            require(abs(sum(gaps)-span)<1e-9,"span sum")
            spans.append(span);adj.extend(gaps)
            periods.append(dict(period=j+1,span_ghz=span,adjacent_gaps_ghz=gaps,minima=[dict(wavelength_nm=w,power_dbm=p,frequency_ghz=C/w) for w,p in group]))
            for k,(w,p) in enumerate(group,1):
                flat.append(dict(scan=key,period=j+1,ordinal=k,wavelength_nm=w,power_dbm=p,frequency_ghz=C/w))
        recurrence=[delta(g[j][k][0],g[j+1][k][0]) for j in range(3) for k in range(n)]
        require(all(44<s<46 for s in recurrence),"ordinal recurrence screen")
        sensitivity=[]
        for threshold in (-71,-72,-73,-74):
            for radius in (75,100,125):
                c=minima(rows,threshold,radius)
                counts=[len(v) for v in groups(c)]
                sensitivity.append(dict(threshold_dbm=threshold,radius_samples=radius,total=len(c),counts_by_window=counts,outside_windows=len(c)-sum(counts)))
        report.append(dict(scan=key,rows=len(rows),source_sha256=PINS[key],minima_count=len(candidates),minima_per_period=n,periods=periods,
                           span_range_ghz=[min(spans),max(spans)],adjacent_gap_range_ghz=[min(adj),max(adj)] if adj else None,
                           recurrence_range_ghz=[min(recurrence),max(recurrence)],median_recurrence_ghz=statistics.median(recurrence),sensitivity=sensitivity))
    result=dict(experiment="OPA-LIB-004-TFLN-CASCADE",source_doi="10.5281/zenodo.14065933",article_doi="10.1038/s41467-025-57441-1",
                scans=report,rows=40004,additional_rows_vs_ring=30003,minima_count=len(flat),
                selection=dict(threshold_dbm=-72,radius_samples=100,wavelength_windows_nm=WINDOWS,exploratory=True),
                scope="Four optical circuit spectra; repeated minima, no isolated physical ring attribution",
                physical_ring_assignment=None,heater_settings=None,complex_s=None,geometry_match=None,qualification=None,measurement_uncertainty=None,
                checks=dict(source_identity=True,shape_grid=True,common_grid=True,independent_minima_readback=True,repeated_count=True,recurrence=True,span_consistency=True),
                limitations=["Exploratory threshold and windows chosen after data inspection; sensitivity is descriptive, not instrument uncertainty.",
                             "Minima counts are algorithm-dependent, not physical ring counts.",
                             "Ordinal recurrence is not proof of common mode identity or isolated FSR.",
                             "Absolute optical power, no coherent phase or transfer matrix reconstruction.",
                             "No calibrated cascade model, exact geometry match, or RF bandwidth inferred."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with (OUT/"minima.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__": main()
