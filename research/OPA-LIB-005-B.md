# OPA-LIB-005-B — Passive test structures and measurement requirements

Scope: **design of a measurement program, not fabrication-ready geometry**. [Machine-readable plan](../components/comparison/lib005-passive-test-plan.json) enumerates ten distinct structure categories (five per process); [LIB005-A](OPA-LIB-005.md) records why no exact-cell optical measurements can calibrate current simulated components. The aim is a small **passive** first test die and external tunable laser, detector/power meter or OSA. Integrated sources, optical gain, photodiodes, electrodes and full AI mesh are outside the scope.

## Candidate structures and real component reuse

| Test category | SOI SiEPIC EBeam | TFLN Luxtelligence lnoi400 | Measurement |
|---|---|---|---|
| Cutback | New measured-length series; reference published PCM spirals are **not same geometry** | reuse `straight_rwg1000` as building block; make several lengths | attenuation slope, fit quality, account for input/output loss |
| Bend chain | New SOI bend test layout | reuse `L_turn_bend` with straight controls | per-bend excess loss conditional on reference |
| Splitter | `ebeam_bdc_te1550` original GDS | `mmi2x2_optimized1550` generated PCell | bar/cross split, total normalized transmission; characterize both inputs |
| Passive MZI | revise existing SOI MZI layout so heater is absent or explicitly inactive | two MMI PCells and passive paths; **not** active 5 mm MZM | spectral fringe, extinction, FSR and path-dependent interpretation |
| Optical I/O | `ebeam_gc_te1550` grating | `double_linear_inverse_taper` edge | fiber-to-fiber power, wavelength and alignment repeatability |

The TFLN directional-coupler polynomial fit fails passivity at all 201 samples. It remains quarantined and excluded from candidate modeling; neither its GDS nor its use in a future exploratory test should be mistaken for calibrated passivity. The SOI parent MZI has an independent DRC result; it **does not qualify any new child test layout**. PCell source software rights are separate from foundry process access or IP licensing.

## Measurement protocol and data contract

Each candidate has hypothesis, baseline/reference structures, measurable readouts, mandatory metadata and failure modes in the JSON plan. Repeat optical I/O reference and source-power/polarization checks before and after device groups. Record raw traces per device and illumination direction, wavelength grid, launch power and calibration, alignment, exposure/measurement temperature, port naming, exact design revision and as-fabricated path lengths when available. Fit attenuation versus known lengths, propagate uncertainties and report fit residuals. Back-to-back coupler loss cannot automatically be divided by two without justified symmetry; raw optical powers cannot establish complex phase or intrinsic microring Q. Avoid claiming foundry DRC or process qualification from repository layout checks.

**Proposed file schema:** `raw_spectra.csv`, `instrument-settings.json`, `device-map.csv`, `reference-measurements.csv`, `derived-metrics.json`, `source-and-license-provenance.json`. These are future deliverables, not files currently measured or created.

## Four gates, all currently open

- **P0 process access:** select a facility, process revision and permission; confirm design-rule deck, MPW, budget and schedule
- **P1 measurement plan freeze:** finalize exact geometries/lengths, replicates and quantitative acceptance criteria, wavelength/polarization, reference planes, instrument uncertainty
- **P2 layout/foundry review:** create test-chip GDS, route and label ports; pass applicable foundry-approved DRC/DFM and review
- **P3 physical evidence:** manufacture/test, archive raw and reference measurements, uncertainty, full geometry identity and matched simulations

SOI and TFLN require **separate process-specific die proposals** unless an actual heterogeneous integration process is confirmed. No wafer, fab booking or shipping is implied. Numerical values, footprint, acceptance thresholds and measurement uncertainty remain unknown instead of being invented.

## LIB005-C handoff

Seek measured, same-process, same-revision component transfer data and establish complex phase/reference-plane conventions where appropriate. Prefer a matched passive optical MMI or SOI broadband coupler; otherwise use the P0–P3 plan to obtain new data. LIB006 selection remains gated by facility feasibility, geometry, measurement plan and cost.
