"""Audit exact-revision public PDK numerical source leads without promoting measurement status."""
import csv,hashlib,io,json,math,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"components/comparison/lib005-source-discovery.json"
OUT=ROOT/"results/opa-lib-005-c"
def require(ok,msg):
 if not ok: raise ValueError(msg)
def blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def main():
 s=json.loads(SPEC.read_text())
 require(s["experiment"]=="OPA-LIB-005-C" and s["upstream_revision"]=="363fbb52eefa8669100499ab531d3fe7befc4867","source revision")
 local={}
 for k,x in s["local_sources"].items():
  b=(ROOT/x["path"]).read_bytes()
  require(blob(b)==x["git_blob_sha1"],"local "+k)
  local[k]=json.loads(b)
 upstream={}
 for x in s["upstream_sources"]:
  u=s["upstream_raw_base"]+urllib.parse.quote(x["path"],safe="/")
  with urllib.request.urlopen(u,timeout=30) as r: raw=r.read(1_000_001)
  require(len(raw)<=1_000_000 and blob(raw)==x["git_blob_sha1"],"upstream "+x["key"])
  upstream[x["key"]]=raw.decode("utf-8")
 require(len(s["upstream_sources"])==7 and len(local["si_manifest"]["components"])==3,"original paths")
 def lookup(key,params,filename):
  root=ET.fromstring(upstream[key])
  require(root.tag=="lumerical_lookup_table" and len(root.findall("association"))==9,"lookup combinations")
  found=[]
  for a in root.findall("association"):
   values={v.get("name"):float((v.text or "").strip()) for v in a.findall("./design/value")}
   name=a.find("./extracted/value").text
   if all(math.isclose(values[k],v,abs_tol=1e-13,rel_tol=0) for k,v in params.items()):found.append(name)
  require(found==[filename],"nominal LUT mapping")
 lookup("bdc_lookup",{"height":220e-9,"width":500e-9},"bdc_Thickness =220 width=500.sparam")
 lookup("gc_lookup",{"height":220e-9,"deltaw":0},"GC_TE1550_thickness=220 deltaw=0.txt")
 code=upstream["opics_model_registry"]
 require('class ebeam_bdc_te1550(componentModel)' in code and 'filename = "bdc_lookup_table.xml"' in code and 'filename = "GC_TE_lookup_table.xml"' in code,"upstream model registry")
 raw=upstream["bdc_model"].strip().splitlines()
 require(len(raw)==16*(2+51),"BDC lines")
 data={}
 for block in range(16):
  h=raw[block*53]
  m=re.fullmatch(r"\('port ([1-4])','TE',1,'port ([1-4])',1,'transmission'\)",h)
  require(m is not None and raw[block*53+1]=="(51,3)","BDC header")
  key=(int(m.group(1)),int(m.group(2)))
  require(key not in data,"duplicate S port")
  trace=[]
  for line in raw[block*53+2:block*53+53]:
   parts=[float(t) for t in line.split()]
   require(len(parts)==3 and all(map(math.isfinite,parts)) and parts[1]>=0,"BDC data")
   trace.append(parts)
  require(all(b[0]>a[0] for a,b in zip(trace,trace[1:])),"frequency direction")
  if data:require([r[0] for r in trace]==[r[0] for r in next(iter(data.values()))],"common freq grid")
  data[key]=trace
 require(set(data)=={(i,j) for i in range(1,5) for j in range(1,5)},"complete BDC ports")
 center=25
 sums={str(i):sum(data[(out,i)][center][1]**2 for out in range(1,5)) for i in range(1,5)}
 require(all(.9 <v<1.05 for v in sums.values()),"BDC magnitude sanity at center (not full passivity test)")
 gc=[[float(y) for y in row.split()] for row in upstream["gc_model"].splitlines() if row.strip()]
 require(len(gc)==100 and all(len(row)==9 and all(map(math.isfinite,row)) for row in gc),"GC 100x9")
 require(all(b[0]<a[0] for a,b in zip(gc,gc[1:])),"GC descending frequency")
 require("## Experimental Results" in upstream["bdc_docs"] and "TE – TBD" in upstream["bdc_docs"],"BDC qualitative documentation")
 require("Model uses S-Parameters generated for 9 variations" in upstream["gc_docs"],"GC model provenance ambiguous")
 require({x["cell"] for x in local["si_manifest"]["components"]}>={"ebeam_bdc_te1550","ebeam_gc_te1550"},"GDS identity")
 require(local["si_manifest"]["revision"]==s["upstream_revision"],"same source PDK revision")
 require(local["lnoi_manifest"]["revision"]=="d16db6a4882657feb1ce696c16c604ff6cb7ccfa","LNOI unchanged")
 require(all(x["calibration_eligible"] is False and x["independent_measured_raw_data_proven"] is False and x["model_exact_gds_geometry_proven"] is False for x in s["assessments"]),"no false calibration")
 require(next(x for x in s["assessments"] if x["id"]=="lnoi400-directional-coupler")["status"]=="already_imported_quarantined_nonpassive","quarantine")
 require(s["policy"]["exact_cell_calibrations"]==0 and s["policy"]["original_source_copied_into_repository"] is False,"read-only source audit")
 report={"experiment":s["experiment"],"source_revision":s["upstream_revision"],"verified_upstream_blobs":len(upstream),
         "bdc":{"ports":4,"blocks":len(data),"samples_per_block":51,"total_complex_entries":sum(map(len,data.values())),"nominal_height_nm":220,"nominal_width_nm":500,"center_frequency_hz":data[(1,1)][center][0],"center_input_power_sums":sums,"source_kind":"upstream PDK complex model; not independently confirmed raw measurement"},
         "gc":{"rows":len(gc),"columns":len(gc[0]),"nominal_height_nm":220,"nominal_deltaw_nm":0,"column_semantics":"unverified","source_kind":"upstream PDK numerical model; raw measurement provenance unverified"},
         "comparison_candidates":s["assessments"],"exact_cell_measurement_matches":0,
         "checks":{"source_file_git_identity":True,"lookup_default_parameters":True,"model_class_linkage":True,"complete_bdc_complex_model_inventory":True,"gc_numeric_structure":True,"source_docs_claim_scope":True,"no_exact_cell_calibration":True,"separate_tfln_and_quarantine":True},
         "limitations":["Retrieved source files read-only from a pinned revision; did not import source bytes or edit registry.","BDC source supports complex coefficients but not certified port reference planes, origin of numerical values, polarization calibration, passivity across band or exact GDS equivalence.","GC nine-column model semantics unverified and must not be silently interpreted as measured transmission.","Different SiEPIC ebeam_dc_te1550 is not the archived ebeam_bdc_te1550.","Missing experimental raw files, geometry/run identification and uncertainty prevents measured error comparison."]}
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
 with (OUT/"source-inventory.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["key","path","git_blob_sha1","kind"])
  for x in s["upstream_sources"]:w.writerow([x["key"],x["path"],x["git_blob_sha1"],x["kind"]])
 print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__":main()
