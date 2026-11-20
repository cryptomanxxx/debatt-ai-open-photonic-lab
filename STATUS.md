# Project status — Debatt-AI Open Photonic Lab

*Last updated 20 November 2026. A one-page, plain-language summary for collaborators, fabrication facilities and funders. Details and evidence are linked; every number below comes from an archived, reproducible result in this repository.*

**In one sentence:** an independent, open laboratory that has built and verified a complete numerical design chain for a small programmable photonic matrix processor, and now needs access to fabrication to test its models against real devices.

## What exists today

- **Component simulations.** Meep FDTD/MPB studies of waveguides, bends and couplers ([results](results/README.md)).
- **Chip layouts.** A programmable 2×2 Mach–Zehnder interferometer (MZI) in the open SiEPIC EBeam silicon PDK that passes the official SiEPIC design-rule check (OPA-LAYOUT-002/003). An electro-optic 2×2 MZI in the Luxtelligence lnoi400 thin-film lithium niobate PDK (OPA-LAYOUT-005), passing 10/10 automated layout checks but **not** checked against the foundry's own design rules.
- **Circuit models.** A calibrated 4×4 programmable MZI mesh and a general 4×4 matrix layer (W = U·Σ·V†) built from pinned lnoi400 compact models, with a coherent I/Q readout and a partial power budget ([OPA-CIR final report](research/OPA-CIR-FINAL-REPORT.md)).
- **Component library.** Revision-pinned external components that keep layout geometry, simulated models and published measurements separate ([component library](components/README.md)).
- **Reproducibility.** Experiments run in GitHub Actions with locked environments; original outputs are archived with checksums.

## What we have learned (simulation only)

- A calibrated 4×4 mesh reproduces target matrices to about 2–4 % in simulation; the full matrix layer with modeled coherent readout has a worst-case error of 4.8 %.
- **Small meshes are not energy-efficient.** The partial budget gives about 4.4 pJ per complex multiply-accumulate at an assumed 10 Gvector/s, more than half of it in data converters. Converter cost grows with N, computation with N², so any advantage would need much larger meshes. The 4×4 mesh is a research vehicle, not an efficiency demonstrator.
- **WDM with fixed weights fails in our model:** three channels at 25 GHz spacing already give 13 % matrix error. Unequal optical path lengths are a hypothesis, not a demonstrated cause.
- **Simulation models need measurements.** Two published compact models we examined are not physically passive at most sampled wavelengths (a lnoi400 directional coupler at 201/201 points, a SiEPIC broadband coupler at 50/51), so they are quarantined ([LIB-005 review](research/OPA-LIB-005-E.md)).
- **No architecture beats electronics in our system study.** None of the modeled accelerator designs exceeded an assumed 3.5 TOPS/W electronic reference, and reliable 6-bit training was not established ([AG-PHOTONIC-003 report](antigravity/reproduction/AG-PHOTONIC-003/FINAL_REPORT.md)).
- Optical nonlinear activation remains a phenomenological model; electronic activation is the baseline ([OPA-NL final report](research/OPA-NL-FINAL-REPORT.md)).

## What we do not know

Real propagation, bend and coupling losses; fabrication tolerances; phase errors and drift; detector and converter performance; and whether a photonic accelerator of this kind can have an energy advantage at any scale. Nothing has been fabricated or measured by this project.

## Next physical step

A **small passive test chip** on a single material platform (silicon nitride, silicon or lithium niobate, depending on the accessible process):

- cutback waveguides and bend chains (propagation and bend loss);
- splitters/couplers and passive MZIs (splitting ratio, extinction);
- microring resonators (resonance, free spectral range, quality factor);
- optical input/output reference structures.

Measured with an external tunable laser and detector, and compared against predictions made before fabrication. Integrated lasers, amplifiers, detectors and active phase control are out of scope. Our cutback analysis is already validated on public SiEPIC measurement data (2.40 dB/cm, R² 0.97; [LIB-004](components/experimentally_validated/SiEPIC-PCM-2020-02-UW/README.md)).

## What we are looking for

- **Fabrication access** to an established passive photonic process, with its layer stack and design rules. No fabrication access is confirmed yet.
- **Optical characterization** (tunable laser, fiber alignment), or a partner laboratory that has it.
- **Research collaborators**, including for future European research consortia.

## What we offer

Open designs, simulation code, verification tooling and documentation; careful separation of simulation, layout and measurement evidence; and open publication of results wherever facility rules allow.

**Contact:** [debatt-ai.se](https://www.debatt-ai.se/) · Repository: [github.com/cryptomanxxx/debatt-ai-open-photonic-lab](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab)
