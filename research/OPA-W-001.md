# OPA-W-001A — Material evidence and OPA-M interface requirements

2026-11-26. Initial evidence review, not a calibrated model or fabrication decision. The [OPA-W roadmap](OPA-W-ROADMAP.md) and [OPA-M roadmap](OPA-M-ROADMAP.md) remain independent research tracks. This step establishes a candidate for numerical screening, not a completed W-001 gate. Existing CIR/LIB and passive test-chip priorities remain unchanged.

## Primary evidence comparison

| Device and source | Observed external evidence | Limits and relevance |
|---|---|---|
| GST optical PCM, Ríos et al., Nature Photonics 9, 725–732 (2015), [DOI](https://doi.org/10.1038/nphoton.2015.182) | Abstract reports eight levels, optical programming/readout, minimum reported switching energy 13.4 pJ, wavelength addressing. | Publisher abstract inspected; full methods and energy boundary not audited. Useful optical-write comparator, not four-bit qualification. |
| GSSe electrically programmed PCM, Meng et al., Light: Science & Applications (2023), [DOI](https://doi.org/10.1038/s41377-023-01213-3) | Fig. 2a: 16 transmission states and 0.12 dB insertion loss in fully amorphous state for the multi-heater four-bit device. Fig. 2d: approximately 500,000 write/reset cycles in a two-state endurance test. Fig. 4c: separate asymmetric heater design demonstrates six states. | Full publisher HTML relevant sections inspected. Do not assign 16 states to the asymmetric two-heater cell or interpret endurance as four-bit retention. Electrical heating, optical read; neither minimum footprint nor all-optical write established. |
| BaTiO3 ferroelectric, Geler-Kremer et al., Nature Photonics 16, 491–497 (2022), [DOI](https://doi.org/10.1038/s41566-022-01003-0) | Abstract reports eight stable phase states, electrical programming, nondestructive optical readout, minimum switching energy 4.6 pJ. | Abstract only; [correction](https://doi.org/10.1038/s41566-022-01041-8) requires audit before quantitative reuse. Phase encoding needs interferometric readout; not a direct intensity-cell equivalent. |
| PCM tensor core, Feldmann et al., Nature 589, 52–58 (2021), [DOI](https://doi.org/10.1038/s41586-020-03070-1) | Experimental PCM weight array and microcomb-based convolution. | Abstract/bibliographic evidence only; [correction](https://doi.org/10.1038/s41586-021-03216-9) noted. Does not demonstrate billion-weight storage or full LLM inference. |

Other roadmap leads (photosensitive media, liquid crystals, 3D archival storage) remain unreviewed; no numerical parameters adopted. Values are source-specific reported results, not OPA measurements. No full-text rights or permission to redistribute figures/data inferred. No direct energy ranking: minimum pulse energy, delivered electrical energy and wall-plug system energy have different boundaries. No assumption of equal precision, temperature, write speed, retention interval or footprint.

## Candidate choice and missing evidence

Prioritize GSSe multi-heater intensity memory for the first conditional W-002 numerical screen because the reported architecture matches the 16-state target and the passive intensity interface. Keep GST optical-write and BTO phase-memory as independent comparators. This is a research ordering, not a foundry choice. Do not mix the GSSe cell with lnoi400 or SiEPIC layouts without process compatibility evidence. The [component registry](../components/registry.json) contains reusable optical routing, MMI, modulator and ideal MZI references but no qualified programmable nonvolatile weight cell. No new component admitted.

Before calibration obtain state-by-state transmission distributions (including uncertainty, repeated programming and device variation), wavelength/polarization, write energy/time and boundary, elapsed retention conditions, read disturbance, four-bit endurance, full layout/driver area and process constraints. Missing quantities remain unknown. Published 0.12 dB is a single state of one architecture, not per-state loss or a complete link budget. Do not derive evenly spaced measured levels from 16 reported states. Optical writing remains a distinct candidate to investigate, not a prerequisite for optical readout.

## Common OPA-W / OPA-M comparison contract

Use the archived [M-001 report](../results/opa-m-001/result.json) and [methods](OPA-M-001.md) for frozen warm batch-one dense/MoE traffic scenarios. Use the same checkpoint, precision, context, active weights and output quality for all comparisons. Separate cold programming/loading, prefill, warm decode and reprogramming. Three architectures:

- A: electronic memory, electrical or optical digital transport, electronic MVM (M-001 reference).
- B: optically read persistent storage, digital recovery and separate electronic MVM; readout and conversion are not free.
- C: stationary optical weights with local MVM; only activation/partial-sum/control traffic crosses the interface if all needed weights are resident. Missing weights or tiles still require loading, programming and transfer. Electronic KV, activation storage and nonlinearity remain baseline.

At N logical weights and b bits per weight, packed payload is N*b/8 bytes before metadata. For 70B dense four-bit, 35 GB decimal; a 16-level cell needs one element per unsigned four-bit weight in the ideal packing limit. Signed differential MVM with two independently programmed cells per weight needs 140B physical elements before redundancy; it is not equivalent to a 35 GB addressable digital memory. Count total stored and active accessed weights separately for MoE. Never subtract weight bytes from M-001's link traffic without verifying residency and read/overfetch semantics. Preserve host, SSD, ingress, local memory and compute bottlenecks.

For digital optical read, useful rate = independent lanes * samples/s * useful bits/sample * payload efficiency. For local MVM define tile size, input/output streams, partial sum reductions, effective precision and active utilization; optical carrier frequency is not throughput. Charge programming energy amortized over actual reuse, write verification, optical source wall-plug, splitting, detector/TIA/ADC, calibration, controller, transport, KV and activation costs. Compare both latency and J/token at matched task quality, not just optical-core energy. Unknown parameters stay unknown. No physical advantage inferred.

## Next bounded experiment: W-002A conditional multilevel screen

Prerequisite for empirical calibration is still open; begin only an explicitly hypothetical reference model. Compare binary and 16-level intensity codebooks at the same normalized full-scale interval with separate programming variation, common drift and read noise. Freeze calibration thresholds on an independent split, report state confusion matrices, symbol and bit errors (define bit mapping), worst state, clipping and uncertainty over held-out repeated writes/read conditions. Include deterministic ideal and zero-margin cases; preregister a numerical error target, not a physical reliability claim. Distinguish shared drift across reads from independent receiver noise. Preserve failed scientific outcomes. No empirical device distribution inferred from the literature summaries.

Before W-003, require a candidate with a documented error/retention envelope and obtain addressing/routing/crosstalk constraints; before physical commitment require written process and measurement access. PIXEurope/Myfab are possible access routes, not confirmed fabrication partners. No contact or purchase made in this step.
