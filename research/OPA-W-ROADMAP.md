# OPA-W · Open Photonic Weight Memory

Date: 2026-11-24. Status: initial W-001A evidence review started; W-002A conditional experiment executed and archived; W-002B audit executed and archived; W-002C executed and archived; W-002D audit pending CI; no fabricated device or measured result. See [W-001A](OPA-W-001.md).

## Research question and scope

Can billions of AI model weights be stored in scalable, non-volatile optically accessible structures and used directly for optical computation without repeatedly transferring the weights to a separate processor? Test this hypothesis against digital and hybrid electronic/photonic baselines at matched model quality, throughput, latency, cost and system energy. A negative result is publishable.

Distinguish four functions:
- OPA-DELAY-001: transient optical pulse retention, not persistent memory.
- OPA-M: digital optical transport between electronic memory and accelerators; see [roadmap](OPA-M-ROADMAP.md) and [analytical baseline](OPA-M-001.md).
- OPA-W: persistent or infrequently rewritten weights, with optical readout or local matrix computation. Not general-purpose random-access RAM; electronic working memory remains the baseline for activations, KV cache and control.
- High-density optical archival storage: a separate candidate source tier (provisional OPA-S concept, not an active project); storage density alone does not establish random access, sustained bandwidth or inference suitability.

The near-term CIR, LIB and passive test-chip priorities remain unchanged. No purchase, external paid execution, fabrication or new experiment is authorized by this roadmap.

## Candidate architectures

Compare (A) digital weights streamed from electronic memory, (B) optically read nonvolatile digital or multilevel weights with separate compute, and (C) stationary weights directly participating in optical MVM. Include an electronic analog in-memory baseline where suitable evidence exists. Evaluate planar integrated waveguide arrays, free-space spatial arrays and tiled modules first; 3D stacking is a conditional extension, not a requirement or a demonstrated architecture.

Survey GST, GSSe and other phase-change materials, ferroelectrics, photoresponsive liquid crystals and 3D photosensitive media. Record write mechanism, measured optical contrast and complex response, loss, usable precision, retention, drift, endurance, read disturbance, temperature, integration constraints and availability. Do not conflate material voxel pitch with complete addressable cell footprint. Distinguish digital read integrity from analog MVM error.

For an intensity-encoded passive cell, P_out = T(w) P_in, with 0 <= T <= 1. A linear idealization is not a calibrated material model. Signed weights and inputs require differential paths or another explicit encoding and normalization. For y = W x, demonstrate independent weighting and summation; coherent fields can interfere and a detector does not generally sum arbitrary amplitudes linearly. Include splitter loss, wavelength response, detector saturation, noise and readout precision. Electronic nonlinearities and intermediate storage remain the baseline; no claim of fully optical transformer inference.

## Gated research phases

W-001A evidence review is active; W-002A conditional numerical screen executed and archived; [W-002B analysis](OPA-W-002B.md) and independent audit executed and archived; W-002C executed and archived; W-002D audit pending CI. Remaining gates are planned.

| Phase | Deliverable | Gate |
| --- | --- | --- |
| [OPA-W-001](OPA-W-001.md) · Materials and architecture evidence (initial review) | Primary-source comparison, requirements and reference baselines; reuse [component registry](../components/registry.json), MZI/CIR and OPA-M results. | Trace every parameter to a source or label it unknown/assumed; select a candidate on matched requirements, not density alone. |
| [OPA-W-002A](OPA-W-002A.md) · Multilevel cell (conditional numerical implementation) | Ideal and calibrated candidate transfer models; target 16 distinguishable states, with binary reference. | Report state distributions, read error, drift, write energy, retention and uncertainty; require a preregistered error target before claiming usable four-bit storage. |
| OPA-W-003 · Addressable array | Model a 16 × 16 array with selection, routing, write isolation and full physical footprint. | Quantify addressing failures, thermal/optical crosstalk, yield and peripheral overhead; compare against isolated-cell results. |
| OPA-W-004 · Parallel optical readout | Evaluate spatial, wavelength and time multiplexing with independent addressing. | Report sustained useful bandwidth, access latency, error rate, read energy and bottlenecks including detector/ADC capacity. |
| OPA-W-005 · Photonic in-memory MVM | Compare stored-weight optical multiplication and summation against NumPy/PyTorch and existing OPA MZI/CIR models, including signed encoding. | Paired seeds and inputs; report numerical error, effective precision, matched task quality, wall-plug energy and latency; no assumed advantage. |
| OPA-W-006 · 3D and modular architecture | Compare planar tiles, free-space modules and stacked layers with explicit layer selection, optical access, packaging and heat removal. | Demonstrate modeled independent access with realistic loss and crosstalk; do not extrapolate archival density into read bandwidth. |
| OPA-W-007 · Million-weight scaling | Resource and error scaling model; representative small AI workload and tiled MVM validation. | Separate simulated scale from extrapolated scale; account for routing, calibration, programming and utilization; compare electronic analog and digital baselines. |
| OPA-W-008 · Billion-weight feasibility | Dense and MoE scenarios at 7B, 70B and 405B; active versus total weights, KV cache, activations and inter-module traffic. | Bound area, module count, capacity, yield, latency, quality, energy/token and cost; identify infeasible regions and unresolved dependencies. No billion-weight hardware claim. |
| OPA-W-009 · Physical validation | Accessible process and small test coupon/array plan; open data, measurement protocol and cost/access assessment. | Confirm process compatibility, fabrication and lab access before design commitment; measure transmission states, retention, endurance, disturb, precision and MVM error before any hardware claim. |

Physical validation can be scoped earlier if access becomes available; a scaled architectural model is not a substitute for cell measurements. An inexpensive LED/mask/camera experiment may illustrate MVM but is not evidence of programmable nonvolatile memory.

## Scaling and system accounting

For N cells with b usable bits/cell, ideal capacity is N*b/8 bytes. A dense 70B checkpoint at four bits/weight requires at least 35 GB before metadata, redundancy and encoding overhead. For direct analog weights count independently programmable signed weight elements, not simply bits. Report pitch, complete cell and peripheral area, utilization, yield, packaging and access geometry separately. Read bandwidth depends on independent read lanes, useful bits/sample, sampling rate and overhead; do not infer it from optical carrier frequency. For streamed dense batch-one decode use the OPA-M traffic model; for local MVM account for activation traffic, tile reductions, routing, nonlinearity and KV cache. Compare equivalent service rather than equating optical propagation time with inference latency.

Reuse OPA-SYS accounting boundaries: wall-plug lasers, couplers, splitting, tuning, DAC/ADC, drivers, detectors/TIA, programming amortized over actual reuse, calibration, static/idle energy, digital control, host, cooling and memory. Report quality, context, batch, throughput, latency and energy/token jointly. Unknown parameters stay unknown; sensitivity sweeps are not measurements.

## Primary literature leads

Start by verifying full papers, experimental scope, measurement boundaries and licensing before extracting coefficients:
- Feldmann et al., [Parallel convolutional processing using an integrated photonic tensor core](https://doi.org/10.1038/s41586-020-03070-1), Nature (2021): integrated optical compute and nonvolatile weight candidate.
- [A 3D nanoscale optical disk memory with petabit capacity](https://doi.org/10.1038/s41586-023-06980-y), Nature (2024): storage-density lead, not a demonstrated inference memory.
- [Light-driven molecular reorientation for large-scale photonic in-memory computing](https://link.springer.com/article/10.1186/s43593-026-00141-0): molecular-memory lead; bibliographic details and reported capacity require verification.
- [Scaling strategies for photonic neural networks](https://www.nature.com/articles/s42254-026-00984-z): scaling review lead; verify metadata and scope.

No new literature-derived numeric performance claims are adopted in this planning document.

## Education and access

Browser teaching implementations: [Chip 13 (Photonic Weight Memory)](../web/chip13/README.md), [Chip 14 (Photonic In-Memory Computing)](../web/chip14/README.md) and [Chip 15 (Photonic Neural Network)](../web/chip15/README.md). They use illustrative models. The nine research phases retain their existing planned status and validation gates. Connect Chip 10 comb/WDM, Chip 11 optical logic (distinct from analog MVM), and Chip 12 interconnect where relevant. Keep teaching, analytical models, electromagnetic simulation, layout/DRC, fabrication and measured evidence separate.

Independent researchers can develop models, open benchmarks and reproducible layouts without owning a fabrication lab. Investigate shared infrastructure (Myfab, PIXEurope and suitable MPW services) and funding; eligibility, cost, material support and access are unverified. Preserve open documentation and do not redistribute restricted PDK data. Follow AGENTS.md, existing CI, provenance and archival conventions when a phase is explicitly authorized.

## Conditional multilevel results

[W-002B](OPA-W-002B.md) records the archived W-002A panel results and an independent confusion-matrix audit implementation. No empirical W-002 qualification or W-003 release is implied.

[W-002C](OPA-W-002C.md) registers paired reference-assisted drift compensation on independent held-out seeds. The W-002B original audit is archived; W-002C original results are archived; [W-002D](OPA-W-002D.md) documents trade-offs and registers a read-only audit with conditional cadence costs. No W-003 release or material qualification.
