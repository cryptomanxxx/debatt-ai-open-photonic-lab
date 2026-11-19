# OPA-CIR-001–008 — Final Research Report

**Debatt-AI Open Photonic Lab | 2026-11-19 | Numerical circuit and system research**

## Executive summary and closure decision

The CIR phase established a reproducible complex scattering solver, integrated pinned lnoi400 compact models, constructed a calibrated 4×4 unitary mesh and a general 4×4 SVD layer, tested frozen WDM weights, added a conditional coherent I/Q interface and integrated a partial power budget. All eight original runs passed 63/63 numerical checks in total (20+5+5+5+6+5+7+10). These are different checks, not independent statistical observations. The archive preserves negative as well as positive results. No chip has been fabricated or measured in this phase.

**Recommended frozen reference:** one 1550 nm carrier, two 4×4 meshes, four ideal singular-value attenuators, nominal 8-bit I/Q DAC and ADC, maximum aggregate core launch 1 mW, LO 1 mW per output hybrid. Worst relative held-out vector error across five nonzero targets is 4.8121% (CIR007 pooled over vectors and noise repeats, not maximum individual-vector error). The nominal partial cooled accounting proxy is 0.702324 W at assumed 10 Gvector/s. Neither physical feasibility nor speed, ENOB, total system power, AI accuracy or comparative advantage has been established. WDM with the frozen mesh failed the provisional multichannel screen. Close the original numbered CIR001–008 series after this report audit; future improvements require a separate bounded hypothesis and new identifiers. Do not silently change the archived baseline.

## Evidence ledger

Each link points to the exact archived report, with original ZIP and provenance in its parent directory. Numerical success is not a physical validation gate.

| Experiment | Scope and result | Original CI |
|---|---|---|
| [CIR001](evidence/opa-cir/opa-cir-001/files/result.json) | 128 seeded trials; 20 checks; programmed-target maximum complex error 1.21238e-15; analytical reflection and invalid-input controls. | [44511534366](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44511534366) |
| [CIR002](evidence/opa-cir/opa-cir-002/files/result.json) | 63 cases; native MMI FDTD polynomial and SAX connection agreement, max network discrepancy 3.49894e-14; 1540–1560 nm exploratory interval. | [44513345216](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44513345216) |
| [CIR003](evidence/opa-cir/opa-cir-003/files/result.json) | 330 cases; four-port EO MZI with 5 mm phase sections and 700 µm heater section; SAX discrepancy 1.60821e-11; central in1→out1 modeled power range 0.0000174957–0.929768. | [44514440625](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44514440625) |
| [CIR004](evidence/opa-cir/opa-cir-004/files/result.json) | Eight unitary targets; 6 MZIs/16 phase parameters; median shape error 87.5578% → 2.4058%; median optical transmission 73.4050%. | [44515459851](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44515459851) |
| [CIR005](evidence/opa-cir/opa-cir-005/files/result.json) | Six matrices including zero; five nonzero median shape error 77.8723% → 2.7171%, max 3.9915%, median held-out MVM 2.8806%; median mean transmission 19.4049%. | [44516404174](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44516404174) |
| [CIR006](evidence/opa-cir/opa-cir-006/files/result.json) | 255 logical cases, 15 windows; exact center replay; only one carrier passed both 5% matrix screens across all targets. | [44517897095](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44517897095) |
| [CIR007](evidence/opa-cir/opa-cir-007/files/result.json) | 180 groups; four of 36 interface settings passed; no clipping in passing groups; ideal coherent hybrid and conditional sampled noise. | [44523102737](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44523102737) |
| [CIR008](evidence/opa-cir/opa-cir-008/files/result.json) | 96 accounting scenarios, four inherited eligible settings; nominal partial proxy 0.702324 W; no additional accuracy experiment. | [44526090427](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44526090427) |

## Optical model and evidence hierarchy

CIR001 solves power-normalized complex scattering networks with explicit ports and internal feedback. CIR002–006 use the pinned [Luxtelligence lnoi400 source](https://github.com/Luxtelligence/lxt_pdk_gf/tree/d16db6a4882657feb1ce696c16c604ff6cb7ccfa), including upstream FDTD-derived MMI polynomial data and EO/TO compact models. CIR002 compares native polynomial and SAX evaluations, not independent fabrication measurements. Native reference planes, compatible modes and dispersion are assumed. The explored band is not a certified validity interval. No process corners, temperature, polarization or geometry extraction audit. LAYOUT005 is a geometry reference, not a verified physical equivalent of the whole mesh.

SVD uses W = U diag(s) V†; optical sequence V† → normalized singular amplitudes s/max(s) → U. Six MZIs in each mesh, 24 MMI total, 32 phase-control parameters (not necessarily 32 physical electrodes), four ideal reciprocal reflectionless attenuators. Independent bounded mesh fits with common complex output normalization, no joint SVD optimization. Scale and gain are electronic/coherent assumptions, not optical amplification. Median transmission is a power ratio that includes intended attenuation; it is not a pure excess insertion-loss metric. The five nonzero cases are identity, rank one, signed diagonal, seeded dense real and dense complex; zero is tested separately in CIR005. Full S includes reflections. All reported passivity eligibility gates through CIR006 passed, not proof of fabricated passivity.

## WDM: a negative result with a clear engineering requirement

Frozen voltages and attenuation; same-weight parallel input vectors on equal-frequency lines, not wavelength-specific independent weights. 25/50/100 GHz spacing, centered windows of 1/3/5/9/17 channels, ideal sources, no physical comb or mux. Worst relative Frobenius matrix error even after independent scalar complex gain per channel:

| Spacing | 1 channel | 3 | 5 | 9 | 17 |
|---|---:|---:|---:|---:|---:|
| 25 GHz | 3.9915% | 13.0657% | 24.9476% | 47.3219% | 79.5329% |
| 50 GHz | 3.9915% | 24.9476% | 47.3219% | 79.5329% | 93.7239% |
| 100 GHz | 3.9915% | 47.3219% | 79.5329% | 93.7239% | 98.5841% |

At 25 GHz/3 carriers the fixed central gain gives 18.8709%; individual gain cannot restore matrix shape. The center reproduced CIR005 exactly. Only centered single-channel windows passed across all five targets. This does not establish impossibility of WDM, maximum continuous usable bandwidth or a specific culprit. Differential phase/group-delay imbalance, including unequal optical lengths and omitted bypass routing, is a hypothesis to isolate, not a demonstrated cause. A 5% matrix screen is not a neural-network accuracy or ENOB guarantee. No WDM throughput credited in CIR008.

## Coherent interface and frozen system baseline

Four complex input fields, eight real DAC/driver lanes, four coherent 90° hybrids, 16 photodiodes, eight balanced I/Q TIA pairs and eight ADC lanes. CIR007 assumes an ideal linear field encoder, external phase-locked LO, known per-vector normalization/headroom, frozen complex gain, static quantizers, Gaussian shot/TIA noise, 0.9 A/W responsivity and 7 GHz rectangular noise bandwidth. Five targets × 32 fixed held-out vectors × 64 noise repeats per configuration, 180 groups total; noise repeats are paired across settings. Relative error is the norm of pooled residuals divided by norm of repeated reference, worst across five targets. Not independent validation of trained AI, actual ENOB, BER, RF or rate. No RIN, imbalance, saturation, clock jitter, phase drift, physical encoder or output coupling model.

| DAC/ADC nominal bits | Max signal launch mW | LO mW per output | Worst relative vector error | Nominal partial cooled W | pJ/complex MAC (conditional) |
|---:|---:|---:|---:|---:|---:|
| 8 | 1 | 1 | 4.8121% | 0.702324 | 4.38953 |
| 8 | 1 | 3 | 4.7605% | 0.776928 | 4.85580 |
| 10 | 1 | 1 | 4.2979% | 1.829324 | 11.43328 |
| 10 | 1 | 3 | 4.1931% | 1.903928 | 11.89955 |

All four passed the 5% provisional worst-target pooled-error screen and no ADC clipping in the sample. The 8-bit 1 mW LO baseline minimizes nominal resolution and LO among tested passing settings, not a global optimum. Max modeled diode optical power 0.674708 mW for baseline; actual detector limits unknown. Only 0.1879 percentage points of error margin relative to 5%; do not assume extra routing loss, drift or quantization errors are tolerable. The 10-bit converter model scales both ADC and DAC energy by 2^(bits-8), an assumption rather than actual hardware comparison.

## Partial system accounting, not a benchmark

CIR008 uses historical [AG003 parameter assumptions](../antigravity/reproduction/AG-PHOTONIC-003/original/params.py), not selected devices. At assumed 10 Gvector/s and one 4×4 complex MVM per vector, 16 complex MAC/vector and 160 Gcomplex MAC/s are arithmetic scenarios, not demonstrated latency or throughput; no real TOPS conversion. Baseline fixed equal signal split, 8 TIA front ends, SRAM, nominal parameters. Source optical signal 11.536126 mW + LO 6.487240 mW = 18.023366 mW upstream, max core entrance signal 1 mW and total LO 4 mW at hybrids. Four equal signal branches reserve full-scale component power, hence 4× signal provisioning; LO fanout counted once. Core loss is already reflected in detected signal; do not charge it again. Mean detected signal across targets spans 0.146410–0.536305 mW in this interface sample (not the CIR005 basis-vector transmission statistic).

| Budget term | W |
|---|---:|
| Laser/LO electrical proxy | 0.0901168320 |
| DAC | 0.120000 |
| ADC | 0.200000 |
| Input drivers | 0.080000 |
| TIA | 0.040000 |
| Calibration proxy | 0.000600 |
| Packed vector SRAM traffic | 0.080000 |
| Partial subtotal | 0.6107168320 |
| Assumed 15% cooling/PSU uplift | 0.0916075248 |
| Partial cooled proxy | 0.7023243568 |

70.23243568 pJ/vector, 4.38952723 pJ/complex MAC at assumed rate. DAC+ADC account for 45.56% of cooled proxy or 52.40% of subtotal. Nominal HBM payload substitution increases 0.702324 W to 1.346324 W with no accuracy change in this accounting-only comparison. The 96 scenarios span 0.240660–7.432175 W, deterministic joint assumption changes, not a probability interval or validated hardware envelope. Adaptive signal allocation is an optimistic bound on source provisioning, not a built device. Excludes actual phase/attenuator hold power, output and routing loss, physical IQ and LO distribution/phase tracking, digital normalization/complex correction/activation, weight programming, calibration probes, metadata, clocks, idle, host and packaging. Partial proxy is not a complete system total or rigorous lower bound. No measured energy/speed advantage over GPU or other electronics.

## Prioritized research handoff (proposed, not new experiment authorization)

1. **Physical passive reference and model-to-layout closure.** Begin with the existing process-specific MMI/MZI and passive test structures rather than a full accelerator tape-out. Verify access to process rules, layer stack, ports and test equipment; choose foundry/process only after access is confirmed. Build geometry-extracted matched path lengths including bypasses, bends, tapers and facet interfaces. Compare full complex S and loss to pinned models; specify reference planes and uncertainty. DRC and measured calibration are separate gates. Use external laser/detection for early passive tests; no integrated laser required. Retain OPA-FAB-001 intent, subject to facility feasibility.
2. **Replace ideal attenuation and encoding/readout.** Search existing compatible PDK components first; demonstrate an attenuation implementation including dump ports, reflections, loss, control power and range. Select realistic I/Q modulation, coherent hybrid, photodiodes/TIA and converter specifications; measure or obtain calibrated transfer, noise, phase and saturation limits. Re-run the frozen 1550 nm accuracy screen with independent validation and all additional losses; no retrospective promotion. Determine real achievable sample rate and margins. This is a prerequisite for an integrated SVD chip, not a reason to delay simple passive test structures.
3. **WDM root-cause and architectural remediation.** Use one bounded controlled attribution study: replace MMI/EO/TO dispersion and path-length terms one at a time, include geometry-correct bypasses, compare center-preserving controls and joint multichannel calibration. Predefine 3 carriers at 25 GHz as an initial engineering target, same weights, frozen settings and <=5% worst-target matrix error; keep failures. Do not solve the problem by pretending each wavelength has independently tunable weights or by adding a comb before the compute network is ready. Consider alternative broadband PDK cells or architecture only when a bottleneck is identified.
4. **System economics and workload.** Replace AG003 energy proxies with actual device/driver/bias/memory measurements or documented specifications at matched accuracy, rate and boundary. Investigate converter sharing, precision allocation and local data reuse; no assumed savings. Reuse MOD007 for electronic activation and multilayer validation, NL021 only if a distinct need emerges. Compare electronic baseline under matched workload, accuracy and end-to-end boundary. No training acceleration claim.

No ordering implies that all items must be completed serially before the first passive chip. Facility access, time, costs and device availability are open. Maintain reuse-first library policy; develop custom components only for demonstrated gaps. Freeze CIR001–008 as an auditable reference; do not pursue an unbounded CIR009 series. Next research phase requires its own scope and decision.

## Reproducibility and archive

[Archive manifest](cir_archive_manifest.json) pins all eight original run IDs, artifact IDs, byte counts, SHA-256 and commits. [Archive workflow run 44531822192](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44531822192), [PR221](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/221), archive merge 629aa6bbf401c109a9ae46f440cafb4799d88854: 41 files, 3,222,234 bytes, original ZIPs plus exact members and provenance. CRC, archive safety, report checks, source linkage and Git-staged byte identity verified. [Permanent audit workflow](../.github/workflows/opa-cir-evidence-audit.yml) reads Git bytes without relying on expiring Actions artifacts. The report's independent summary audit reuses the archive verifier, checks the 63 gates, WDM outcome, accuracy admissions and accounting headline values against the archived reports without re-executing simulations. See [audit script](analyze_cir_final.py). No original evidence was modified.
