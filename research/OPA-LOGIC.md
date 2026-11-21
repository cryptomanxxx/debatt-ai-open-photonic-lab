# OPA-LOGIC · Energy-Efficient Optical Logic

Chip 11 uses a receiver-assisted silicon microring routing tree. A and B are
on/off optical power inputs. Two powered receivers set an electrical voltage
on ring A and the two copies of ring B. A third, continuously available laser
supplies the probe and permits a high NAND output for 00. Each ring has a
through port and a backward drop port folded into the next stage. The four
leaves are through-through (00), through-drop (01), drop-through (10) and
drop-drop (11). The selected leaves feed one output of an ideal symmetric
coherent combiner; other ports terminate in optical dumps. Gate selection
represents a choice of passive wiring. The optical power at the photodetector
and a fixed comparator threshold determine the displayed bit.

The browser and compact-model experiments share one implementation. The
frequency-domain model uses temporal coupled-mode rates for two equal
couplers and an independent intrinsic loss rate. Loaded linewidth adds those
three rates. A local radius derivative uses effective/group indices 2.4/4.1.
The exponential gap relation and 130 pm/V electrical tuning are illustrative
parameters. A phase-ramp control tests relative phases at the combiner. One
ideal combiner row has field weights of magnitude 1/√k for k selected paths.
The archived silicon spiral cutback measurements in LIB004 constrain straight
propagation for their specific process and geometry. The LIB004 Twente ring
analysis is TFLN. Neither source calibrates this SOI junction, ring geometry,
coupling or electrical shift. See the
[component evidence policy](../components/README.md).

| Experiment | Method and exported evidence |
| --- | --- |
| OPA-LOGIC-001 | Passive 2D effective-index Meep FDTD. Eigenmode excitation and port projection with straight-guide normalization at 24 and 32 pixels/µm. Through/drop spectra, strongest drop resonance, loaded Q, uncollected flux and predeclared screens. |
| OPA-LOGIC-002 | Compact model evaluates 16 nominal AND/OR/XOR/NAND vectors and deterministic detuning, phase, drive, optical-input and loss perturbations. |
| OPA-LOGIC-003 | Compact-model AND→XOR for all eight input patterns at each interstage loss. The measured quantity in the calculation is the optical power at the second-stage input plane, followed by electrical regeneration and routing of a fresh optical probe. |
| OPA-LOGIC-004 | Per-slot accounting across operation rates and laser efficiencies. Exports the optical input/output, wall-plug laser, switching, drivers, receivers and static overhead terms. |

Use the existing [Experiments workflow](../.github/workflows/experiments.yml).
The four registered IDs are `opa-logic-001` through `opa-logic-004`.
The workflow uploads per-experiment JSON and CSV files as well as the
`all-experiment-results.zip` bundle. Compact runs use Node.js 20 or later.
Run browser model assertions with
`node --test simulations/logic/optical-logic.test.mjs`. The browser also exports
its selected parameter set, truth table, spectrum and per-vector energy
budget as JSON, CSV or a single ZIP.

## Limits and next measurement

The FDTD component uses a small ring to isolate the mechanism and make the
two-resolution run practical. It has lossless materials and does not include
the silicon slab, vertical confinement, PN junction, electrical response or
nonlinearity. Uncollected flux can include leakage into other ports,
reflection, radiation and numerical error. It is not measured absorption.
The 10 nm peak-shift screen is a coarse grid check. A foundry model would
need mode-matched 3D extraction, channel separation, independent
resolution/time convergence and a revision-matched measurement.

In the local locked Meep 1.35.1 run, the main drop peak was at 1574.80 nm
on the 24 px/µm grid and 1571.37 nm on the 32 px/µm grid. On the finer
grid, the guided drop and through fractions were 54.84% and 6.60% at the
peak, and 38.57% was uncollected. Extending the post-source window from
650 to 1800 µm/c reduced maximum apparent guided power excess from
11.0% to 0.29% across the two grids. The 3.44 nm grid shift was larger
than the approximately 1.79 nm finer-grid linewidth. This verifies the
qualitative add-drop signature and a bounded power balance for the toy
geometry. It leaves the absolute wavelength unresolved at linewidth
precision.

The gate and cascade calculations use settled optical fields and ideal
comparator decisions. An EO test chip needs calibrated bias, capacitance,
driver and receiver noise, bandwidth, data thresholds, thermal drift, phase
matching, regeneration and fan-out. Passive filters route a pre-existing
carrier without data-dependent modulation. All-optical nonlinear logic
needs an optical control interaction with independently validated
power-dependent loss and dynamics. Ordinary linear FDTD cannot establish
those dynamics. A future silicon nonlinear study should model the relevant
Kerr, two-photon absorption, free-carrier and thermal terms where applicable,
then test switching and regeneration with a matched control.

The energy model calculates ½CV² per capacitive edge (20 fF assumption)
and assumes a 0.5 transition probability for independently distributed
equiprobable decoded bits. The two drivers and three receivers are
separately accounted for. Laser wall-plug energy includes the energy sent
as light. The slot rate does not establish speed, and the accounting needs
component measurements and matching workload/system boundaries before
a comparison with electronics.

## Published evidence

- [Zhou et al., Nature Communications 17, 8793 (2026)](https://doi.org/10.1038/s41467-026-75750-x)
  fabricated a reconfigurable SOI ALU using reverse-biased carrier-depletion
  microring modulators and thermal trim. Functional verification was
  at 20 Gb/s. The separate 80 Gb/s modulator characterization does not
  establish that ALU rate. Their 12.36 fJ/bit ALU estimate accounts for
  twelve microring loads at an estimated 1.03 fJ/bit per ring. The
  experimental laser, EDFA, test electronics and detection do not enter
  this figure. Chip 11 borrows the directed-routing principle.
- [High-Contrast and High-Speed Optical Logic Operations Using Silicon
  Microring Resonators, Nanomaterials 15, 707 (2025)](https://doi.org/10.3390/nano15100707)
  reports FDTD for phase-sensitive interference using coherent inputs and
  a control port. Its threshold, modeled contrast and timing are specific
  to that design. The results are simulations. They do not establish a
  fabricated chip, an arbitrary passive single-ring gate or a measured
  system energy advantage.
- [Chen et al., Optics Letters 37, 1882–1884 (2012)](https://pubmed.ncbi.nlm.nih.gov/22714146/)
  demonstrated XOR/XNOR with two electrically controlled cascaded silicon
  rings. Chip 11's three-ring tree and leaf wiring are its own teaching
  architecture.
