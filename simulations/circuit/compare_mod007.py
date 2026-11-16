"""Compare scientific records independent of shard ordering."""
import json
import math
import sys

def compare(a,b):
    for key in ("config","assumptions","checks"):
        if a[key] != b[key]:
            raise ValueError(f"Mismatch: {key}")
    for key in ("rows","curves","comparisons","layer_errors"):
        def identity(row):
            return tuple(row.get(k) for k in ("seed","depth","tile_size","scenario","method","calibration","step","layer"))
        def index(rows):
            result = {identity(r):r for r in rows}
            if len(result) != len(rows):
                raise ValueError("Duplicate scientific record")
            return result
        left,right = index(a[key]),index(b[key])
        if left.keys() != right.keys():
            raise ValueError(f"Record identity mismatch: {key}")
        for ident,row in left.items():
            other = right[ident]
            if row.keys() != other.keys():
                raise ValueError("Record fields differ")
            for k,v in row.items():
                w = other[k]
                if isinstance(v,float):
                    if not isinstance(w,(int,float)) or not math.isclose(v,w,rel_tol=1e-7,abs_tol=1e-9):
                        raise ValueError(f"Numeric mismatch: {key} {ident} {k}: {v} vs {w}")
                elif v != w:
                    raise ValueError(f"Exact mismatch: {key} {ident} {k}")
    print("All scientific records match archived serial reference")

if __name__ == "__main__":
    with open(sys.argv[1]) as a, open(sys.argv[2]) as b:
        compare(json.load(a),json.load(b))
