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
