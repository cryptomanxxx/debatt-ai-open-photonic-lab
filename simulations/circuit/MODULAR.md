# OPA-MOD – Modular photonic computing

Research question: can tiled photonic processors improve accuracy and optical power budgets for the same workload, after electronic and communication overhead is accounted for?

| Experiment | Scope |
|---|---|
| OPA-MOD-001 | Ideal mathematical equivalence |
| OPA-MOD-002 | Optical loss and power budgets (planned) |
| OPA-MOD-003 | Component errors (planned) |
| OPA-MOD-004 | Calibration (planned) |
| OPA-MOD-005 | Communication and energy (planned) |
| OPA-MOD-006 | Training (planned) |

MOD-001 compares a digital reference with SVD and QR factor models for a 128×128 matrix, using tile sizes 128, 64, 32, 16 and 8. Each tile implements its actual matrix block, with signed coherent field readout and electronic accumulation. SVD uses two unitary meshes, normalized attenuators and electronic gain; QR uses one mesh and electronic triangular multiplication. The adjoint reverses these mathematical operations. Explicit Clements reconstruction is checked separately at sizes 4 and 8; large-size comparisons are factor-level only.

Run from repository root: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/modular_equivalence_v001.py`. CI uses the registered locked environment and publishes the result artifact. This experiment establishes numerical equivalence only, not physical advantage. Results are not archived as CI provenance until an actual run is available.
