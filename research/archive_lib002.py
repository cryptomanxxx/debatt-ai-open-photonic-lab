"""Preserve the exact successful LIB002 artifact; no PCell regeneration."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/external/Luxtelligence/lnoi400"
MANIFEST=BASE/"archive-source.json"
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b):
    return hashlib.sha256(b).hexdigest()
def audit(raw):
    m=json.loads(MANIFEST.read_text())
    require(len(raw)==m["size"] and sha(raw)==m["sha256"],"pinned ZIP identity")
    ids=set(m["components"])
    require(len(ids)==7,"seven pinned components")
    expected={i+s for i in ids for s in (".gds",".json")} | {"result.json","LICENSE","generation-spec.json","environment-lock.txt","installed-packages.json"}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist()
        names=[i.filename for i in entries]
        require(len(names)==len(set(names)) and set(names)==expected,"exact ZIP member set")
        require(sum(i.file_size for i in entries)<10_000_000,"archive size limit")
        for i in entries:
            p=PurePosixPath(i.filename)
            require(len(p.parts)==1 and p.name==i.filename and not p.is_absolute() and "\\" not in i.filename and not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16),"unsafe member")
        require(z.testzip() is None,"ZIP CRC")
        files={n:z.read(n) for n in names}
    for name,path in [("LICENSE",BASE/"LICENSE"),("generation-spec.json",BASE/"generation-spec.json"),("environment-lock.txt",ROOT/"layout/requirements-lock-lnoi400.txt")]:
        require(files[name]==path.read_bytes(),"source identity "+name)
    spec=json.loads(files["generation-spec.json"])
    r=json.loads(files["result.json"])
    require(r["experiment"]==m["experiment"]==spec["experiment"] and r["revision"]==m["revision"]==spec["revision"],"experiment revision")
    require(r["origin"]==spec["origin"]=="external_pcell_generated" and r["license_sha256"]==sha(files["LICENSE"]),"origin and license")
    require(set(r["checks"])=={"source_identity","license_identity","geometry_readback","pcell_port_inventory","allowed_layers","fresh_process_reproducibility"} and all(v is True for v in r["checks"].values()),"six audit checks")
    require(len(r["components"])==len(spec["components"])==7,"component count")
    rows={x["id"]:x for x in r["components"]}
    specs={x["id"]:x for x in spec["components"]}
    require(set(rows)==set(specs)==ids,"component identity")
    for ident in sorted(ids):
        row=rows[ident]; s=specs[ident]
        gds=files[ident+".gds"]
        require(json.loads(files[ident+".json"])==row,"sidecar matches report "+ident)
        require(row["gds_file"]==ident+".gds" and row["gds_bytes"]==len(gds) and row["gds_sha256"]==sha(gds) and [len(gds),sha(gds)]==m["components"][ident],"GDS identity "+ident)
        require(row["source_revision"]==m["revision"] and row["origin"]=="external_pcell_generated" and row["factory"]==s["factory"] and row["kwargs"]==s["kwargs"],"PCell provenance "+ident)
        require(all(row[k] is None for k in ("drc","measurement","qualification")) and row["complex_s_parameters"]=="not_imported","evidence scope "+ident)
        require(len(row["ports"])==s["expected_optical_ports"]+s["expected_electrical_ports"],"port count "+ident)
        require({p["name"] for p in row["ports"] if p["type"]=="optical"}=={f"o{i}" for i in range(1,s["expected_optical_ports"]+1)},"optical inventory "+ident)
        require({p["name"] for p in row["ports"] if p["type"]=="electrical"}=={f"e{i}" for i in range(1,s["expected_electrical_ports"]+1)},"electrical inventory "+ident)
    out={"original.zip":raw}
    for name,b in files.items():
        folder="gds" if name.endswith(".gds") else "ports" if name.endswith(".json") and name[:-5] in ids else "evidence"
        out[folder+"/"+name]=b
    provenance=dict(**m,verification="Pinned original CI artifact ZIP, CRC, exact member set, individual GDS hashes, sidecar/report equivalence and staged byte identity; no reruns.",
                    members={name:{"bytes":len(b),"sha256":sha(b)} for name,b in sorted(out.items())})
    out["provenance.json"]=(json.dumps(provenance,indent=2,sort_keys=True)+"\n").encode()
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output",type=Path)
    g.add_argument("--staged",type=Path)
    a=p.parse_args()
    files=audit(a.source.read_bytes())
    if a.output:
        require(not a.output.exists(),"refuse overwrite")
        a.output.mkdir(parents=True)
        for n,b in files.items():
            f=a.output/n
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(b)
    else:
        require({p.relative_to(a.staged).as_posix() for p in a.staged.rglob("*") if p.is_file()}==set(files),"archived member set")
        for n,b in files.items():
            require((a.staged/n).read_bytes()==b,"archived bytes "+n)
    print(f"Verified seven LIB002 GDS files, {len(files)} archive files, {sum(map(len,files.values()))} bytes.")
if __name__=="__main__":
    main()
