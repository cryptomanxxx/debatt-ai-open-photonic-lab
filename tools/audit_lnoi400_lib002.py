"""Generate and audit external PCell reference geometry; no DRC or optical simulation."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import gdsfactory as gf
import klayout.db as kdb
import lnoi400
from lnoi400 import cells
from lnoi400.tech import LAYER

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/external/Luxtelligence/lnoi400"
SPEC=json.loads((BASE/"generation-spec.json").read_text())
REV="d16db6a4882657feb1ce696c16c604ff6cb7ccfa"
EXPECTED={
    "straight-rwg1000":("straight_rwg1000",{"length":100},2,0),
    "euler-bend-90":("L_turn_bend",{},2,0),
    "mmi-2x2":("mmi2x2_optimized1550",{},4,0),
    "directional-coupler":("directional_coupler_balanced",{},4,0),
    "edge-coupler":("double_linear_inverse_taper",{},2,0),
    "eo-phase-shifter-5mm":("eo_phase_shifter",{"modulation_length":5000},2,2),
    "mzm-2x2-5mm":("mzm_unbalanced",{"modulation_length":5000,"length_imbalance":0,"splitter":"mmi2x2_optimized1550","with_heater":True},4,4),
}
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(p):
    raw=p.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
def source_audit():
    src=Path(os.environ["LXT_PDK_DIR"]).resolve()
    require(subprocess.check_output(["git","-C",str(src),"rev-parse","HEAD"],text=True).strip()==REV==SPEC["revision"],"PDK revision")
    require(not subprocess.check_output(["git","-C",str(src),"status","--porcelain","--untracked-files=no"],text=True).strip(),"modified upstream tracked files")
    require(Path(cells.__file__).resolve()==src/"lnoi400/cells.py","actual PCell source")
    require(blob(src/"lnoi400/cells.py")==SPEC["source_cells_git_blob_sha1"],"cells blob")
    require(blob(src/"lnoi400/tech.py")==SPEC["source_tech_git_blob_sha1"],"tech blob")
    require((src/"LICENSE").read_bytes()==(BASE/"LICENSE").read_bytes() and blob(BASE/"LICENSE")==SPEC["license_git_blob_sha1"],"license bytes")
    require(SPEC["origin"]=="external_pcell_generated" and SPEC["schema_version"]==1 and SPEC["experiment"]=="OPA-LIB-002","manifest identity")
    require(len(SPEC["components"])==len(EXPECTED) and {x["id"] for x in SPEC["components"]}==set(EXPECTED),"component selection")
    return src
def generate(out):
    source_audit()
    lnoi400.activate_pdk()
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    allowed={(l.layer,l.datatype) for l in LAYER}
    for spec in SPEC["components"]:
        ident=spec["id"]
        factory,kwargs,nopt,nelec=EXPECTED[ident]
        require((spec["factory"],spec["kwargs"],spec["expected_optical_ports"],spec["expected_electrical_ports"])==(factory,kwargs,nopt,nelec),"selection "+ident)
        require(all(spec[k] is None for k in ("drc","measurement","qualification")),"evidence scope")
        c=getattr(cells,factory)(**kwargs)
        ports=[]
        for p in sorted(c.ports,key=lambda q:q.name):
            row=dict(name=p.name,type=p.port_type,center_um=[float(v) for v in p.dcenter],width_um=float(p.dwidth),orientation_deg=float(p.orientation))
            require(all(math.isfinite(x) for x in row["center_um"]+[row["width_um"],row["orientation_deg"]]) and row["width_um"]>0,"invalid port "+ident)
            ports.append(row)
        require(len(ports)==nopt+nelec and len({p["name"] for p in ports})==len(ports),"port count "+ident)
        require({p["name"] for p in ports if p["type"]=="optical"}=={f"o{i}" for i in range(1,nopt+1)},"optical names "+ident)
        require({p["name"] for p in ports if p["type"]=="electrical"}=={f"e{i}" for i in range(1,nelec+1)},"electrical names "+ident)
        path=out/(ident+".gds")
        c.write_gds(path,with_metadata=False)
        ly=kdb.Layout()
        ly.read(str(path))
        tops=ly.top_cells()
        require(len(tops)==1 and tops[0].name==c.name,"GDS top cell "+ident)
        top=tops[0]
        require(math.isfinite(ly.dbu) and ly.dbu>0,"DBU")
        used={(ly.get_info(i).layer,ly.get_info(i).datatype) for i in ly.layer_indexes() if not top.begin_shapes_rec(i).at_end()}
        require(used<=allowed,"non-PDK layers "+ident)
        required={tuple(map(int,x.split("/"))) for x in spec["required_geometry_layers"]}
        require(required<=used,"required layers "+ident)
        areas={}
        for layer in sorted(required):
            region=kdb.Region(top.begin_shapes_rec(ly.find_layer(*layer))).merged()
            require(not region.is_empty() and region.area()>0,"empty geometry "+ident)
            areas[f"{layer[0]}/{layer[1]}"]=region.area()*ly.dbu**2
        bbox=top.bbox()
        require(bbox.width()>0 and bbox.height()>0,"bbox "+ident)
        # The port sidecar comes directly from the PCell, not GDS markers.
        sidecar=dict(id=ident,origin=SPEC["origin"],factory=factory,kwargs=kwargs,source_revision=REV,top_cell=top.name,
                     gds_file=path.name,gds_sha256=sha(path),gds_bytes=path.stat().st_size,dbu_um=ly.dbu,
                     bbox_um=[v*ly.dbu for v in (bbox.left,bbox.bottom,bbox.right,bbox.top)],
                     used_layers=[f"{a}/{b}" for a,b in sorted(used)],required_layer_area_um2=areas,
                     ports=ports,port_source="upstream PCell API; not independently validated modal reference planes",
                     drc=None,measurement=None,qualification=None,complex_s_parameters="not_imported")
        (out/(ident+".json")).write_text(json.dumps(sidecar,indent=2,sort_keys=True,allow_nan=False)+"\n")
        rows.append(sidecar)
    return rows
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=ROOT/"results/opa-lib-002")
    p.add_argument("--generate-only",action="store_true")
    a=p.parse_args()
    rows=generate(a.out)
    if a.generate_only:return
    with tempfile.TemporaryDirectory() as d:
        other=Path(d)
        subprocess.run([sys.executable,__file__,"--out",str(other),"--generate-only"],check=True)
        for r in rows:
            for suffix in (".gds",".json"):
                name=r["id"]+suffix
                require((a.out/name).read_bytes()==(other/name).read_bytes(),"fresh-process reproducibility "+name)
    report=dict(experiment="OPA-LIB-002",revision=REV,origin=SPEC["origin"],source_repository=SPEC["source_repository"],
                license_sha256=sha(BASE/"LICENSE"),gdsfactory_version=gf.__version__,python_version=sys.version.split()[0],
                components=rows,checks=dict(source_identity=True,license_identity=True,geometry_readback=True,
                pcell_port_inventory=True,allowed_layers=True,fresh_process_reproducibility=True),
                limitations=["Generated from external PCells with pinned defaults/overrides, not original upstream GDS bytes.",
                "GDS geometry and PCell port metadata only; not DRC, modal reference-plane verification, RF simulation, measurement or fabrication qualification.",
                "CIR002 MMI nominal geometry is a candidate model correspondence, not validated measured equivalence.",
                "MZM uses 2x2 splitter unlike default 1x2 compact MZM model; do not attach that default model to this four-port geometry.",
                "No complex S dataset imported and no cross-process assembly."])
    (a.out/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__":
    main()
