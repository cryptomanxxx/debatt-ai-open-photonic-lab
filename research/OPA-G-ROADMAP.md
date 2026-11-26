# OPA-G — Open Photonic Graphics Accelerator

2026-11-26 · Proposed research track. No hardware or measured OPA-G performance. Existing CIR, LIB, OPA-M, OPA-W and passive test-chip priorities remain unchanged.

## Hypothesis and scope

Can an optical accelerator reduce energy or latency of bounding-volume hierarchy (BVH) ray-box intersection tests at matched correctness and workload, including conversion and memory overhead? This is not a full GPU, rasterizer or ray-tracing pipeline. Triangle intersection, traversal, shading, texture access and display remain electronic initially. A negative result is useful.

Primary evidence: Shiji Zhang et al., *Thin-film lithium niobate photonic circuit for ray tracing acceleration*, Nature Communications 16, 5938 (2025), https://doi.org/10.1038/s41467-025-61234-x. The authors demonstrate a TFLN core with four push-pull MZMs and coherent detection, reporting >100 GHz modulator bandwidth, 16 GS/s experimental signaling and 326 fJ/operation under their accounting. These figures are external, not OPA measurements, frame rates or headset-level power. Reconstruct their operation definition and energy boundary before comparison.

## Gated phases

| ID | Deliverable and acceptance gate |
|---|---|
| OPA-G-001 | Exact forward-ray/AABB slab reference, independent geometric cases and a reduced-precision comparator proxy. Cover parallel axes, inside origins, negative direction, tangency, behind-origin boxes, degeneracy and near-boundary errors. Publish seeded workloads, false negatives/positives separately, precision sweeps and CI provenance. No physical speed claim. |
| OPA-G-002 | Reproduce the paper's side-function algorithm from its supplementary derivation; compare against G-001 including coordinate conventions and 3D edge cases. Separate ideal math from optical encoding. |
| OPA-G-003 | Model four MZMs and coherent readout; sweep bias, nonlinearity, loss, phase drift, noise and comparator threshold. Require calibrated uncertainty and report missed intersections separately. |
| OPA-G-004 | Matched electronic CPU and GPU ray-box/BVH benchmarks with identical scene, rays and quality. Account for DMA, BVH memory, DAC, drivers, laser wall-plug, detector, TIA, comparator and idle power. Report throughput, p50/p95 latency and joules per delivered correct test; no assumed benefit. |
| OPA-G-005 | Candidate process-specific test coupon with reference structures and RF/optical interfaces. Reuse lnoi400 models and OPA-LAYOUT-005 where applicable; check registry, access, model validity and foundry DRC before tape-out. |
| OPA-G-006 | Bench measurement with calibrated electrical/optical planes, raw traces, uncertainty, drift, error counts and matched reference. |
| OPA-G-007 | Hybrid GPU/FPGA integration and BVH traversal with conservative fallback for ambiguous tests. Measure scene-level image errors, frame timing and whole-system energy before OPVR integration. |

All phases planned; no registry entry is implied by this document. Reuse CIR007/008 conversion accounting, EO001/002 and component library; no cross-process layout without explicit interface. See [OPVR](OPVR-ROADMAP.md) and [Chip 16](../web/chip16/README.md).

## Publication and access

Publish reproducible code, inputs, limitations and negative findings under repository policy. PIXEurope/Myfab are prospective access routes, not confirmed partners or funding. Validate packaging, RF and process feasibility before any physical commitment.
