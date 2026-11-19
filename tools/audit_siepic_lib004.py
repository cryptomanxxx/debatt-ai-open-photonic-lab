"""OPA-LIB-004: audit original measured SiEPIC spiral cutback scans.

No phase reconstruction, no exact-cell certification, no cross-platform fit.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import scipy
from scipy.io import loadmat
from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "components/experimentally_validated/SiEPIC-PCM-2020-02-UW"
OUT = ROOT / "results/opa-lib-004"
REV = "363fbb52eefa8669100499ab531d3fe7befc4867"
LENGTHS = [1213, 11204, 32237, 53018, 102530]
DEVICES = [1698, 1695, 1711, 1712, 1699]
MEASURED_DEVICES = [1363, 1360, 1376, 1377, 1364]
BLOBS = ["4cdfbe9acf553a68696337663e5acdec2144cd98",
         "68aa62ff077e818561bfb64ad6839b07cb82bcc7",
         "68ef25d77935bf25c17a424e8723d45d1a625dab",
         "b43f95bba900f8862af75d9798a3363a028c125f",
         "a54b25e1b78d44bc73188b7821398b85ac37258e"]
CENTER = np.array([-25.376132318130566, -32.439206132237835,
                   -36.03509304381582, -41.29090969191405, -51.54415074216904])
FLOOR = -100.0  # observed stored sentinel; not a calibrated detector sensitivity

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def blob(b):
    return hashlib.sha1(f"blob {len(b)}\0".encode() + b).hexdigest()

def regression(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    require(x.shape == y.shape and len(x) == 5 and np.isfinite(y).all(), "five finite observations")
    xx = x - x.mean()
    ssx = float(xx @ xx)
    slope = float(xx @ (y-y.mean()) / ssx)
    intercept = float(y.mean() - slope*x.mean())
    res = y - (intercept+slope*x)
    sse = float(res @ res)
    sst = float((y-y.mean()) @ (y-y.mean()))
    se = float(np.sqrt(sse / (len(x)-2) / ssx))
    half = float(t.ppf(.975, len(x)-2)*se)
    return dict(loss_db_per_cm=-slope, slope_db_per_cm=slope,
                intercept_db=intercept, r2=1-sse/sst if sst>0 else None,
                residual_db=res.tolist(), slope_standard_error_db_per_cm=se,
                conditional_ols_95ci_loss_db_per_cm=[-slope-half,-slope+half])

def main():
    m = json.loads((BASE/"manifest.json").read_text())
    require(m["revision"] == REV and m["experiment"] == "OPA-LIB-004", "revision")
    require(m["detector_number"] == 2 and m["phase"] is None and m["complex_s"] is None
            and m["qualification"] is None and m["measurement_uncertainty"] is None, "evidence scope")
    require(blob((BASE/"LICENSE.md").read_bytes()) == m["license_git_blob_sha1"] ==
            "e5d16d71c2ff1f40c393ef23a2e01cb850aa9a4d", "license identity")
    require(blob((BASE/"upstream/spiral_cutback_analysis.py").read_bytes()) ==
            m["analysis_git_blob_sha1"] == "7360437856a7491acd1c1fa4bf5a89aaf4f5dffc", "analysis identity")
    require(len(m["files"]) == 5, "file count")
    scans = []; records = []; reference = None
    for e, length, device, measured_device, expected_blob in zip(m["files"], LENGTHS, DEVICES, MEASURED_DEVICES, BLOBS, strict=True):
        name = f"PCM_PCM_SpiralWG{length}TE_gap2000_{device}.mat"
        require(e["name"] == name and e["source_path"] == "PCM/D2020_02_UW/"+name
                and e["nominal_length_um"] == length and e["device_number"] == device
                and e["measured_device_number"] == measured_device, "selection")
        raw = (BASE/"original"/name).read_bytes()
        require(len(raw) == e["bytes"] == 193336 and blob(raw) == e["git_blob_sha1"] == expected_blob, "original MAT identity")
        mat = loadmat(BASE/"original"/name, squeeze_me=True, struct_as_record=False)
        w = np.asarray(mat["scandata"].wavelength, dtype=float)
        p = np.asarray(mat["scandata"].power, dtype=float)
        meta = mat["metadata"]
        require(w.shape == (6001,) and p.shape == (6001,3) and np.isfinite(w).all() and np.isfinite(p).all(), "scan dimensions/finite")
        require(np.all(np.diff(w)>0) and np.max(abs(w*1e9-np.linspace(1520,1580,6001)))<1e-9, "wavelength grid")
        if reference is None:
            reference = w
        else:
            require(np.array_equal(reference,w), "identical measured grids")
        require(str(meta.device) == name[:-4], "stored device label identity")
        require(int(meta.measured_device_number) == measured_device, "stored measured-device identity")
        coord = str(meta.coord_file_line).split(",")
        require(len(coord)==7 and coord[2:5]==["TE","1550","device"] and coord[5]==name[:-4], "TE label")
        require(np.isclose(float(coord[0]),float(meta.gds_x_coord)) and np.isclose(float(coord[1]),float(meta.gds_y_coord)), "layout coordinate metadata")
        scans.append(p)
        records.append(dict(name=name,nominal_length_um=length,device_number=device, measured_device_number=measured_device,
                            gds_coord_as_stored=[float(meta.gds_x_coord),float(meta.gds_y_coord)],
                            measured_time_as_stored=str(meta.time_str),sha256=sha(raw),git_blob_sha1=expected_blob,
                            points=len(w),detectors=3,detector2_floor_count=int(np.count_nonzero(p[:,1]<=FLOOR)),
                            detector2_center_db=float(p[3000,1])))
    data = np.stack(scans)
    x = np.array(LENGTHS)*1e-4  # source analysis uses length in cm
    y = data[:,:,1]
    require(np.max(abs(y[:,3000]-CENTER))<1e-10, "frozen independently read center")
    require(np.all(y[:,3000]>FLOOR), "center above stored floor")
    center = regression(x,y[:,3000])
    require(abs(center["loss_db_per_cm"]-2.40201899741961)<1e-10, "independent center regression")
    # Cross-check least squares independently of centered formula.
    ref = np.linalg.lstsq(np.column_stack((np.ones(5),x)),y[:,3000],rcond=None)[0]
    require(np.max(abs(ref-[center["intercept_db"],center["slope_db_per_cm"]]))<1e-10, "OLS crosscheck")
    # Only complete five-point rows are fitted; preserve floor observations in raw export.
    rows = []
    for i,w in enumerate(reference):
        n = int(np.count_nonzero(y[:,i]<=FLOOR))
        row = dict(wavelength_nm=float(w*1e9),floor_or_below_count=n,
                   eligible_complete_five_point_fit=n==0,
                   loss_db_per_cm=None,intercept_db=None,r2=None)
        if n==0:
            fit=regression(x,y[:,i])
            row.update({k:fit[k] for k in ("loss_db_per_cm","intercept_db","r2")})
        rows.append(row)
    # Local 1540–1560 nm quartic sensitivity analysis, not the upstream full-grid
    # polynomial; evaluate at 1550 without clipping or replacing original scans.
    local = (reference>=1540e-9-1e-18)&(reference<=1560e-9+1e-18)
    fitted_center = []
    for p in y:
        keep=local&(p>FLOOR)
        require(np.count_nonzero(keep)>=5,"local polynomial samples")
        coefficients=np.polynomial.polynomial.polyfit((reference[keep]-1.55e-6)*1e9,p[keep],4)
        fitted_center.append(float(coefficients[0]))
    sensitivity = regression(x,fitted_center)
    # Leave-one-out sensitivity: OLS slopes only; not independent replicate uncertainty.
    loo=[]
    for i in range(5):
        keep=np.arange(5)!=i
        fit=np.linalg.lstsq(np.column_stack((np.ones(4),x[keep])),y[keep,3000],rcond=None)[0]
        loo.append(dict(omitted_device=DEVICES[i],loss_db_per_cm=-float(fit[1])))
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"raw-detectors.csv").open("w",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["device_number","nominal_length_um","wavelength_nm","detector1_db","detector2_db","detector3_db"])
        for j,device in enumerate(DEVICES):
            for i,w in enumerate(reference):
                writer.writerow([device,LENGTHS[j],float(w*1e9),*map(float,data[j,i])])
    with (OUT/"cutback-spectrum.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    report=dict(experiment="OPA-LIB-004",revision=REV,source_run=m["source_run"],
                evidence_scope=m["evidence_scope"],geometry_match=m["geometry_match"],
                measurement_files=records,detector_number=2,polarization="TE label",
                wavelength_points_per_scan=6001,detector_readings=int(data.size),
                center_wavelength_nm=1550,center_raw_fit=center,
                center_local_quartic_fit=sensitivity,center_local_quartic_detector_values_db=fitted_center,
                leave_one_out_center=loo,complete_spectral_fits=sum(r["eligible_complete_five_point_fit"] for r in rows),
                floor_or_below_counts=[r["detector2_floor_count"] for r in records],
                checks=dict(original_identity=True,shape_and_finite=True,common_grid=True,device_metadata=True,
                            independent_center_readback=True,ols_crosscheck=True),
                phase=None,complex_s=None,qualification=None,measurement_uncertainty=None,
                numpy_version=np.__version__,scipy_version=scipy.__version__,python_version=sys.version.split()[0],
                limitations=["External measured spiral test structures, not exact archived component GDS.",
                             "Effective length-dependent loss includes bend/layout/fabrication/coupling variations; no isolated straight-waveguide loss claim.",
                             "Detector values follow upstream dB usage; absolute calibration, temperature and uncertainty unknown.",
                             "OLS intervals conditional on regression assumptions with n=5, not calibrated instrument or wafer uncertainty.",
                             "Stored -100 dB floor is observed, not a calibrated sensitivity; incomplete rows excluded, not interpolated.",
                             "No measured phase or complex S, no comparison to TFLN, no process qualification."])
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
