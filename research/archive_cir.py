"""Verify and preserve original CIR001–008 GitHub Actions ZIPs without reruns."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"research/cir_archive_manifest.json"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def read_archive(raw, m):
    require(len(raw)==m["size"] and sha(raw)==m["sha256"],m["name"]+" ZIP identity")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist()
        names=[i.filename for i in entries]
        require(len(names)==len(set(names)), "duplicate ZIP members")
        require(sum(i.file_size for i in entries)<=30_000_000,"unexpected uncompressed size")
        for i in entries:
            p=PurePosixPath(i.filename)
            require(not p.is_absolute() and len(p.parts)==1 and p.name==i.filename
                    and i.filename not in (".","..") and "\\" not in i.filename
                    and not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16),"unsafe ZIP entry")
        require(z.testzip() is None,"ZIP CRC failure")
        files={n:z.read(n) for n in names}
    require("result.json" in files,"missing result")
    r=json.loads(files["result.json"])
    require(r["experiment"]==m["experiment"] and len(r["checks"])==m["checks"]
            and all(v is True for v in r["checks"].values()) and r["failures"]==[],"unexpected numerical result")
    return files,r

def audit(source):
    manifest=json.loads(SPEC.read_text())
    out={}; reports={}; raw_by={}
    for m in manifest:
        n=m["name"]
        raw=(source/(n+".zip")).read_bytes()
        files,r=read_archive(raw,m)
        raw_by[n]=raw;reports[n]=r
        # Preserve original compressed bytes and every member byte.
        out[n+"/original.zip"]=raw
        for name,b in files.items():
            out[n+"/files/"+name]=b
        provenance=dict(**m,verification="Pinned GitHub ZIP digest and byte count, safe member names, CRC and report checks; staged bytes independently compared.",
                        members={name:dict(bytes=len(b),sha256=sha(b)) for name,b in sorted(files.items())})
        out[n+"/provenance.json"]=(json.dumps(provenance,indent=2,sort_keys=True)+"\n").encode()
    r=lambda i:reports["opa-cir-"+str(i).zfill(3)]
    require(r(1)["random_trials"]==128,"CIR001 trials")
    require(r(2)["passivity_eligible"] is True,"CIR002 passivity")
    require(r(3)["cases"]==330 and r(3)["passivity_eligible"] is True,"CIR003 result")
    require(r(4)["targets"]==8 and r(4)["passivity_eligible"] is True,"CIR004 result")
    require(r(5)["targets"]==6 and r(5)["passivity_eligible"] is True,"CIR005 result")
    require(r(6)["cases"]==255 and r(6)["center_error"]==0 and r(6)["passivity_eligible"] is True,"CIR006 result")
    require(len(r(6)["windows"])==15 and all(w["fixed_gain_screen_passed"]==(w["channels"]==1)
           and w["channel_gain_screen_passed"]==(w["channels"]==1) for w in r(6)["windows"]),"CIR006 negative WDM result")
    require(r(7)["rows"]==180 and r(7)["passing_configurations"]==4,"CIR007 screen")
    require(r(8)["scenario_count"]==96 and r(8)["accuracy_eligible"]==4,"CIR008 result")
    require(r(8)["nominal_baseline"]["partial_cooled_proxy_w"]==0.7023243568111672,"CIR008 baseline")
    require(out["opa-cir-006/files/cir005-source.zip"]==raw_by["opa-cir-005"],"CIR006 nested source mismatch")
    require(out["opa-cir-008/files/cir007-source.zip"]==raw_by["opa-cir-007"],"CIR008 nested source mismatch")
    require(r(6)["source_zip_sha256"]==sha(raw_by["opa-cir-005"]),"CIR006 provenance")
    require(r(7)["source_sha256"]==sha(raw_by["opa-cir-006"]),"CIR007 provenance")
    require(r(8)["source_zip_sha256"]==sha(raw_by["opa-cir-007"]),"CIR008 provenance")
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output",type=Path)
    g.add_argument("--staged",type=Path)
    a=p.parse_args()
    files=audit(a.source)
    if a.output:
        require(not a.output.exists(),"archive exists; refusing overwrite")
        a.output.mkdir(parents=True)
        for name,data in sorted(files.items()):
            path=a.output/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
    else:
        actual={str(p.relative_to(a.staged)) for p in a.staged.rglob("*") if p.is_file()}
        require(actual==set(files),"archive member set mismatch")
        for name,data in files.items():
            require((a.staged/name).read_bytes()==data,"staged bytes mismatch: "+name)
    print("Verified eight exact original CIR archives,",len(files),"files,",
          sum(len(b) for b in files.values()),"bytes; negative WDM outcome preserved.")

if __name__=="__main__":
    main()
