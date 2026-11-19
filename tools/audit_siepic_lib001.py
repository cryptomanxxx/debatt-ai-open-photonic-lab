"""OPA-LIB-001: audit exact original SiEPIC GDS, not a DRC or optical simulation."""
import hashlib
import json
import math
from pathlib import Path
import klayout.db as kdb

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/external/SiEPIC-EBeam"
OUT=ROOT/"results/opa-lib-001"
EXPECTED={
    "ebeam_bdc_te1550":("26c73f88ceb9b282f5da2ff4e1f4418bfbabb98a",7674,4),
    "ebeam_gc_te1550":("c25af553ffde8f7431659886abc9918379b278df",115348,1),
    "ebeam_y_1550":("f05fbc54dbfd33169540ad2245a2b3d103dceb72",12006,3),
}

def require(ok,message):
    if not ok: raise ValueError(message)

def git_blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    m=json.loads((BASE/"manifest.json").read_text())
    require(m["schema_version"]==1 and m["experiment"]=="OPA-LIB-001","manifest version")
    require(m["source_repository"]=="https://github.com/SiEPIC/SiEPIC_EBeam_PDK" and
            m["revision"]=="363fbb52eefa8669100499ab531d3fe7befc4867","source revision")
    lic=(BASE/"LICENSE.md").read_bytes()
    require(m["license"]=="MIT" and m["license_path"]==str((BASE/"LICENSE.md").relative_to(ROOT)) and
            git_blob(lic)==m["license_git_blob_sha1"]=="e5d16d71c2ff1f40c393ef23a2e01cb850aa9a4d","license identity")
    require(len(m["components"])==3 and {e["cell"] for e in m["components"]}==set(EXPECTED),"exact selection")
    require({p.name for p in (BASE/"gds").iterdir()}=={c+".gds" for c in EXPECTED},"unexpected GDS")
    registry=json.loads((ROOT/"components/registry.json").read_text())
    ids={e["id"] for e in registry["components"]}
    rows=[]
    for e in m["components"]:
        cell=e["cell"]; blob,size,pins=EXPECTED[cell]
        path=BASE/"gds"/(cell+".gds")
        require(e["path"]==str(path.relative_to(ROOT)) and e["source_path"]=="klayout/EBeam/gds/EBeam/"+cell+".gds","source paths")
        require(e["origin"]=="external_original" and e["geometry_status"]=="pending_ci" and
                e["measurement"] is None and e["drc"] is None and e["qualification"] is None and
                e["complex_s_parameters"]=="not_imported","evidence scope")
        require(e["related_registry_id"] is None or e["related_registry_id"] in ids,"related reference")
        raw=path.read_bytes()
        require(len(raw)==e["bytes"]==size and git_blob(raw)==e["git_blob_sha1"]==blob,"original GDS bytes")
        layout=kdb.Layout()
        layout.read(str(path))
        c=layout.cell(cell)
        require(c is not None,"missing named cell")
        require(math.isfinite(layout.dbu) and layout.dbu>0,"database unit")
        silicon=layout.find_layer(1,0)
        require(silicon is not None and silicon>=0,"missing silicon layer")
        region=kdb.Region(c.begin_shapes_rec(silicon))
        require(not region.is_empty(),"empty silicon geometry")
        bbox=region.bbox()
        require(bbox.width()>0 and bbox.height()>0,"nonpositive silicon bounding box")
        # The three pinned original GDS files encode optical pin text
        # on layer 1, TEXTTYPE 10 (KLayout layer 1/10).
        # Layer 68/0 contains component and model metadata, not pins.
        pin_layer=layout.find_layer(1,10)
        require(pin_layer is not None and pin_layer>=0,"missing optical pin text layer 1/10")
        labels=[s.text.string for s in c.shapes(pin_layer).each() if s.is_text()]
        expected=[f"opt{i}" for i in range(1,pins+1)]
        require(sorted(labels)==expected==e["optical_pin_labels"],"optical pin label identity")
        rows.append(dict(cell=cell,bytes=len(raw),git_blob_sha1=blob,sha256=sha(raw),
                         dbu_um=layout.dbu, silicon_bbox_um=[v*layout.dbu for v in (bbox.left,bbox.bottom,bbox.right,bbox.top)],
                         silicon_polygon_count=region.count(),pin_labels=sorted(labels),pin_text_layer="1/10",
                         layers=sorted([f"{layout.get_info(i).layer}/{layout.get_info(i).datatype}" for i in layout.layer_indices()]),
                         top_cells=sorted([x.name for x in layout.top_cells()]),
                         geometry_status="parsed_and_checked",drc=None,measurement=None,qualification=None))
    report=dict(experiment="OPA-LIB-001",source=m["source_repository"],revision=m["revision"],license_sha256=sha(lic),
                components=rows,checks=dict(original_bytes=True,license_identity=True,geometry=True,pin_labels=True,scope=True),
                limitations=["Geometry inspection only, not DRC, electromagnetic simulation, measured loss or fabrication qualification.",
                "Original SiEPIC revision differs from ubcpdk 3.3.0 references; no revision equivalence assumed.",
                "Pin text labels are not verified optical modal reference planes. Grating coupler has one on-chip pin; free-space/fiber interface not modeled.",
                "No S-parameter data imported; no process mixing."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
