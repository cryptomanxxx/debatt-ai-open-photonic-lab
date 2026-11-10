# Debatt-AI Open Photonic Lab

An open, reproducible laboratory for designing photonic AI accelerators: from
simulation of single components, through Mach–Zehnder interferometer (MZI)
meshes, to chip layouts that can be sent to a multi-project wafer (MPW)
fabrication run.

> **Status:** early stage. The lab currently contains a series of
> reproducible Meep FDTD experiments on generic dielectric waveguides. No
> foundry-calibrated component or chip layout exists yet. See the
> [roadmap](#roadmap).

## Interactive demonstrations

- **Open Photonic Lab:** [Explore the photonic chip design laboratory](https://debatt-ai-open-photonic-lab.mr-marcus-sweden.chatgpt.site/)
- **MZI learning simulation:** [Explore optical interference and AI learning](https://optiskt-ai-larande.mr-marcus-sweden.chatgpt.site/)

## Why

Optical computing can perform matrix–vector multiplication, the core
operation of neural networks, with light instead of electrons. Going from an
idea to a fabricated photonic chip is still hard and mostly happens behind
closed doors. This lab aims to make every step open, documented and
reproducible so that anyone can learn from it and build on it.

## Principles

1. **Reproducible:** every experiment runs in GitHub Actions against an exact,
   locked conda environment
   ([`opa-fdtd-linux-64.lock.txt`](simulations/meep/opa-fdtd-linux-64.lock.txt)).
2. **Honest:** every result states what it does *not* show. Illustrative
   models are never presented as foundry-validated predictions.
3. **Incremental:** experiments are numbered (`OPA-FDTD-NNN`), small, and
   build on each other. Old experiments are kept unchanged as a record.

## Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| 1 | FDTD fundamentals: reproducible Meep pipeline, convergence and normalization practice | **Done** (001–009) |
| 2 | Guided-mode metrics in 3D (eigenmode source and decomposition) | **Started** (010–011) |
| 3 | Real material platforms (e.g. Si/SiO₂ 220 nm, SiN, LNOI) and spectral response | Planned |
| 4 | GDSFactory components in an open PDK: waveguide, bend, directional coupler, MMI, phase shifter, single 2×2 MZI | Planned |
| 5 | MZI mesh (2×2 → 4×4) as an optical matrix multiplier, with a link to the MZI learning simulation | **Started** (MZI-001) |
| 6 | Design-rule-checked GDS ready for an MPW run | Planned |
| 7 | Measurement plan and published measurement data | Planned |

Fabricating photonic chips requires a foundry. The realistic open path is to
share designs made in open PDKs and submit them to MPW runs, where many
designs share one wafer.

## Experiments

All experiments live in [`simulations/meep/`](simulations/meep/) and each has
its own workflow in [`.github/workflows/`](.github/workflows/). Workflow
artifacts expire after 90 days, so every result report is also kept in
[`results/`](results/), with a `provenance.json` that names the CI run and
commit it came from. [`results/README.md`](results/README.md) lists the key
numbers for every experiment.

| ID | What it establishes |
|----|---------------------|
| 001 | Meep runs reproducibly in CI with a locked environment (free-space smoke test) |
| 002 | Normalized 2D straight-waveguide / air-gap scattering with convergence check |
| 003 | Exploratory 2D 90° bend-radius comparison (aperture flux) |
| 004 | 2D guided-mode power audit of bends using eigenmode decomposition |
| 005 | Memory and runtime benchmark for bounded 3D simulations |
| 006 | Guarded 40×40×4 µm 3D capacity profile |
| 007 | First 3D dielectric waveguide bend comparison (aperture flux) |
| 008 | Temporal convergence of the 3D bend simulations |
| 009 | Grid-resolution sensitivity of the 3D bend simulations |
| 010 | 3D modal decomposition (odd-Z band 1) of bend ports, still with a finite-size Ez source |
| 011 | 3D **guided-mode** bend transmission: launched TE-like eigenmode, decomposed at both ports, validated by a straight reference |

### OPA-FDTD-011 results

Fundamental TE-like mode, index-1.8 core (0.8 × 0.4) in air, vacuum
wavelength 1.25 (Meep units), 90° bend:

| Case | Guided transmission (res 12 → 16) | Loss at res 16 | Aperture-flux ratio at res 16 |
|------|-----------------------------------|----------------|-------------------------------|
| Straight reference | 0.9996 → 0.9998 | 0.001 dB | 1.000 |
| Bend, radius 1.0 | 0.333 → 0.315 | 5.0 dB | 0.472 |
| Bend, radius 2.0 | 0.762 → 0.743 | 1.3 dB | 0.819 |

What this shows:

- The straight waveguide transmits 99.98 % in the guided mode, which
  validates the measurement method.
- Within this experiment, aperture flux **overestimates** guided
  transmission (0.472 vs 0.315 at radius 1.0) because it also counts radiated
  light that passes through the output aperture. The 007–010 numbers are not
  directly comparable: they use an Ez current, which excites the TM-like
  (odd-Z) polarization, and normalize to the straight input aperture flux.
- Guided reflection is about 0.00001 for both bends, measured after
  subtracting the straight-reference fields. Without that subtraction, leakage
  of the incident field into the discretized backward mode reads about 10–20×
  higher, comparable to the straight waveguide's own leakage floor.
- The low index contrast (1.8 vs 1.0) makes tight bends very lossy. Real
  platforms such as silicon (index ≈ 3.48) allow much tighter bends.
- Changing the resolution from 12 to 16 changes transmission by less than 0.02,
  but two resolutions do not prove convergence.
- Not yet checked: sensitivity to port-monitor size and PML thickness (mode
  confinement), more resolutions, and an independent mode-solver comparison of
  the effective index (n_eff ≈ 1.359). Until then these numbers are
  preliminary.

The full CI report is
[`results/opa-fdtd-011/result.json`](results/opa-fdtd-011/result.json); a local
run with the same locked environment agreed to within 2e-9.

## Circuit experiments

FDTD shows how light behaves inside one component. Circuit experiments treat
each component as a small complex matrix and ask what a whole circuit computes.
They live in [`simulations/circuit/`](simulations/circuit/), use only numpy from
the same locked environment, and run in seconds.

| ID | What it establishes |
|----|---------------------|
| MZI-001 | An ideal 2×2 MZI plus an output phase screen is a programmable 2×2 unitary matrix multiplier |

### OPA-MZI-001 results

A 2×2 MZI is two 50:50 couplers with an internal phase shifter θ between them
and an external phase shifter φ on one input. θ sets how power is split
(top-port output power = sin²(θ/2)) and φ sets the relative phase. With two
more phase shifters on the outputs, the circuit can realize **any** 2×2 unitary
matrix, which is the building block of the meshes used in optical AI
accelerators.

| Check | Max error |
|-------|-----------|
| Transfer matrix equals the closed form | 4e-16 |
| Unitarity (lossless) | 7e-16 |
| Power splitting follows sin²(θ/2) | 7e-16 |
| 1000 random unitaries + bar/cross/Hadamard programmed exactly | 2e-15 |
| Targets 1e-12 to 1e-4 rad from the bar and cross states | 7e-16 |
| Programmed circuit multiplies input vectors correctly | 2e-15 (relative) |
| Real 30° rotation weight applied to real inputs | 5e-16 |

All errors are at floating-point rounding level. As a sensitivity check, the same
settings on hardware with 48:52 instead of 50:50 couplers give errors of 0.04,
which shows why fabrication tolerance (OPA-MZI-002) matters.

Not included: loss, fabrication errors, wavelength dependence, and detection.
Photodetectors measure power |y|², not the complex field.

## Running locally

```bash
# Requires micromamba (or conda/mamba) on linux-64
micromamba create -n opa-fdtd --file simulations/meep/opa-fdtd-linux-64.lock.txt
micromamba activate opa-fdtd
python simulations/meep/bend_3d_launched_mode_v011.py   # writes results/opa-fdtd-011/result.json
python simulations/circuit/mzi_2x2_v001.py               # writes results/opa-mzi-001/result.json, < 1 s
```

New experiments should import shared geometry and measurement helpers from
[`simulations/meep/opa_common.py`](simulations/meep/opa_common.py).

## Contributing

Contributions are welcome. Add a new numbered experiment (`OPA-FDTD-NNN`)
with its own workflow, state its limitations in the result report, add a
row to the experiment table above, and archive the report in
[`results/`](results/README.md#adding-a-result).

## License

[MIT](LICENSE)
