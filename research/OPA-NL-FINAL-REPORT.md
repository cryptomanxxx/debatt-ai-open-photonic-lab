# OPA-NL final research report — NL001–NL021

Date: 2026-11-19. Phase closure report; independent archive reanalysis is required to pass the accompanying PR audit before merge. No new experiment, fitting or test draw is authorized. The current nonlinear phase ends here; OPA-CIR is the next main research priority.

## Executive result

The frozen NL019 Margin16 Low readout at LO 3 mW, 120 GHz modeled electrical cutoff, C2, 42 ps on, zero gap and 5 ps response passed the preregistered NL021 primary endpoint on two independent test-draw panels and both drives. Worst combined correct-decision fraction 1970/2048 (96.19140625%), above 1967/2048 required. This is 23.8095 Gsymbol/s modeled cadence, not physical throughput or a measured BER. LO 2 mW secondary failed the 96% threshold by one decision (1966/2048); it passed the inherited 95% gate. No NL022, speed promotion or post-hoc replacement of the primary.

## Evidence ledger

Each linked result is the archived report, not a hardware validation. All 21 reports list zero implementation failures; scientific outcomes differ.

| Study | Main finding or lesson |
|---|---|
| [NL001](../results/opa-nl-001/result.json) | Static saturable absorber in synthetic multilayer task failed nominal scientific hypothesis; do not confuse nonlinear transfer with useful activation. |
| [NL002](../results/opa-nl-002/result.json) | Signed coherent XOR construction; absorber and softsat nominal gates failed despite perfect nominal classification. |
| [NL003](../results/opa-nl-003/result.json) | Conditional static coherent receiver; absorber cleared both drive gates; softsat failed low drive. Archived absorber weights underpin later tests. |
| [NL004](../results/opa-nl-004/result.json) | Lumped transmission/phase envelope: 30/270 low-drive and 32/270 high-drive cases passed; no material fit. |
| [NL005](../results/opa-nl-005/result.json) | Distributed steady-state propagation with hypothetical endpoint transmissions and TPA; bounded feasibility screen, not graphene calibration. |
| [NL006](../results/opa-nl-006/result.json) | Single-mode symmetric two-port cavity; root and energy balance checks; instantaneous closure is not dynamic validation. |
| [NL007](../results/opa-nl-007/result.json) | Mechanism and tolerance screens separate amplitude/phase effects; diagnostic ablations not physical ports. |
| [NL008](../results/opa-nl-008/result.json) | Finite index response, cold versus continuous stream; 85 passing stream groups under fixed 1 GHz noise, not speed proof. |
| [NL009](../results/opa-nl-009/result.json) | Longer streams and timing boundaries; 124 passing stream groups; C2 model becomes receiver research reference. |
| [NL010](../results/opa-nl-010/result.json) | Dynamic receiver with aligned resolution and electrical PSD; 50 ps C2 end-sampling reference clears both drives for some settings. |
| [NL011](../results/opa-nl-011/result.json) | Receiver bandwidth/timing exploration and stationary noise regression; faster timings can fail low-drive margin. |
| [NL012](../results/opa-nl-012/result.json) | Causal ridge readout improves modeled timing; 40 ps instantaneous-response passes do not establish 5 ps-response operation (best 40 ps/5 ps maximin 0.9375). |
| [NL013](../results/opa-nl-013/result.json) | Independent 45 ps ridge16 primary confirmed at LO1/60 GHz; worst 0.9599609375 under 95% gate. |
| [NL014](../results/opa-nl-014/result.json) | Single-panel exploration at 42 ps; frozen control passed, no independent cadence promotion. |
| [NL015](../results/opa-nl-015/result.json) | 42 ps ridge8 primary failed; ridge16 secondary confirmed at LO2/120 GHz (0.95068359375); LO3 ridge16 also confirmed as eligible endpoint. |
| [NL016](../results/opa-nl-016/result.json) | No qualifying proposed confirmation candidate in exploratory study. |
| [NL017](../results/opa-nl-017/result.json) | 41 ps frozen ridge16 midlow candidate proposed after single-panel maximin 0.95263671875. |
| [NL018](../results/opa-nl-018/result.json) | Independent 41 ps primary failed (0.94189453125), positive controls also failed; no speed promotion. |
| [NL019](../results/opa-nl-019/result.json) | Noise-aware margin fitting improves matched decisions but no qualifying 96% candidate; archived low-drive margin vector later frozen. |
| [NL020](../results/opa-nl-020/result.json) | Robust group/repeat optimization passed numerical checks, but all robust candidates lost one worst-repeat decision relative to fresh margin; none qualified. |
| [NL021](../results/opa-nl-021/result.json) | Independent frozen 42 ps primary passed 96% on all four groups; secondary failed; phase closure. |

## Final endpoint and controls

| Panel / drive mW | LO3 primary correct / 2048 | LO2 secondary correct / 2048 |
|---|---:|---:|
| A / 0.1 | 1970 | 1966 |
| A / 1 | 2047 | 2047 |
| B / 0.1 | 1979 | 1979 |
| B / 1 | 2047 | 2047 |

All 27 numerical checks passed. No 95% or 96% gate ambiguity across middle/fine grids; 48 of 72 groups passed inherited confirmed gate. Five of 18 endpoints satisfy the 96% criterion, but supporting comparisons do not substitute for the prespecified endpoint. Two panels share the same five trained model seeds, not independent model training. Counts are worst repeat across seeds, not independent Bernoulli trials. No statistical confidence or measured BER inference. Detailed endpoint table: [NL021 protocol and results](OPA-NL-021.md).

## Reproducibility and archive

Source [run 44504831351](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44504831351), archived by [run 44507763898](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44507763898), [PR 209](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/209), archive merge e3e142a58568f3474e326514bc96b608028c663a. [Provenance](../results/opa-nl-021/provenance.json) pins 15 science files and original ZIP. Reanalysis: `python3 research/analyze_nl021.py` checks bytes, source vectors, 360 primary rows, 1080 resolution rows, 72/216 groups, 18 endpoints, 9600 contingency rows, 240 summaries, both paired marginals and exact counts, repeat minima, normalized noise and the two thresholds. The accompanying audit workflow executes it without rerunning the experiment.

## Handoff to OPA-CIR

- Treat the C2 nonlinear block as a conditional dynamic compact-model candidate, not a PDK-qualified component. Reuse [model](../simulations/circuit/nonlinear_activation_v009.py), [receiver](../simulations/circuit/dynamic_receiver.py), [frozen workflow](../simulations/circuit/dynamic_receiver_sweep_v021.py), [weights](../results/opa-nl-003/weights.json) and [vectors](../results/opa-nl-021/coefficients.json). Keep the exact LO3 primary hash 0e7e248644f97810db177da4dabc09b6ef7f581bfb46129d85457df45d23e0ef. Separate optical state dynamics from electronic coherent readout and digital equalization.
- Use electronic activation as the hybrid accelerator baseline; optional nonlinear candidate only after circuit interfaces and power/noise budgets are defined. Do not apply a linear S-matrix to a nonlinear time-dependent device. Passive waveguide/coupler S-parameters must carry complex amplitude, phase, port reference, wavelength, normalization and provenance.
- Prioritize circuit-level verification and an end-to-end reference architecture over further isolated cadence optimization. Start with a small MZI circuit; progressively replace ideal models with validated component models. Compare matched workloads, optical power, phase, loss, latency and electrical overhead. Unknown parameters remain unknown.
- Reopen NL only if system-level evidence identifies a concrete bottleneck and a separately preregistered study is justified. 40 ps remains a long-term research target, not a requirement for starting circuit work.

## Limits and unresolved engineering questions

Phenomenological cavity, hypothetical PSD, no calibrated material or geometry, no fabricated nonlinear device, no WDM cross-saturation validation, no ADC/clock/driver implementation or measured wall-plug power. Eight segments per symbol imply about 190.48 Gsegment/s in the model, not an implemented ADC rate. Coherent signed encoding, LO phase stability, detector peak cap and assumed receiver noise must be revalidated for a real system. Signal and LO electrical lower bounds do not include control, ADC, memory, packaging or distribution. Synthetic XOR is not a large neural network or general AI workload. No fully optical training or backpropagation claim.

**Closure decision:** preserve all positive and negative evidence and freeze the NL001–NL021 phase. Next: OPA-CIR-001, a separate circuit-simulation research project.
