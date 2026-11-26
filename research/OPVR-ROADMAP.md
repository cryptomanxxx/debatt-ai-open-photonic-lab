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
