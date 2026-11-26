# OPA research roadmap: photonic computing beyond linear layers

Date: 2026-11-17. Status: proposed research, not implemented or validated.

## Motivation and scope

The [AI Andrew video](https://youtu.be/CJd37oe0quY), *Germany's NEW Photonic Chip JUST Made NVIDIA & AMD GPUs Look Like a JOKE!* (42:15), provides leads about Q.ANT's hybrid photonic accelerator and Akhetonics' all-optical digital architecture. The video is a secondary source, not evidence of measured OPA performance. Its commercial claims require primary-source verification before being cited as results. Timestamps below refer to the supplied transcript.

The near-term OPA target remains a hybrid accelerator with electronic memory and control and optical matrix–vector multiplication (MVM). All-optical nonlinear computation is a research extension; all-optical digital logic is a separate, longer-term branch. Do not conflate inference, hybrid training and fully optical training.

## Existing foundations and gaps

- [MZI-001–003](results/README.md): programmable MZI, impairments/calibration and Clements mesh; precision is already studied at the component/mesh level.
- MOD-006 and MOD-007: hybrid training and nonlinear multilayer classification with **electronic** tanh and digital backward updates. Extend these rather than duplicating them.
- EO-001–002 and LAYOUT-004–005: TFLN electro-optic modeling and lnoi400 layouts already exist. Material comparison should build on these; an electro-optic modulator is not by itself an all-optical activation.
- FDTD and coupler studies already address guided loss and convergence. Extend toward a cascaded link budget rather than repeating standalone bend experiments.

See [README](README.md), [experiment registry](simulations/experiments.json) and [results](results/README.md) for authoritative current status. Proposed identifiers below are placeholders, to be checked against the registry before implementation.

## Prioritized research backlog

| Priority | Proposed track | Question and initial deliverable | Source lead |
|---|---|---|---|
| 1 | OPA-NL-001 | Can a physically motivated nonlinear optical transfer function support a second optical MVM? Compare an ideal activation, electronic baseline and optical candidate on identical inputs. | 11:44–14:04; 36:16–36:38 |
| 2 | OPA-SYS-001 | Under what assumptions does a hybrid chain reduce end-to-end energy or latency? Produce a transparent parameterized energy/latency model and break-even sweeps. | 34:28–38:15 |
| 3 | OPA-PRECISION-001 | How do noise, drift, quantization and loss affect multilayer task accuracy? Extend MOD-007/MZI-002 rather than recreating them. | 37:16–37:45 |
| 4 | OPA-GAIN-001 | When does optical amplification help a cascaded waveguide path, and what does it cost in noise and electrical energy? | 06:02–06:15; 27:50–28:08; 36:46–37:07 |
| 5 | OPA-MAT-001 | Compare Si, SiN and TFLN on matched functional requirements, using process-specific parameters and existing EO/layout work. | 10:57–11:44; 18:59–19:14 |
| 6 | OPA-DELAY-001 (provisional) | Can delay lines or recirculating loops preserve a pulse for a useful short interval? | 24:21–24:51; 27:35–27:50 |
| 7 | OPA-LOGIC-001 | Can optical logic be cascaded with sufficient regeneration, fan-out and timing margin? | 21:46–25:53 |

### Nonlinear activation and multilayer chain

Start with a bounded circuit-level study using a documented transfer model (e.g. Kerr ring with detuning and loss, saturable absorption, or nonlinear interferometer). Distinguish input power, complex field and encoded signed values. An intensity-only transfer is not automatically ReLU/tanh/GELU on signed amplitudes; explicitly specify encoding, bias, phase preservation or re-encoding, normalization, and whether any O/E/O conversion occurs. Compare two optical MVM layers separated by the candidate against electronic activation and a linear-only control, with paired data/seeds and a NumPy or PyTorch reference. Report transfer curves, task accuracy/error, insertion loss, required optical power, operating range, bandwidth and noise sensitivity; unsupported quantities remain unknown. An ideal mathematical activation is a behavioral baseline, not proof of a realizable device. Negative outcomes are valid.

Only after a viable compact-model study, pursue component-level simulation with independently sourced material constants and appropriate nonlinear solvers, convergence and power normalization. Do not assume existing linear FDTD runs validate nonlinear dynamics.

### End-to-end system accounting

**First implementation: OPA-SYS-001 ([completed accounting audit](results/opa-sys-001/README.md)).** The existing AG003
reproduction supplies an archived parameter set and candidate to audit.
This limited accounting experiment is the bridge between AG003-ENERGY-001
(the proposed audit) and OPA-SYS-001; no duplicate energy experiment is
needed. It complements MOD-005 rather than rerunning its tiled inference
sweep. The priority-1 nonlinear activation track remains a separate planned
experiment; this audit continues the already active AG003 work. The AG003 correction, rerun and convergence audit are now complete; see the [final report](antigravity/reproduction/AG-PHOTONIC-003/FINAL_REPORT.md). Physical validation remains pending. The six other tracks remain planned.



Define boundaries separately: optical core, accelerator card, host-inclusive system. Include wall-plug laser efficiency, coupling/splitting/propagation loss, modulators and drivers, DAC/ADC, detection/TIA, gain, tuning/calibration, memory traffic, host and idle overhead; avoid double counting. Report energy per inference or matched operation, throughput, latency, precision, workload shape and batch size; compare at matched accuracy. Sweep uncertain inputs with documented provenance and ranges. Separate assumed, simulated, datasheet and measured values. No CPU simulator runtime is evidence of physical photonic speed or energy.

The transcript's 30 W chip versus 150 W card and its different 50x comparisons (34:53–37:07) illustrate why boundaries and baselines matter; these are unverified reported claims, not OPA parameters.

### Precision and noise

Reuse paired MOD-007 baselines and MZI calibration models. Sweep effective quantization (e.g. 4/6/8 bits), phase noise, detector noise and correlated thermal drift, separating static fabrication draws from dynamic noise. Report per-layer errors, held-out accuracy, calibration overhead and uncertainty across seeds. Compare noise-aware hybrid training against digital training plus optical deployment; do not claim optical backpropagation.

### Gain and optical link budget

Model propagation and insertion losses in dB, gain saturation, ASE/noise and receiver SNR. Compare passive, amplified and regeneration cases under identical launch conditions; include electrical pump/drive costs. Semiconductor optical amplifiers and rare-earth-doped waveguides are candidate mechanisms, not assumed available in each PDK. Provide an educational Chip 10 example only after equations and assumptions are documented; distinguish optical power at the laser, at the ring and at the receiver.

### Materials

Compare matched wavelength, mode/polarization, insertion loss, footprint, modulation efficiency and relevant bandwidth using process-specific cross sections and parameter provenance. Include existing Si/SiO2 and lnoi400 work; consider SiN where relevant to low-loss routing and combs. Distinguish Pockels modulation from optical intensity-dependent nonlinearity; do not assume all platforms support integrated gain or a common fabrication process.

### Optical short-term memory

Compare straight/spiral delay lines and recirculating loops. Track group delay, pulse broadening, round-trip loss, coupling, dispersion and usable retention at a defined receiver threshold; include amplification noise if present. Use a no-loop reference and test multiple round trips. This is transient storage, not a replacement for electronic DRAM or persistent model weights.

### Digital optical logic

Treat as exploratory and distinct from the hybrid AI path. Begin with truth tables, then two-stage cascade, contrast/noise margin, fan-out, power, timing and regeneration. A passive interference demonstration alone does not establish cascadable logic. Review the Akhetonics one-instruction architecture and delay-line memory paper before selecting a mechanism; a two-bit demonstrator does not establish a practical general-purpose computer.

## Evidence and implementation rules

1. Verify primary literature, datasheets and independent benchmarks; record URLs/DOIs, dates, workload, precision and measurement boundaries. Leads: Akhetonics' 2024 all-optical processor paper; Lightmatter's April 2025 Nature paper; Q.ANT/LRZ and Jülich results, IONOS access, next-generation disclosures, IMS CHIPS process. These are leads, not verified results or confirmed hardware access.
2. Use existing numbered experiment and CI conventions, locked environments and registered dependencies. Specify hypothesis, controls, acceptance criteria, seeds, units and artifacts before running. Archive reports with provenance. Do not change historic results.
3. Keep behavioral simulations, electromagnetic simulations, PDK/DRC status, fabrication and measured hardware evidence distinct. Do not claim fabrication readiness or speed/energy advantages without matching evidence.
4. Keep the current component/layout roadmap active. Start with a small nonlinear multilayer feasibility experiment after reviewing current work; advance tracks only when dependencies are met. Update this backlog when evidence changes. No new experiments, hardware purchases or live external AI calls are authorized by this document.


## 2026-11-19 phase decision: OPA-CIR takes priority

The current OPA-NL phase closes with [NL001–NL021 final report](research/OPA-NL-FINAL-REPORT.md), subject to the final archive audit. NL021 confirmed the frozen LO3 Margin16 endpoint at 42 ps in the specified numerical model, while LO2 missed the 96% gate. No NL022 is planned. Prioritize OPA-CIR-001: verify circuit assembly against existing MZI results and progressively connect physics-derived complex S-parameters to circuit models. Keep electronic activation as the hybrid baseline and nonlinear dynamics as a conditional optional block. Component research should respond to system bottlenecks; retain fabrication and measurement roadmap. This is prioritization, not evidence of an implemented circuit simulator or hardware.


### Reuse-first component strategy

Use the [OPA component library](components/README.md) before proposing custom component optimization. OPA-CIR-001 remains the next main experiment; prioritize system-level requirements and reuse pinned PDK models where appropriate. Keep measurement, geometry, DRC, compact-model validity and fabrication qualification separate. No cross-process connection without an explicit interface.

## CIR001–008 system handoff (2026-11-19)

CIR001–007 implementations are merged. CIR006's frozen WDM grid failed the multicarrier 5% screen; single 1550 nm carrier is the baseline, not a general rejection of WDM. CIR007 admitted four conditional interface settings. [CIR008](research/OPA-CIR-008.md) proposes partial integrated accounting on those exact settings. After verification, archive evidence and consolidate a phase report before choosing system-driven remediation. Keep electronic activation, physical attenuator/encoder/receiver validation and fabrication as open work. No measured hardware claim.

## CIR phase closure and next research decision (2026-11-19)

[OPA-CIR Final Research Report](research/OPA-CIR-FINAL-REPORT.md) consolidates eight merged experiments, 63 numerical checks and the permanent evidence archive (PR221). Freeze CIR001–008 on report audit and merge. Single-carrier 1550 nm, nominal 8-bit interface is the conditional baseline, not a fabricated accelerator. WDM remains unresolved. Proposed next priorities: process-access and passive geometry/model-to-layout closure, physical attenuator/encoder/receiver validation, bounded WDM attribution and matched system economics. Retain electronic activation, the closed NL phase and fabrication roadmap. No new experimental series authorized by the report alone.

## OPA-LIB component evidence phase (2026-11-19)

Before selecting FAB001 components, establish a revision-pinned external library. LIB001 imports original SiEPIC core GDS; LIB002 targets Luxtelligence geometry; LIB003 complex S datasets; LIB004 available licensed measurement data; LIB005 matched comparisons; LIB006 FAB001 selection. Only LIB001 is implemented by this PR. Keep silicon and TFLN separate, and distinguish original files, PCell-generated geometry, simulations, measurements and qualification. No fabrication commitment.

### LIB002 execution

[LIB002](components/external/Luxtelligence/lnoi400/README.md) selects seven lnoi400 PCell references, at the same revision as CIR002–008. Export and audit via locked CI, then archive exact generated outputs. No new DRC, measured or S-parameter claim. Continue to LIB003 after verified archive.

### LIB003 execution

[LIB003](components/external/Luxtelligence/lnoi400/s_parameters/README.md) imports exact upstream simulated MMI and directional-coupler polynomial models at the LIB002/CIR revision. Audit full four-port complex matrices at 201 wavelengths, preserve nonpassive fits without modification, quarantine them from passive circuits and archive sampled outputs after CI. No measured validity or WDM remediation claim.

### LIB004 execution

[LIB004](components/experimentally_validated/SiEPIC-PCM-2020-02-UW/README.md) imports five exact original SiEPIC TE spiral cutback scans and independent analysis. Derive effective loss from detector 2 with explicit regression limitations, no phase or geometry-equivalence claim. Preserve measured bytes and archive derived CI results. Additional source leads require file-level evidence and license. Do not calibrate TFLN from silicon measurements.

## Long-term vision: an all-optical OPA (2026-11-21)

**Vision.** In the long term, Debatt-AI's OPA should keep signals optical across all layers of a neural network, from the first optical matrix–vector multiplication to the last, without optical-to-electrical-to-optical (O/E/O) conversion between layers. This is a research direction, not a current capability. The near-term target remains the hybrid accelerator described above, and nothing in this section changes the current priorities: process access and a passive test chip come first.

**Why it matters.** In the hybrid baseline (CIR001–008) every layer passes through detection, ADC, electronic activation, DAC, driver and modulator. In the partial CIR008 budget, data converters, drivers and receivers account for roughly 70 % of the 0.61 W subtotal for a single 4×4 matrix layer (DAC, ADC, input drivers and TIA: 0.44 W). An all-optical chain would pay that conversion cost only at the system input and output, so the saving grows with network depth.

**What it does not remove.** An all-optical design does not make a small mesh as efficient as a large one, and it adds new costs:

1. *System boundary.* Input data and results still come from and return to electronic memory and hosts. Conversion at the boundary remains and is still amortized over N² operations per N inputs, so mesh size N continues to matter.
2. *Photon budget.* Each output must be detected with enough optical power for the required precision (shot and receiver noise). Laser energy is shared across all operations in a mesh, which again favours larger meshes.
3. *Accumulated loss.* Without conversion between layers there is no regeneration. Cascades need optical gain or regeneration, which costs electrical power and adds noise (see OPA-GAIN-001).
4. *Optical activation.* Intensity-dependent optical nonlinearities are weak and usually need high optical power. The OPA-NL phase established only a phenomenological model, without a calibrated material or a fabricated device; electronic activation remains the baseline. A practical, low-energy, cascadable optical activation is the key enabling component and an open problem across the field.
5. *Weights and control.* Weights are stored and phase shifters are held electronically; hold power and calibration remain.

**Staged path and gates.** Each stage requires measured evidence from the previous one; none is authorized by this section.

| Stage | Milestone | Gate before the next stage |
|---|---|---|
| 1 | Passive test chip (loss, couplers, MZIs, rings) | Measured spectra compared with pre-fabrication models |
| 2 | Programmable MZI mesh on one platform | Measured matrix accuracy, drift and calibration |
| 3 | Two optical layers cascaded without O/E/O | Measured link budget, noise and regeneration needs |
| 4 | Optical activation with a real material or device | Measured transfer curve, power, speed and cascadability |
| 5 | All-optical multilayer demonstrator | Matched-accuracy, matched-boundary energy comparison against the hybrid baseline and electronics |

**Research questions to keep open.** How does energy per operation scale with mesh size N and network depth for hybrid versus all-optical chains at matched accuracy and system boundary (a future OPA-SYS extension)? Which activation mechanism, if any, meets the power and cascadability requirements on an accessible platform (a future reopening of OPA-NL, which its final report allows only when a concrete system need is identified)? Does the all-optical digital branch (OPA-LOGIC-001) or the analog branch offer the more realistic route?

**Candidate nonlinear mechanisms (literature survey, not evaluated by this project).** Photons do not interact directly; an optical nonlinearity needs a material response, which is usually weak and therefore costs optical power. A useful activation must combine low switching energy, speed, cascadability (the output can drive the next stage) and on-chip manufacturability. No mechanism below has been shown to meet all four in an AI accelerator.

| Mechanism | Principle | Strength | Main limitation |
|---|---|---|---|
| Kerr (χ³) in Si or SiN | Intensity-dependent refractive index | Near-instantaneous | Weak; needs resonant enhancement; two-photon and free-carrier absorption in silicon |
| χ² in thin-film lithium niobate | Phase-matched second-harmonic generation and its reverse in periodically poled waveguides | Strong and fast; same material family as lnoi400 | Poling and dispersion engineering; demonstrated with ultrashort pulses |
| Saturable absorption (graphene, 2D materials) | Absorption drops at high intensity | Simple transfer shape (modelled phenomenologically in OPA-NL) | Insertion loss, recovery time, heterogeneous integration |
| Phase-change materials (e.g. GST) | Switching between material phases | Non-volatile; suited to weights or memory | Slow and coarse for activations |
| Semiconductor optical amplifiers (III-V) | Gain saturation and cross-gain modulation | Provides gain as well as nonlinearity | Electrical power; III-V integration |

**Practical intermediate step: optoelectronic nonlinearity without data converters.** In the CIR008 budget the dominant cost is the digital ADC/DAC chain, not optical-to-electrical conversion as such. A photodiode and modulator placed together on chip can apply an analog nonlinear function to the optical field without digitizing the signal (light → photodiode → small analog circuit → modulator → light). This removes the most expensive converters while remaining feasible with existing device types, and is the most realistic medium-term option for OPA. It is not all-optical.

| Horizon | Activation approach |
|---|---|
| Now | Electronic activation (current baseline) |
| Medium term | On-chip optoelectronic nonlinear unit, no ADC/DAC between layers |
| Long term | All-optical nonlinearity, e.g. χ² in thin-film lithium niobate |

When OPA-NL is reopened, start from a real mechanism with published measured data, not a phenomenological cavity, consistent with stage 4 of the staged path above.

**Sources.** Akhetonics and similar all-optical efforts are leads for primary literature, not verified results (see Evidence and implementation rules). Claims of all-optical advantage require primary sources with stated workload, precision and measurement boundary.

- M. Kissner, L. Del Bino, F. Päsler, P. Caruana and G. Ghalanos, "An All-Optical General-Purpose CPU and Optical Computer Architecture", *Journal of Lightwave Technology* (2024), DOI [10.1109/JLT.2024.3458459](https://doi.org/10.1109/JLT.2024.3458459), [arXiv:2403.00045](https://arxiv.org/abs/2403.00045). Akhetonics' primary paper: a URISC architecture with a 2-bit demonstrator CPU and a photonic integrated circuit implementation of all-optical digital data processing. It concerns the digital branch (OPA-LOGIC-001), not analog MZI matrix–vector multiplication. The company's further stated targets (THz clock rates, 10–100× energy efficiency, non-volatile optical memory, a full-scale prototype) are not established by this paper and remain unverified. The company's own website (secondary source, summarized 2026-11-21, not independently read) describes keeping computational data optical while lasers, amplifiers and control remain electrically powered, switching based on integrated nonlinear materials (2D and III-V), and optical analog-to-digital conversion; these points are consistent with the limits listed above.
- Q. Guo, R. Sekine, L. Ledezma et al. (corresponding author A. Marandi), "Femtojoule femtosecond all-optical switching in lithium niobate nanophotonics", *Nature Photonics* 16, 625–631 (2022), DOI [10.1038/s41566-022-01044-5](https://doi.org/10.1038/s41566-022-01044-5), [arXiv:2107.09906](https://arxiv.org/abs/2107.09906). Cavity-free χ² nonlinear splitter in thin-film lithium niobate; the published abstract reports switching energies down to 80 fJ and switching times of about 46 fs (the preprint states different figures; cite the published version). Pulsed operation of a single switch, not a cascaded neural-network activation.
- S. Bandyopadhyay, A. Sludds, S. Krastanov et al. (D. Englund), "Single-chip photonic deep neural network with forward-only training", *Nature Photonics* (2024), DOI [10.1038/s41566-024-01567-z](https://doi.org/10.1038/s41566-024-01567-z), [arXiv:2208.01623](https://arxiv.org/abs/2208.01623). Silicon photonic chip integrating coherent matrix units with on-chip nonlinear optical function units (photodiode-driven modulation, no off-chip amplifier); a three-layer, six-neuron network with reported 410 ps latency. An example of the optoelectronic intermediate step, not all-optical nonlinearity. Details beyond the abstract are not independently checked here.

## OPA-M · Open Photonic Memory Interconnect (2026-11-24)

[Research track and phase gates](research/OPA-M-ROADMAP.md) · [OPA-M-001 modeling protocol and literature](research/OPA-M-001.md)

OPA-M studies digital links between electronic memory and AI accelerators. The initial work builds on Chip 12's existing OPA-MEM-001 kernel, comparing electrical and optical transport at matched payload and independently limiting accelerator ingress. OPA-M-001 is active at the analytical stage. Bank architecture, single-lane optics, WDM, layout, endpoint integration, software and physical validation have gated plans. Optical short-term storage retains its existing backlog priority under the provisional ID OPA-DELAY-001. The existing CIR, LIB and passive test-chip priorities remain in force.

## OPA-W · Open Photonic Weight Memory (2026-11-24)

[Research track and phase gates](research/OPA-W-ROADMAP.md)

OPA-W investigates persistent, optically accessible AI model weights and photonic in-memory computing. Its long-term hypothesis is that scalable stationary weights may reduce repeated weight movement by participating directly in optical matrix operations. This is distinct from transient OPA-DELAY-001 storage and OPA-M digital memory transport; electronic RAM remains the working-memory baseline. Nine gated phases cover materials, multilevel cells, addressable arrays, parallel readout, in-memory MVM, 3D/modular architectures, million- and billion-weight feasibility, and physical validation. All are planned; no experiment is registered or authorized here. Existing CIR, LIB, OPA-M and passive test-chip priorities remain in force. Proposed Chips 13–15 are educational concepts, not implemented devices.


## Photonic graphics and open XR (planned)

[OPA-G research roadmap](research/OPA-G-ROADMAP.md) · [OPVR research roadmap](research/OPVR-ROADMAP.md) · [Chip 16 educational prototype](web/chip16/README.md). OPA-G studies optical ray-box intersection acceleration; OPVR proposes a gated hybrid photonic XR architecture. Chip 13–15 retain their OPA-W reservations. Chip 16 is a standalone 2D numerical teaching prototype, not a physical optical model or published Site feature. [OPA-G-001](research/OPA-G-001.md) passed 30/30 numerical checks; [CI evidence archive](results/opa-g-001/provenance.json) includes exact JSON and CSV. Later phases remain planned; existing priorities are unchanged.
