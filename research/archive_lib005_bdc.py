"""Archive original LIB005-D1/D2 CI artifacts, then verify replay and staged byte identity.

No independent estimator, physics calibration or correction of nonpassive source coefficients.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/comparison"
MANIFEST=BASE/"lib005-bdc-archive-source.json"

def require(ok,msg):
    if not ok: raise ValueError(msg)

def sha256(data): return hashlib.sha256(data).hexdigest()
def blob(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def equal(a,b,path=""):
    if isinstance(a,bool) or isinstance(b,bool) or a is None or b is None:
        require(type(a) is type(b) and a==b,"value "+path)
    elif isinstance(a,(int,float)) and isinstance(b,(int,float)):
        require(math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10),"numeric "+path)
    elif isinstance(a,dict) and isinstance(b,dict):
        require(a.keys()==b.keys(),"keys "+path)
        for k in a:equal(a[k],b[k],path+"/"+k)
    elif isinstance(a,list) and isinstance(b,list):
        require(len(a)==len(b),"length "+path)
        for i,(x,y) in enumerate(zip(a,b)):equal(x,y,path+"/"+str(i))
    else:
        require(type(a) is type(b) and a==b,"value "+path)

def equal_csv(a,b):
    aa=list(csv.reader(io.StringIO(a.decode("utf-8"))))
    bb=list(csv.reader(io.StringIO(b.decode("utf-8"))))
    require(len(aa)==len(bb) and aa[0]==bb[0],"CSV header/count")
    for n,(rowa,rowb) in enumerate(zip(aa[1:],bb[1:])):
        require(len(rowa)==len(rowb)==len(aa[0]),"CSV width "+str(n))
        for col,(x,y) in enumerate(zip(rowa,rowb)):
            if x!=y:equal(float(x),float(y),f"CSV[{n},{col}]")

def read_artifact(raw,key):
    # GitHub Actions upload-artifact has different layouts for one versus multiple path roots.
    # Validate the exact two/three member identities, not any arbitrary nested ZIP content.
    if key=="d1":
        allowed=[{"result.json","spectral-audit.csv"},{"opa-lib-005-d1/result.json","opa-lib-005-d1/spectral-audit.csv"}]
    else:
        allowed=[
            {"opa-lib-005-d1/result.json","opa-lib-005-d1/spectral-audit.csv","opa-lib-005-d2/decision.json"},
            {"results/opa-lib-005-d1/result.json","results/opa-lib-005-d1/spectral-audit.csv","results/opa-lib-005-d2/decision.json"},
        ]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist()
        names=[i.filename for i in entries]
        require(len(entries) in (2,3) and len(names)==len(set(names)) and set(names) in allowed,"exact ZIP members "+key+": "+str(names))
        require(sum(i.file_size for i in entries)<1_000_000,"ZIP uncompressed size")
        for i in entries:
            p=PurePosixPath(i.filename)
            require(not p.is_absolute() and ".." not in p.parts and not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16) and "\\" not in i.filename,"unsafe ZIP member")
        require(z.testzip() is None,"CRC "+key)
        return {n:z.read(n) for n in names}

def normalized(files):
    out={}
    for path,data in files.items():
        name=path.rsplit("/",1)[-1]
        require(name not in out,"duplicate basename "+name)
        out[name]=data
    return out

def replay():
    for tool in ["tools/audit_lib005_bdc.py","tools/audit_lib005_bdc_decision.py"]:
        data=(ROOT/tool).read_bytes()
        expected={"tools/audit_lib005_bdc.py":"26d0ef30cddc55298f83477d0e80e04dd4f33001",
                  "tools/audit_lib005_bdc_decision.py":"e5903501f1e54c1243caad06d65b5d72a1661bc2"}[tool]
        require(blob(data)==expected,"reviewed analysis code identity "+tool)
    subprocess.run([sys.executable,str(ROOT/"tools/audit_lib005_bdc_decision.py")],
                   cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    a=ROOT/"results/opa-lib-005-d1"
    b=ROOT/"results/opa-lib-005-d2"
    return {"d1":{"result.json":(a/"result.json").read_bytes(),"spectral-audit.csv":(a/"spectral-audit.csv").read_bytes()},
            "d2":{"result.json":(a/"result.json").read_bytes(),"spectral-audit.csv":(a/"spectral-audit.csv").read_bytes(),
                  "decision.json":(b/"decision.json").read_bytes()}}

def audit(source):
    manifest=json.loads(MANIFEST.read_text())
    require([p["key"] for p in manifest]==["d1","d2"],"manifest order")
    require({p.name for p in source.iterdir()}=={"d1.zip","d2.zip"},"original ZIP count")
    require([p["experiment"] for p in manifest]==["OPA-LIB-005-D1","OPA-LIB-005-D2"],"original experiments")
    outputs={}
    count=0
    rerun=replay()
    original_hashes={}
    for p in manifest:
        key=p["key"]
        raw=(source/(key+".zip")).read_bytes()
        require(len(raw)==p["size"] and sha256(raw)==p["sha256"],"original ZIP SHA and length "+key)
        files=normalized(read_artifact(raw,key))
        expected={"d1":{"result.json","spectral-audit.csv"},"d2":{"result.json","spectral-audit.csv","decision.json"}}[key]
        require(set(files)==expected,"exact artifact basename set "+key)
        report_name="result.json" if key=="d1" else "decision.json"
        report=json.loads(files[report_name])
        equal(report,p["expected_result"],key+"/original log")
        require(report["experiment"]==p["experiment"] and all(x is True for x in report["checks"].values()),"checks "+key)
        count+=len(report["checks"])
        for n in expected:
            if n.endswith(".json"):
                equal(json.loads(files[n]),json.loads(rerun[key][n]),key+"/replay "+n)
            else:equal_csv(files[n],rerun[key][n])
            outputs[key+"/"+n]=files[n]
        outputs[key+"/original.zip"]=raw
        original_hashes[key]={"sha256":sha256(raw),"size":len(raw),"run":p["run"],"artifact":p["artifact"]}
    require(count==16,"16 original verified checks")
    first=manifest[0]["expected_result"]
    second=manifest[1]["expected_result"]
    require(first["passivity"]["nonpassive_frequencies"]==50 and first["samples"]==51,"50/51 negative")
    require(first["passivity"]["max_sigma_global"]>1 and second["decision"]["status"]=="quarantined_nonpassive","negative preserved")
    require(second["decision"]["usable_for_passive_circuit"] is False and second["decision"]["exact_geometry_calibrated"] is False,"no promotion")
    provenance={"experiment":"OPA-LIB-005-ARCHIVE","source":original_hashes,
                "source_refs":[{k:v for k,v in p.items() if k!="expected_result"} for p in manifest],
                "checks":count,"archival_evidence_not_measurement":True,"classification":"quarantined_nonpassive",
                "replay":"Exact reviewed D1 and D2 scripts; JSON fields compared against original CI logs and replay; CSV cells compared against replay. This is not an independent estimator.",
                "limitations":"Original source numerical coefficients remain untouched. No measured complex S, physical optical gain, exact matched geometry or fabrication qualification.",
                "members":{k:{"bytes":len(v),"sha256":sha256(v)} for k,v in sorted(outputs.items())}}
    outputs["provenance.json"]=(json.dumps(provenance,indent=2,sort_keys=True)+"\n").encode()
    return outputs

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output",type=Path)
    group.add_argument("--staged",type=Path)
    args=parser.parse_args()
    if args.staged:
        require(args.source is None,"staged does not take remote original source")
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            for key in ("d1","d2"):
                shutil.copyfile(args.staged/key/"original.zip",tmp/(key+".zip"))
            outputs=audit(tmp)
        paths={p.relative_to(args.staged).as_posix() for p in args.staged.rglob("*") if p.is_file()}
        require(paths==set(outputs),"exact staged file set")
        for path,data in outputs.items():
            require((args.staged/path).read_bytes()==data,"staged exact byte identity "+path)
    else:
        require(args.source is not None and not args.output.exists(),"source and fresh output required")
        outputs=audit(args.source)
        for path,data in outputs.items():
            p=args.output/path
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(data)
    print("Verified 2 original CI ZIPs, 16 checks, 50/51 negative passivity points, "+str(len(outputs))+" archive files.")
if __name__=="__main__": main()
