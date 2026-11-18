# OPA-NL-009 — Timing boundary and long-stream validation

Status: implemented and executed; initial CI-report analysis below; raw archive pending. Parent evidence: [NL008](OPA-NL-008.md), [archive](../results/opa-nl-008/provenance.json), source run 44192685431, archive run 44195593749, archive merge 84678fb6d8c0eb9cbe1adeafe1a16d45f243a72f.

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

## Initial observed results — 18 November 2026

Source [run 44197189683](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44197189683), job 134441768784, PR 158, artifact 14381707815. All 19 implementation checks passed, 3600 seed rows, 720 groups, 30 references, 110 extra confirmations and 34 detected boundary intervals (changes in the four-component drive/history gate vector). Candidate loops finished in 2254.3 seconds. Source is CI-emitted JSON, not yet independently verified raw files.

Maximum stationary error 9.030102731546361e-12; slot balance 2.1940922663195583e-7; coarse/fine field difference 1.0812542784080838e-7; normalized aggregate energy difference 3.4792038083437574e-7. Extra convergence gate passed.

152/360 cold groups and 124/360 stream groups pass. These aggregate counts do not establish paired losses/gains; inspect raw summary after archival. Of 180 candidate/timing tuples, 54 pass streaming at both drives (different frozen networks). Duration breakdown:

| On ps | Stream pass / 36 | Both drives / 18 |
|---:|---:|---:|
| 10 | 0 | 0 |
| 15 | 0 | 0 |
| 20 | 0 | 0 |
| 25 | 1 | 0 |
| 30 | 6 | 1 |
| 35 | 13 | 4 |
| 40 | 20 | 8 |
| 45 | 23 | 11 |
| 50 | 25 | 12 |
| 200 | 36 | 18 |

### Shortest sampled passing stream duration at both drives

| Candidate | Response ps | Gap ps | Shortest on ps | Worst repeat .1 mW | Worst repeat 1 mW |
|---|---:|---:|---:|---:|---:|
| C1 | 0 | 0 | 45 | 99.609375% | 95.312500% |
| C1 | 0 | 20 | 30 | 96.093750% | 99.218750% |
| C1 | 5 | 0 | 45 | 99.609375% | 97.265625% |
| C1 | 5 | 20 | 35 | 97.460938% | 100.000000% |
| C1 | 50 | 0 | 200 | 99.609375% | 100.000000% |
| C1 | 50 | 20 | 200 | 99.609375% | 100.000000% |
| C2 | 0 | 0 | 35 | 97.070313% | 96.679688% |
| C2 | 0 | 20 | 35 | 96.484375% | 100.000000% |
| C2 | 5 | 0 | 40 | 97.460938% | 100.000000% |
| C2 | 5 | 20 | 40 | 97.265625% | 100.000000% |
| C2 | 50 | 0 | 200 | 98.632813% | 100.000000% |
| C2 | 50 | 20 | 200 | 98.632813% | 100.000000% |
| C3 | 0 | 0 | 45 | 98.828125% | 95.312500% |
| C3 | 0 | 20 | 40 | 97.460938% | 99.609375% |
| C3 | 5 | 0 | 50 | 98.828125% | 99.023438% |
| C3 | 5 | 20 | 40 | 96.093750% | 99.804688% |
| C3 | 50 | 0 | 200 | 99.023438% | 100.000000% |
| C3 | 50 | 20 | 200 | 99.023438% | 100.000000% |

No interpolation or monotonicity is assumed. At 25 ps only C2, instantaneous response, 20 ps gap, 1 mW passes (worst repeat 96.2890625%); this is not a both-drive result. C1 30 ps with 20 ps gap has a nominal cadence of 20 Gsymbol/s. C2 35 ps without gap, instantaneous response, reaches nominal 28.571 Gsymbol/s, worst repeats 97.0703125% and 96.6796875%; memory field maxima .006483965 and .041808187 sqrt(mW). C2 40 ps without gap and 5 ps response reaches nominal 25 Gsymbol/s, worst repeats 97.4609375% and 100%, memory field maxima .004777573 and .038180851 sqrt(mW). All five seeds have perfect clean pre-receiver accuracy for these two C2 timings; projected accuracy is not necessarily perfect. These results are conditional on the hypothetical material response and fixed 1 GHz noise diagnostic, not validated receiver bandwidth or hardware throughput. No physical energy or speed advantage is established. The longer test is independent, so differences from NL008 cannot be attributed exclusively to stream length.

### Archive and next steps

ZIP 11597063 bytes, SHA-256 acc3645d4eefcf394d8706ab738271479af5d2fea29161c1a1385dd93b2ce158. Archive workflow will verify identity, CRC, all ten CI-emitted file hashes and staged bytes, then create a separate review branch. No archive execution yet. After archival analyze paired groups, signed margins, position trends and traces, then preregister a dynamic receiver experiment with bandwidth, integration and correlated noise, rather than treating the fixed ENBW diagnostic as validation at these rates.
