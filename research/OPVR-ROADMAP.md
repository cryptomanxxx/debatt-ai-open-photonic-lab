# OPVR — Open Photonic Virtual Reality

2026-11-26 · Long-term open hardware and software research vision, not an implemented headset or funding commitment.

## Architecture

Electronic CPU/GPU and memory provide tracking, application logic, shading, compositor and display. A detachable OPA-G accelerator may offload ray-box tests; OPA AI acceleration, OPA-M optical transport and OPA-W photonic model-weight storage are optional future interfaces, each requiring independent validation before integration. Start with an existing open XR runtime and conventional headset. Linux/Monado/OpenXR are candidate native stack; WebXR/WebGPU/WebAssembly are candidate web stack, subject to actual device and browser support. A browser does not automatically expose a custom accelerator: require a host driver/runtime and explicit secure integration. Use an open distribution catalog with signed releases, provenance, sandboxing and license metadata; free distribution is a goal, not a claim of zero operating cost.

| Phase | Deliverable and gate |
|---|---|
| OPVR-001 | Open system specification and electronic baseline; define target resolution, 72/90/120 Hz profiles, tracking and motion-to-photon measurements, thermal and battery budgets. |
| OPVR-002 | Chip 16 teaching demo and OPA-G-001 numerical baseline; independent reference tests. |
| OPVR-003 | OPA-G optical model and end-to-end accounting with matched graphics quality. |
| OPVR-004 | Process-qualified external test chip and bench verification; requires access and funding. |
| OPVR-005 | GPU/FPGA integration; measure data movement and frame-time tails. |
| OPVR-006 | Tethered headset with external accelerator; compare identical scene and render settings, dropped frames and motion-to-photon latency. |
| OPVR-007 | Miniaturization feasibility: package, laser containment, electrical safety, heat, mass, battery, EMC, optical safety and reliability. No wearable laser prototype before independent safety review. |
| OPVR-008 | Standalone hybrid prototype only after whole-system energy, thermal, safety and latency gates. |
| OPVR-009 | Open game distribution prototype; documented APIs, optional agent integration, security review and device compatibility matrix. Can proceed independently of optical hardware. |

The frame budgets at 72/90/120 Hz are approximately 13.89/11.11/8.33 ms; these are not motion-to-photon targets. Measure CPU, GPU, compositor, transfer, tracking, display and power separately. Compare optical versus electronic substitution on the same workload; do not infer headset benefit from component bandwidth. Evaluate sustained workloads, p95/p99 frame times, missed frames, image quality, battery and temperature.

Candidate open projects: https://monado.freedesktop.org/ , https://github.com/relativty/Relativty , https://github.com/HadesVR/HadesVR . Verify licenses, maintenance and device support before reuse. PIXEurope and Myfab are possible research access routes, not approved collaborations. Existing OPA roadmap priorities remain unchanged.

See [OPA-G](OPA-G-ROADMAP.md), [OPA-M](OPA-M-ROADMAP.md), [OPA-W](OPA-W-ROADMAP.md), [main roadmap](../PHOTONIC_RESEARCH_ROADMAP.md).


## Photonic-First Architecture (PFA) — exploratory research track

Added 2026-11-28. Long-term objective: a standalone, open-hardware and open-software VR/MR headset with a predominantly optical compute and image-data path, integrated photonic accelerators and nonvolatile PCM weight storage. This is a falsifiable research hypothesis, not a commitment to eliminate electronics or a demonstrated system. Existing OPVR-001–009 gates remain valid; the hybrid architecture is a comparator and possible intermediate implementation, not a mandatory final architecture.

### Comparative architectures and hypotheses

| Architecture | Definition |
|---|---|
| A — electronic reference | CPU/GPU/NPU, electronic memory, conventional sensors and display |
| B — hybrid | Electronic rendering and control, photonic AI or graphics acceleration, explicit conversion and transfer interfaces |
| C — photonic-first | Optical encoding, PCM-weighted tensor operations, optical activation/routing/buffering where feasible, neural rendering and optical display interface; electronics retained for control, safety and unsupported operations |

Hypotheses: resident PCM weights reduce weight traffic and static retention power; optical layer-to-layer propagation may reduce conversion overhead; whole-system energy may improve at matched image quality and latency. Null result: no advantage after including laser wall-plug power, insertion loss, amplification, encoding/decoding, calibration, memory, display and control. Never assume that speed of light implies negligible system latency.

### System partition and dependencies

Sensor/pose input -> optical encoding -> PCM tensor core (OPA-W) -> optical activation and dynamic state -> neural rendering (OPA-G) -> composition/display. OPA-M studies transport; frequency-comb/WDM research studies parallel channels; optical logic research studies routing and decisions. Retain a conventional safety/control plane. Direct sensor-light processing and optical-to-visible display mapping are separate unproven interfaces, not interchangeable with telecom-band PIC signals. PCM stores trained weights, not rapidly changing frame state; no per-frame weight rewriting is assumed. Neural denoising, upscaling, learned radiance-field inference and tracking are candidate workloads; Gaussian splatting also involves sorting, projection and compositing and is not simply matrix multiplication.

### PFA research milestones (independent of existing OPVR numbering)

| ID | Deliverable and exit gate |
|---|---|
| OPVR-PFA-001 | Reproducible A/B/C numerical baseline on fixed neural denoising/upscaling workload; publish assumptions and sensitivity analysis. |
| OPVR-PFA-002 | PCM tensor-core model and bench plan; compare MZI and microring/WDM options, GST and low-loss PCM candidates such as Sb2Se3/Sb2S3; quantify precision, retention, read disturb, programming energy, endurance and thermal crosstalk. |
| OPVR-PFA-003 | Cascaded optical activation study; quantify transfer curve, optical power, noise, fan-out and gain requirements against digital reference. |
| OPVR-PFA-004 | Dynamic optical state and routing study; compare delay-line/slow-light buffers and electronic memory; quantify delay-bandwidth product, losses, capacity, random access and refresh. Do not equate optical delay with RAM. |
| OPVR-PFA-005 | Integrate simulated optical rendering pipeline; compare image quality and temporal stability, include conversion boundaries and all power terms; progress to bench only with a credible budget. |
| OPVR-PFA-006 | Separate sensor and display interface bench studies; demonstrate encoding fidelity, visible-output mapping and calibration; no human exposure to experimental lasers before independent safety review. |
| OPVR-PFA-007 | Standalone feasibility assessment; package, mass, thermal limits, battery, safety, manufacturability and open interfaces. Physical prototype conditional on all applicable prior gates, funding and fabrication access. |

### Bottleneck register

| Bottleneck | Measurement / mitigation candidate |
|---|---|
| Nonlinear activation | Optical transfer curve, cascading, saturation power and distortion |
| Optical loss and amplification | Per-stage dB budget, laser wall-plug efficiency, amplifier noise and heat |
| Dynamic memory | Capacity, access time, retention/refresh, delay-bandwidth and energy |
| PCM scaling | Cell density, yield, levels/precision, programming energy and endurance |
| Integrated lasers | Coupling, efficiency, stability, lifetime and containment |
| Optical logic | Correctness, cascadability, footprint and energy versus CMOS |
| Routing and fan-out | Switch losses, contention, reconfiguration time and crosstalk |
| Sensors | Spatial/spectral encoding, coherence, noise and tracking accuracy |
| Display | Visible wavelength mapping, pixel addressing, stereo fidelity, brightness and eye safety |
| Thermal stability | Drift, calibration overhead and sustained performance under realistic temperature variation |

### Benchmark and reproducibility protocol

Use identical scene, stereo resolution, model, input poses, output-quality threshold and refresh profiles for all architectures. Report joules/frame, total watts, frame-time p50/p95/p99, motion-to-photon latency, dropped frames, PSNR/SSIM and temporal artifacts, tracking error, conversion count and energy, memory traffic, peak/sustained temperature and battery runtime under declared battery capacity. Include lasers, drivers, DAC/ADC, detectors, amplifiers, tuning, programming amortization, control, sensors, display and power conversion. Separate measured, simulated and assumed quantities; publish uncertainty ranges and negative results. No extrapolation from isolated optical MAC energy to headset battery life. Start with software simulation, then component bench tests, then integrated bench; wearable prototype is conditional.

### Open hardware and software

Publish source, schematics, HDL, optical layouts where licensing permits, mechanical CAD, bill of materials, interfaces, drivers, simulator configurations, calibration and test data with explicit licenses and provenance. Document any proprietary PDK, firmware or fabrication restrictions rather than calling unavailable components open. Maintain OpenXR-compatible software interfaces where practical; expose a documented, permissioned SDK/API for human and agent developers. Evaluate security, privacy, optical and electrical safety independently. PIXEurope is a potential fabrication/access route, not a confirmed partnership for this headset.

### Initial literature anchor

Feldmann et al., *Parallel convolutional processing using an integrated photonic tensor core*, Nature 589, 52–58 (2021), https://doi.org/10.1038/s41586-020-03070-1 — component-level precedent for PCM and wavelength-multiplexed tensor processing; not evidence of an all-optical VR system.

