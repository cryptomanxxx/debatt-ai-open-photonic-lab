# OPA-NL-009 — Timing boundary and long-stream validation

Status: proposed protocol for review; not implemented or run. Parent evidence: [NL008](OPA-NL-008.md), [archive](../results/opa-nl-008/provenance.json), source run 44192685431, archive run 44195593749, archive merge 84678fb6d8c0eb9cbe1adeafe1a16d45f243a72f.

## Paired archive analysis

Pair summary.csv cold and stream by candidate, response_ps, on_ps, gap_ps and drive_mw (five seeds per group). Use screen_pass exactly as archived, not a new gate.

| On (ps) | Both pass | Cold only | Stream only | Neither |
|---:|---:|---:|---:|---:|
| 10 | 0 | 0 | 0 | 72 |
| 50 | 33 | 11 | 0 | 28 |
| 200 | 52 | 2 | 0 | 18 |
| Total | 85 | 13 | 0 | 118 |

The absence of passes at 10 ps even in cold resets means memory alone cannot explain the failures. At 50 and 200 ps history can change a passing group to a failing group; group-level results do not imply individual accuracy never improves. Cold reset is a diagnostic, not a free physical operation.

C1, 50 ps on, 5 ps response, stream, both drive-specific frozen networks:

| Drive (mW) | Gap (ps) | Worst repeat | Min projected field (sqrt(mW)) | Max memory field (sqrt(mW)) |
|---:|---:|---:|---:|---:|
| .1 | 0 | .9921875 | .00813208 | .00296569 |
| 1 | 0 | 1 | .00592945 | .03012622 |
| .1 | 20 | .9921875 | .00799140 | .00111102 |
| 1 | 20 | 1 | .02481328 | .00626999 |

Values are minima/maxima across five seed rows, not necessarily the same sample. The archived field statistic is min_projected_field; do not reinterpret as a signed class margin without checking implementation. Across all 2160 metrics rows, maximum aggregate normalized energy residual abs(input+initial-reflection-drop-absorption-final)/(1+input+initial) is 7.90268e-9; this does not replace the per-slot audit (max 3.91443e-7 in NL008). Slot boundary energy terms must not be counted as wall-plug energy. First-stream trace file was not available through the analysis connector; no trace-level conclusions are claimed here.

## Preregistered follow-up

Question: how short can the rectangular on duration become while retaining the inherited accuracy gate on independent, longer streams? This is a conditional model boundary, not hardware throughput.

- Primary candidates C1, C2, C3 selected post-hoc from NL008 common-drive passes. Preserve their parameters, tau=10 ps, Us=3 fJ, loss, frozen weights and both .1/1 mW drive-specific networks. No retraining or test-label timing optimization.
- Grid on duration 10,15,20,25,30,35,40,45,50 ps; gap 0 or 20 ps; response 0,5,50 ps. Add 200 ps controls for all gaps and response times. Keep cold and stream paired. 180 candidate/timing combinations including controls, 720 groups and 3600 seed rows for five seeds.
- Use fresh independently generated balanced jittered XOR samples (new RNG domains distinct from all prior training and tests; verify against source before choosing IDs). 512 samples per seed and drive, arranged into eight independent 64-symbol streams with independent label-blind shuffle. Same inputs/order across conditions; carry field and material state without resets within streams. Compare paired cold and stationary references on identical inputs. Report per-position accuracy and memory, and first vs last 8 symbols; no claim beyond 64-symbol horizon.
- Inherit NL008 screen: all five seeds stationary eligible, clean pre-receiver accuracy >=95%, worst noisy repeat >=95%, peak sampled diode <=2 mW. Retain eight noise repeats and existing 1 GHz diagnostic, explicitly not a dynamic receiver. Report all outcomes, including science failures. Compare common-drive passing timing tuples; no monotonicity assumption or interpolation between sampled durations. A 200 ps control failure on fresh data must be reported rather than silently discarded.
- RK4 coarse .5 ps and fine .25 ps, with .125 ps confirmation at every observed pass/fail boundary (both sides) and at 10/50/200 ps controls; if no boundary exists report that fact. Boundary confirmation is a numerical diagnostic, not a new test-label selection. Use inherited slot balance <1e-6, field and aggregate energy convergence <1e-5, passive second MVM, q bounds, first-symbol equality, analytic linear and stationary checks, finite values and expected counts. Preserve prior archives. Budget runtime before launching; if batching is necessary, predeclare deterministic partitions with identical inputs and aggregate completeness checks.
- Record signed projected class margins explicitly (label sign times decision statistic after fixed projection), complex fields, worst repeat, energy terms, and grouped/position summaries. Keep implementation checks separate from science outcomes. Archive raw evidence and provenance via established review workflow.

## Receiver and physical limits

A separate dynamic receiver stage must model optical/electrical filtering, integration and correlated noise at cadence, using a specified transfer function and independently calibrated noise. Do not treat fixed 1 GHz ENBW as validation at 20 Gsymbols/s. For nonzero gap nominal cadence is 1/(on+gap), not 1/on. No measured material response, spatial propagation, hardware rate, BER, energy advantage or general-purpose accelerator performance is established.

## Before execution

Implement the experiment in the existing registered experiment framework, verify RNG domain allocation and source conventions, add regression checks and review the runtime budget. This protocol PR intentionally does not modify the solver or existing results.
