# OPA-G-005A — Process and measurement feasibility review

Status: proposed candidate coupon, **not approved for layout release, fabrication or tape-out**. This review closes the C3 planning handoff, not the physical feasibility gate. Keep CIR/LIB, OPA-M, OPA-W and the passive test-chip priorities unchanged.

## Evidence at the handoff

- [C2](../results/ci-originals/opa-g-004c2/45865605446-15140012141/result.json): selected max_min_125 passes finite-sample final and node gates; raw fails. 249 eligible rays, one coplanar exclusion. No hardware confidence guarantee.
- [C3A geometry](../results/ci-originals/opa-g-004c3a-geometry/45878908141-15145538173/result.json) and [FP64](../results/ci-originals/opa-g-004c3a-fp64/45880072521-15146368733/result.json): no recorded discrepancies. [Native CPU](../results/ci-originals/opa-g-004c3a-cpu/45881149631-15147700133/result.json): single-thread resident FP64 benchmark, four small synthetic scenes, shared CI CPU, no GPU.
- [Energy](../results/ci-originals/opa-g-004c3b-energy/45882481991-15148585656/result.json): 7,641/28,800 positive conditional budgets; 21,159 nonpositive. Two anisotropic selected-policy panels have 952/952 optical fallbacks. [Latency](../results/ci-originals/opa-g-004c3b-latency/45883999327-15149140081/result.json): 2,497/18,000 positive conditional budgets; 15,503 nonpositive. Distinct parameter grids, not probabilities or evidence of simultaneous energy and latency advantage.
- [G-003](OPA-G-003.md) defines a normalized four-MZM signed-field model with two serial products and coherent addition, followed by balanced reference readout. It is not the measured paper topology or an absolute receiver model.

Do not combine independent positive fractions or transfer energy assumed per side to a different rate/utilization without recalculating the static service window. A future joint study must use the same scene, repeat, policy, complete side count, physical service rate, elapsed time, power boundary and configuration; replace hypothetical values with measured bounds when available. Positive residual budgets cannot justify tape-out. Both negative and positive results remain archived.

## Candidate process and component reuse

Prefer a single-platform lnoi400 exploratory coupon as a starting hypothesis because the repository already has a pinned open geometry and partial model chain; **not a foundry selection or confirmed access**. Pin revision d16db6a4882657feb1ce696c16c604ff6cb7ccfa. See [registry](../components/registry.json), [LIB002](../components/external/Luxtelligence/lnoi400/README.md), [LIB003](../components/external/Luxtelligence/lnoi400/s_parameters/README.md) and [LAYOUT005](../results/opa-layout-005/result.json).

| Function | Existing evidence | Proposed use / unresolved issue |
|---|---|---|
| MZM | lnoi400-mzm; mzm_unbalanced, 5 mm, balanced arms, 2x2 MMI, heater, 4 optical and 4 electrical PCell ports | Single-device coupon first; confirm actual push-pull voltage/field convention, output-port phase, extinction, independent bias and RF termination. Four-port geometry is not the default 1x2 compact model. |
| MMI | lnoi400-mmi2x2; LIB003 sampled max singular value 0.992942; conditional complex simulated model | Candidate splitter/combiner; confirm port planes, normalization, phase, polarization and model correspondence. No continuous-band certification. |
| Directional coupler | LIB003 sampled max singular value 1.127581, 201/201 nonpassive | Quarantined; do not normalize, clip, use as gain or cascade in passive network. |
| Edge coupling | lnoi400-edge, double_linear_inverse_taper; 127 um pitch demonstrated in LAYOUT005 | Candidate external fiber interface; actual coupling loss, polarization, facet polish and alignment unknown. |
| Routes | LIB002 straight_rwg1000 and L_turn_bend generated references | Route length, crossing, bend loss, phase and crosstalk need validation; use same cross section or explicitly justified transitions. |
| EO phase reference | LIB002 5 mm EO phase shifter; EO002 generic 600 nm film model | Independent calibration structure; do not transplant EO002 1.863 V cm into lnoi400. LAYOUT005 compact-model Vpi=6.6 V at 5 mm, not measured. |
| Receiver, laser, LO, electronics | No revision-qualified integrated chain established by cited registry | External laser, LO branch, balanced detector/TIA and digitizer initially; characterize electrical and optical reference planes separately. No integrated laser or detector assumed. |

LAYOUT005 passed ten local geometry/reproducibility checks but no lnoi400 foundry DRC, RF impedance/velocity/termination validation or full optical chip simulation. LIB002 MZM generated bbox 7132.55 x 462 um excludes new assembly routes and external probe/fiber clearance. Four MZMs cannot be assumed to fit an MPW allocation from those dimensions alone. SiEPIC SOI DRC and published family measurements do not transfer to lnoi400. No cross-process layout or proprietary model publication without explicit interface and permission.

## Proposed staged coupon and logical interfaces

1. **005B reference cell**: one independently accessible 2x2 MZM with both output fields observable via calibrated interferometric/receiver measurement, RF input/output and slow heater bias. Straight/cutback, coupling loopback, MMI splitter/combiner and electrode open/short/thru (or facility-approved calibration standards) as separately accessible references. Confirm if process allows these structures.
2. **005C product arm**: two independently driven null-biased MZMs in series, monitor the intermediate and output signed fields. Test whether unused ports can be routed to monitored outputs or safely terminated using allowed process structures; no unspecified optical absorber or crossing.
3. **005D one complete side engine**: four signed modulators in two serial product branches, controlled relative phase, coherent addition, external LO and balanced readout. Include monitor ports and optical references. Logical operand mapping x1,x2,x3,x4 in [-1,1], intended output x1*x2+x3*x4; negative sign is encoded by input phase, not inferred from optical intensity. One side engine is not an entire ray-box accelerator. Electronic guard, two/six-side scheduling, minimum aggregation and compiled fallback remain off chip. Scaling lanes is deferred.
4. **005E release gate**: actual process stack and port mapping, verified layout connectivity, routing/phase budgets, RF pad and termination constraints, bias/thermal limits, package/facet/probe pitch, die/reticle allocation, allowed layers/keepouts, official DRC and provider review, measurement resources and license. No GDS release until relevant gates are satisfied.

The order is a proposed design sequence; a provider may require separate dies or a reduced scope. External reference arm must be phase-stable with respect to the signal. Distinguish intensity from field, optical loss from voltage calibration, and RF electrode ports from discrete electrical drive channels. Logical four operands require four independently controlled waveform streams; actual differential/GSG connections and return paths are to be derived from provider port geometry, not inferred from a logical count.

## Measurement protocol for G-006 planning (not execution)

Freeze instrument calibration, wavelength/polarization, reference planes, modulation/bias convention, detector bandwidth/noise, environmental conditions and raw time synchronization. Preserve failed runs and saturation/clipping. No inferred device bandwidth from paper headline or PDK DC model.

| Measurement | Required evidence |
|---|---|
| Passive transmission | Reference/cutback powers, uncertainty, wavelength sweep, polarization, route lengths, coupling vs propagation separation. |
| MZM transfer | Both outputs, bias sweep, signed field with calibrated reference, Vpi, extinction, imbalance, insertion loss, drift and repeatability; measured transfer vs simulated compact model. |
| RF | Calibrated S11/S21 at documented planes, termination, electrical-optical response, driver swing and frequency dependence; include de-embedding uncertainty. |
| Two-product and sum | Independent held-out operand vectors, sign reversal, zero cancellation, near-zero margins, unequal amplitude/phase, clipping and correlated noise. Record raw receiver values, not just classifications. |
| Confidence/fallback | Separate calibration and held-out geometry; freeze threshold before evaluation, report FP/FN separately, fallback by scenario/panel, and uncertainty. Require matched correctness before any acceleration claim; zero observed errors is not a guarantee. |
| System | Per correct delivered side/node/ray as applicable, all conversion and fallback work charged, idle and active power, laser/LO wall-plug, detector/TIA, clocks, controller, memory and transfer. Distinguish optical core, accelerator card and host-inclusive boundaries. Actual matched CPU/GPU baselines require measured energy and comparable workload. |

Do not extrapolate a single coupon's measured optical response to GPU, FPS or headset power. First quantify the absolute optical power and receiver noise budget; choose a statistically justified validation sample size and uncertainty method before physical testing.

## Access and decision register

| Gate | State | Evidence needed to change state |
|---|---|---|
| Public candidate PDK identity | documented | Pin exact revision throughout new layout. |
| Partial numerical MMI evidence | conditional | Validate same geometry/planes, loss, phase and operating interval. |
| Four-port active signed transfer | open | Device-specific complex model or calibrated measured response. |
| RF and packaging feasibility | open | Provider-confirmed pad/termination/impedance, available probes and fiber array, thermal and mechanical limits. |
| Laser/LO and receiver chain | open | Instrument inventory, calibration, power/noise and safety limits. |
| Fabrication access and funding | open | Written provider eligibility, scope, process, allocation, quote and access terms; PIXEurope/Myfab are leads, not confirmed routes. |
| Official DRC and release rights | open | Authorized rule deck and pass, provider review, license/redistribution and fabrication permission. |
| Joint energy/latency | open | Consistent parameter mapping and actual component measurements; no requirement that results be positive. |

**Decision:** proceed only with numerical/interface specification and provider-question preparation; physical fabrication remains blocked. No external contact made, no cost, allocation, equipment access or funding confirmed. If reference structures or RF/optical access are unavailable, reduce scope to passive/single-device characterization, document the reason and do not claim a four-MZM engine is feasible. A negative decision is valid.

## Next bounded step

005B: create a revision-pinned numerical signed-transfer and port-contract audit for the single MZM, using the existing geometry sidecar and model source. Verify the four-port versus default compact-model mismatch explicitly; report missing complex phases as missing, not synthetic measured data. Do not generate a tape-out layout or import new third-party bytes in this review.
