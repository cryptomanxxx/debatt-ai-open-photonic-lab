"""Parity-resolved cross-check using the OPA-COUPLER-001 Python MPB approach.

Unlike the original Scheme model, solve each symmetry sector separately.
Rotate propagation to x and use the laboratory's TE parity conventions.
"""
import json
import math
from pathlib import Path
import sys
import meep as mp
from meep import mpb

HERE = Path(__file__).resolve().parent
WL = 1.55
WIDTH, HEIGHT = 0.45, 0.22
N_CORE, N_CLAD = 3.48, 1.44

def neff(gap, parity, res, cell):
    offset = (WIDTH + gap)/2
    geometry = [mp.Block(center=mp.Vector3(0,s*offset,0),
                         size=mp.Vector3(mp.inf,WIDTH,HEIGHT),
                         material=mp.Medium(index=N_CORE)) for s in (-1,1)]
    ms = mpb.ModeSolver(geometry_lattice=mp.Lattice(size=mp.Vector3(0,*cell)),
                        geometry=geometry, default_material=mp.Medium(index=N_CLAD),
                        resolution=res, num_bands=1, mesh_size=3)
    f = 1/WL
    k = ms.find_k(parity,f,1,1,mp.Vector3(1),1e-10,f*2.4,f*N_CLAD,f*N_CORE)
    return float(k[0]/f)

def solve(gap_nm,res,cell=(5,3)):
    e = neff(gap_nm/1000,mp.EVEN_Z+mp.ODD_Y,res,cell)
    o = neff(gap_nm/1000,mp.EVEN_Z+mp.EVEN_Y,res,cell)
    if not all(map(math.isfinite,(e,o))) or not N_CLAD < o < e < N_CORE:
        raise ValueError("Invalid guided TE supermode pair")
    return dict(gap_nm=gap_nm,resolution=res,cell_um=cell,neff_even=e,neff_odd=o,
                Lc_um=WL/(2*(e-o)),L50_um=WL/(4*(e-o)))

def main():
    ref=json.loads((HERE/"reference.json").read_text())
    rows=[]
    for gap,e,o,l in ref["sweep"]:
        r=solve(gap,96)
        r["reference"]=dict(neff_even=e,neff_odd=o,L50_um=l)
        r["relative_error"]=abs(r["L50_um"]/l-1)
        r["passed"]=r["relative_error"]<=0.01 and abs(r["neff_even"]-e)<=0.0002 and abs(r["neff_odd"]-o)<=0.0002
        rows.append(r)
        print(json.dumps(r),flush=True)
    # Grid-aligned refinements: all dimensions are integer pixels at 200/400.
    refinements=[solve(200,res) for res in (100,200,400)]
    change=abs(refinements[-1]["L50_um"]/refinements[-2]["L50_um"]-1)
    cell=solve(200,200,(6,4))
    cell_change=abs(cell["L50_um"]/refinements[1]["L50_um"]-1)
    passed=all(r["passed"] for r in rows) and change<=0.01 and cell_change<=0.005
    report=dict(method="parity-resolved Python MPB",meep_version=mp.__version__,
                geometry=dict(width_um=WIDTH,height_um=HEIGHT,wavelength_um=WL,n_core=N_CORE,n_clad=N_CLAD),
                matched=rows,refinements=refinements,refinement_relative_change=change,
                cell_check=cell,cell_relative_change=cell_change,passed=passed)
    Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report),flush=True)
    return 0 if passed else 1

if __name__=="__main__":
    sys.exit(main())
