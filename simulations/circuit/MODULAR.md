# OPA-MOD – Modular photonic computing

Research question: can tiled photonic processors improve accuracy and optical power budgets for the same workload, after electronic and communication overhead is accounted for?

| Experiment | Scope |
|---|---|
| OPA-MOD-001 | Ideal mathematical equivalence |
| OPA-MOD-002 | Optical loss and power budgets (archived) |
| OPA-MOD-003 | Component errors and numerical precision (archived) |
| OPA-MOD-004 | Calibration and bounded gain compensation (archived) |
| OPA-MOD-005 | Communication and energy (implemented; CI pending) |
| OPA-MOD-006 | Training (planned) |

MOD-001 compares a digital reference with SVD and QR factor models for a 128×128 matrix, using tile sizes 128, 64, 32, 16 and 8. Each tile implements its actual matrix block, with signed coherent field readout and electronic accumulation. SVD uses two unitary meshes, normalized attenuators and electronic gain; QR uses one mesh and electronic triangular multiplication. The adjoint reverses these mathematical operations. Explicit Clements reconstruction is checked separately at sizes 4 and 8; large-size comparisons are factor-level only.

Run from repository root: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/modular_equivalence_v001.py`. CI uses the registered locked environment and publishes the result artifact. This experiment establishes numerical equivalence only, not physical advantage. Results are not archived as CI provenance until an actual run is available.

MOD-002 uses the same deterministic 128-dimensional workload as MOD-001. It compares fixed total launched optical signal power, with actual normalized singular-value attenuation, ideal fan-out allocation, splitter excess loss, uniform column-equivalent MZI/waveguide loss, interface loss and modular link loss. QR is a separate hybrid scenario with independently encoded electronic R*x inputs. All loss parameters are hypothetical sensitivity assumptions. Aggregate detected signal power is not an equal-SNR or energy-efficiency metric. Electronic gain is ideal and noiseless; real detector, conversion and communication costs are deferred. Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/modular_power_budget_v002.py`.

MOD-003 compares explicit Clements SVD meshes at all five sizes, with an algebraically equivalent row/column optimized decomposition validated against the existing mesh implementation. Four MOD-002 workloads, eight static hardware draws, eight error scenarios and two scalar loss conditions are used. Static phase/coupler/differential-arm/attenuator errors and coherent real-field readout noise/quantization are separated. Equal total launched signal power and fixed detector full-scale are used; only known common loss is compensated. All error and receiver parameters are hypothetical, not calibrated to physical hardware. No QR, calibration, training or energy claim. Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/modular_imperfections_v003.py`.

MOD-004 uses explicit MOD-003 SVD meshes and compares uncalibrated, oracle-assisted local phase correction with 0.001 rad metrology uncertainty, global scalar electronic gain, tile-wise scalar gain, and their combinations. Gains are bounded and fitted on 32 noisy calibration probes; 32 independent held-out probes evaluate generalization. No full electronic residual matrix is used. Coupler and differential loss remain unchanged; local metrology access is hypothetical, not a hardware procedure. Costs count phase offsets and scalar gain measurement/arithmetic, not physical energy or time. Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/modular_calibration_v004.py`.

MOD-005 compares the same 128-dimensional SVD workloads at five tile sizes. It solves for launched signal photons under a common worst-vector expected receiver-noise RMS target, including a fixed normalized ADC rounding floor. It then budgets signal laser, local oscillator, input modulation, receiver/ADC, partial-output communication, electronic gain and accumulation, static control, setup/calibration and fixed power. All coefficients are hypothetical sensitivity inputs. Static hardware errors and calibration residuals are excluded from the precision target; this is not a measured end-to-end energy or accuracy comparison. Infeasible ADC floors and both favorable and unfavorable energy ratios are retained. Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/modular_energy_v005.py`.
