# AG003 preliminary source audit (2026-11-17)

Scope: static inspection of the seven files downloaded from GitHub artifact
14325015236, snapshot workflow run 44074735184. The downloaded ZIP SHA-256 is
`ff289ebdc02161598cc4a2655796c8e4ad4df537095b3f84129651f44d88f04d`.
All seven lengths and SHA-256 digests match the live snapshot diagnostics.
The exact bytes are pinned in import_snapshot.py. No recovered code was executed.
The snapshot is from the original environment after recovery attempts, not
an independently attested historical version.

## Observations that block scientific acceptance

1. **Low-loss test permits a pass without a comparison.** sweep.py:290–303
   reports a successful monotonic loss check if the low-loss case is feasible
   and the nominal case is infeasible. report.json records nominal loss null,
   low-loss 18.63 dB, passed true. Thus the final code does not demonstrate
   that reducing passive losses decreases path loss. The earlier failing
   implementation is not recovered. Independently evaluate both cases at
   identical operating conditions, expose intermediate losses even for
   rejected configurations, and compare unrounded quantities.
2. **Structured results and narrative disagree.** report.json reports
   CFG-0100 at 1.5405 system TOPS/W and 5.962 chip TOPS/W; the structured best
   convergent comb-powered candidate is null. run_all.py:163–168 hardcodes
   narrative values of about 1.73 and 1.3 system TOPS/W. Do not treat these
   narrative numbers as computed results.
3. **Convergence assumptions exceed measured training tests.**
   run_all.py:63–65 unconditionally accepts 12-bit with the baseline epoch
   count; train_sim.py:189–198 has no 12-bit test. Convergence filtering uses
   only a selected candidate pool (run_all.py:67–107), not all 325 feasible
   configurations. The null comb result is not proof that no feasible
   comb architecture can converge. Check the entire feasible population,
   and test 12-bit and architecture-specific error models.
4. **Circuit and training models are not physically coupled.**
   train_sim.py:42–63 and 189–198 use fixed quantization and Gaussian noise/
   bias per training configuration, not the calculated wavelength-dependent
   circuit transfer matrices. The synthetic teacher dataset and student
   MLP cannot establish large-model training efficiency. The so-called FP32
   baseline initializes float64 weights and biases (84–87); the label is
   not a verified FP32 numerical baseline.
5. **Energy/throughput assumptions require explicit checks.**
   physics_model.py:357–367 has a comment stating 200 TMAC/s (400 TOPS)
   but uses a 100 TMAC/s electronic unit and a 200 TOPS peak contribution.
   The calculation and peak contribution are internally consistent on this
   point; the comment is not. At 393 the max of photonic and electronic
   times assumes overlap; validate scheduling and dependencies, and audit
   per-component power, optical link budget and system boundaries.

## Reported comparison targets, not reproduced

- 330960 configurations, 325 feasible before convergence filtering.
- CFG-0100: independent laser MZI, six bits, 488.467 sustained TOPS,
  317.085 W system power, 1.5405 system TOPS/W.
- Modeled electronic baseline 3.5 TOPS/W.
- Mean final validation accuracies: digital 94.50%, 8-bit hybrid 93.05%,
  6-bit hybrid 91.50%, 4-bit hybrid 79.72%.
- Reported environment: Python 3.12.3, NumPy 2.5.4, Pandas 3.1.1.

## Reproduction plan

Archive the seven files without changing any bytes. Review the complete
source before execution. Run in a credential-free, network-isolated sandbox
using a disposable copy mounted at /workspace: run_all.py:182 writes to
/workspace/report.json, so never mount the archived original there writable.
Record actual dependency availability and versions; if original versions
cannot be installed, disclose the substitute environment. Compare structured
numeric results and seeds with the original report; ignore runtime variance
only by explicit policy. Preserve failures and separate exact replay from
independent corrected-model validation. Do not claim FDTD, experimental
hardware verification, or large-model training from these simulations.
