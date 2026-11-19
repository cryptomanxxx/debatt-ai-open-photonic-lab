# OPA-CIR-002 — first external compact-model integration

CIR-001 [CI run 44511534366](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44511534366) passed all 20 checks; maximum programmed target error 1.2124e-15. Build on that solver.

## Source and scope

Use the exact existing lnoi400 revision [d16db6a](https://github.com/Luxtelligence/lxt_pdk_gf/tree/d16db6a4882657feb1ce696c16c604ff6cb7ccfa), MIT [license](https://github.com/Luxtelligence/lxt_pdk_gf/blob/d16db6a4882657feb1ce696c16c604ff6cb7ccfa/LICENSE), [model](https://github.com/Luxtelligence/lxt_pdk_gf/blob/d16db6a4882657feb1ce696c16c604ff6cb7ccfa/lnoi400/models.py), [data](https://github.com/Luxtelligence/lxt_pdk_gf/blob/d16db6a4882657feb1ce696c16c604ff6cb7ccfa/lnoi400/data/mmi_2x2_optimized_1550.json) and [helper](https://github.com/Luxtelligence/lxt_pdk_gf/blob/d16db6a4882657feb1ce696c16c604ff6cb7ccfa/_utils/models.py). Data explicitly describe FDTD polynomial fit around 1550 nm, not measurements. No vendoring; install existing Python 3.12 lock with SAX 0.16.14; JAX CPU x64. Dedicated workflow follows existing layout PDK setup, rather than modifying the Meep lock or experiment selector. 

The model specifies complex bar o1-o4/o2-o3 and cross o1-o3/o2-o4 plus same-side reflection, reciprocity. Use native port names, power-normalized wave assumption and phase as supplied; no claim of independently verified modal normalization, polarization, reference planes or fit validity bounds. Explore 1540–1560 nm only (21 points), not an asserted rated range. The default layout is 5 µm MMI width, 76.5 µm length, 25 µm tapers, xs_rwg1000. Do not transfer its model to altered geometry or another process.

## Tests before execution

1. Evaluate upstream model and independently reconstruct complex entries using NumPy polynomial evaluation of the pinned data. Check all 16 entries, finite scalar values and reciprocity, error <=1e-10.
2. Connect two upstream 2x2 MMIs using upstream straight_rwg1000 models (bottom 100 µm; top 100, 100.25, 110 µm). Compare full four-port complex S with independent SAX circuit assembly for 63 cases. Includes reflections; no hand-built 50:50 replacement. This is a model-level MZI reference, not the geometry or RF model of LAYOUT-005. Note upstream mzm_unbalanced compact model internally uses 1x2 MMIs, not the layout's 2x2 splitters; do not treat these as equivalent.
3. Report maximum singular values and passivity excess of component and circuit. Numerical agreement gates CI; physical eligibility is a separate explicit gate. If nonpassive, preserve unmodified data and block promotion; no clipping. Require full grid and phase-sensitive output.
4. Archive provenance hashes, package versions, sweep and report; CI must pass before any success claim. Registry remains reference-only until evidence is reviewed.

## Next

After numerical verification and passivity review, integrate the model into a more complete PDK MZI with actual routing lengths, then mesh. No new FDTD optimization, no measured hardware claim. 

## Recorded results

Run [44513345216](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44513345216): 5/5 checks passed, 63 cases; polynomial and reciprocity error zero, SAX maximum error 3.4989384658674724e-14, MMI and circuit passivity excess zero, passivity_eligible true. Artifact 14522744683, ZIP SHA256 6272dc7414fa970ed7e8fe6f995a0a9c983c6660649bd8cc161695ee6c6bad10. Full artifact not yet permanently archived. Numerical eligibility only. Proceed to [CIR-003](OPA-CIR-003.md).
