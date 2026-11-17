# OPA-SYS-006 — paired training convergence audit

This experiment extends the AG003 original training benchmark, not the
MOD-007 physical mesh model. It uses the archived original teacher
dataset (8 inputs, 16 teacher hidden units, six classes; 3000 training
and 600 validation examples), 128 student hidden units, electronic ReLU
and softmax, Adam, batch 64, 120 epochs, learning rate 0.008, seeds
42, 137, 2025. Separate random streams fix initialization and batch
order across policies and pair validation noise. No tuning on validation
labels. All settings are chosen before results; negative results valid.

## Candidates and controls

Select the best system-efficiency candidate in each of Hybrid:4,
Hybrid:6, MZI:6, MRR:6, IndepLaser_MZI:6 and IndepLaser_MZI:8, plus
the six-bit comb candidate with greatest modeled booster headroom.
Verify all seven records against the immutable SYS005 archive and
verify its evidence-file hashes. No inference about the other candidates.

Run true FP32 and FP64 digital controls, quantization-only 4/6/8,
original fixed-noise/drift 4/6/8 and original severe-drift control.
For each candidate compute SNR independently from SYS003 current-noise
equations using archived receiver signal and ASE. Use normalized RMS
numerical noise sigma = 1/sqrt(SNR), conditional on the chosen signal
normalization, not a calibrated signed optical encoding. Apply
per-tensor symmetric quantization to operands and output; receiver
noise is additional, not a measured combined ENOB. Compare nominal
sigma, 3*sigma plus 1% RMS bias, and 10*sigma plus 5% RMS bias.
These are hypothetical sensitivity points. Identical bits and SNR
imply identical nominal proxy behavior regardless of architecture;
do not interpret this as an MZI/MRR comparison. The noisy backward
activation MVM, electronic weight gradients and Adam approximate the
original hybrid training; this is not physical optical backpropagation.

Separately re-optimize gain for each selected candidate at 100%, 95%,
90%, 80% of assumed booster saturation limit; link feasibility is
not coupled to the training proxy. Report failure reasons. Do not
assume amplifier headroom proves robustness against actual saturation.

## Outputs and acceptance

30 cases (9 controls + 21 candidate scenarios), three seeds each:
90 training runs, 10,800 epoch records, 28 derating cases. Report
per-seed final validation accuracy, loss, first five consecutive
epochs at >=90%, final-epoch gate and all-seed convergence, deployment
of digitally trained FP32 weights under the same noise, and clean
readout of hybrid weights. No fabricated epochs for untested cases.
Finite-difference digital gradient test, independent SNR checks,
source integrity, candidate membership, finite metrics and row counts
are implementation gates. Digital learning preflight requires mean
accuracy >80%; scientific convergence target remains 90%.
A small teacher-student task does not establish large-model convergence.
No extrapolation of epochs or energy to the SYS005 system workload;
no physical efficiency claim. Preserve original and all prior stages.

Run:
```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/ag003_convergence_v006.py
```

Artifacts: result.json, metrics.csv, learning_curves.csv,
paired_deploy.csv, derating.csv, CI environment metadata.

## Observed results — 2026-11-17

[CI run 44125011406](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44125011406)
passed all 13 implementation checks. Artifact 14347985409 was downloaded
and independently inspected locally: 220,764 ZIP bytes, SHA-256
dbf45cf71e8d3d1faaafb171badba61f6156b6345be28b8de1370c06eb47187e,
all CRCs passed, seven exact file lengths and hashes pinned in
archive_sys006.py. Verified 90 metric rows, 10,800 unique epoch keys.
Digital finite-difference gradient error 2.78e-11.
Permanent archive pending explicit workflow.

| Case | Mean final validation accuracy | Minimum | All seeds pass |
|---|---:|---:|---|
| Digital FP32 | 94.33% | 93.33% | yes |
| Digital FP64 | 94.11% | 93.17% | yes |
| Quantization only 4 | 79.22% | 73.00% | no |
| Quantization only 6 | 91.00% | 89.83% | no |
| Quantization only 8 | 93.83% | 92.67% | yes |
| Original noise 4 | 80.22% | 75.00% | no |
| Original noise 6 | 89.72% | 87.83% | no |
| Original noise 8 | 92.28% | 90.67% | yes |
| Original high drift | 76.72% | 73.50% | no |
| 4-bit nominal | 79.72% | 75.17% | no |
| 4-bit stress | 81.17% | 78.00% | no |
| 4-bit severe | 78.06% | 73.67% | no |
| 6-bit nominal | 90.39% | 89.50% | no |
| 6-bit stress | 90.39% | 89.33% | no |
| 6-bit severe | 88.89% | 85.83% | no |
| 8-bit nominal | 93.83% | 91.67% | yes |
| 8-bit stress | 93.39% | 91.67% | yes |
| 8-bit severe | 91.61% | 89.17% | no |

The five six-bit representatives share the same numerical error proxy,
not independent physical validation. Nominal RMS receiver errors are
3.4080%, 0.8521%, 0.2131% at 4/6/8 bits respectively. Six-bit
nominal final accuracies for seeds 42,137,2025: 89.50%, 90.33%,
91.33%; first five-epoch sustained target starts at 27,33,1.
All hit the sustained threshold at some point, but seed 42 finishes
below target. Nominal eight-bit final accuracy: 91.67%,94.50%,95.33%;
first sustained target starts at 7,6,1, identical to FP32's starts.
Four-bit nominal never reaches a five-epoch sustained target.
Four-bit quantization alone is a substantial bottleneck in this task.
Original fixed-noise six-bit control also fails the all-seed gate
under the new paired protocol; this is not an exact replay of the
original training loop.

Nominal digital-weight deployment mean accuracy: 73.39%, 91.50%,
94.11% for 4/6/8 bits. This outperforms noisy six/eight-bit training
in mean accuracy but does not establish a general training strategy.
Four-bit hybrid training improves over direct deployment (79.72%
vs 73.39%) without reaching target. No measured hardware accuracy.

### Independent amplifier derating test

| Selected representative | 250 mW | 237.5 mW | 225 mW | 200 mW |
|---|---|---|---|---|
| Hybrid 4 | pass | pass | pass | fail |
| Hybrid 6 best efficiency | pass | fail | fail | fail |
| MZI 6 best efficiency | pass | pass | pass | fail |
| MRR 6 best efficiency | pass | pass | pass | pass |
| Independent laser 6 | pass | pass | pass | pass |
| Independent laser 8 | pass | pass | pass | pass |
| Hybrid 6 best headroom | pass | pass | pass | pass |

Independent lasers are passive in these selected configurations;
derating does not stress their source limits. MZI 6 reselects gain
17/15/14 dB at the first three limits; efficiency 0.8899/0.8636/0.8387.
Best headroom six-bit comb: distributed Hybrid, eight pumps and
combs, eight wavelengths, mesh 4, eight tiles, TFLN. 15 dB gain,
121.343 mW per pump, 108.153 mW per booster, 56.74% nominal
saturation headroom, 30.529 TOPS, 34.792 W, 53.04 mm², 0.8775 TOPS/W.
It is a useful lower-power link research candidate, but fails the
same six-bit numerical convergence gate. Best efficiency Hybrid 6
(1.2428 TOPS/W) fails already at 95% saturation. Derating does not
model real saturation dynamics or training noise changes.

### Interpretation and next step

Only the selected eight-bit independent-laser numerical proxy passes
both nominal and moderate stress convergence. Its SYS005 system
proxy is 0.6359 TOPS/W, 244.234 TOPS, 384.088 W, not a measured or
accuracy-matched electronic comparison. No six-bit comb representative
passes the strict all-seed numerical gate. No eight-bit comb analytical
candidate was found in SYS005. Do not label all 82 eight-bit candidates
as individually trained, or promote any 6-bit architecture as validated.
A final AG003 report should distinguish analytical feasibility, this
toy convergence gate, and unverified transfer/hardware accuracy;
recommend the passive eight-bit source as a numerical reference and
the headroom Hybrid 6 as an experimental link target, not a production
OPA. Further precision-aware training or eight-bit comb link work
belongs to the subsequent research roadmap, not a silent change of
the preregistered gate. No toy-to-system energy extrapolation.
