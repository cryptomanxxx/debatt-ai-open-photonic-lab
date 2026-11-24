# OPA-M-001 · AI Inference and Memory Bottleneck Modeling

**Status:** active, with a reproducible first analytical sensitivity study. Electronic trace calibration and optical hardware validation remain open. The [OPA-M roadmap](OPA-M-ROADMAP.md) specifies the follow-on gates.

## Question and experimental design

At fixed workload, capacity and delivered precision, which transport improvement would move the bottleneck, and what dynamic optical energy per delivered bit would break even at the system boundary? Chip 12's [OPA-MEM-001 methodology](OPA-MEM.md) is the teaching baseline. The new study reuses its decode kernel, tracks a separate accelerator ingress ceiling, and compares three paths per case:

1. Electronic PCIe at the baseline encoder and payload efficiency.
2. WDM with line rate scaled to match the PCIe payload ceiling using the same channel count and assumed WDM payload efficiency.
3. A wider WDM setting using the baseline line rate.

All three share model, checkpoint precision, report token count, KV assumptions, placement, host memory/storage/controller, accelerator local memory and compute. The eleven deterministic cases isolate SSD, host RAM, controller, accelerator ingress, local accelerator memory, optical budget failure and VRAM residency; include a 405B stream and same-inventory 235B dense/MoE controls with different expert overfetch. There are 33 path/scenario rows. Both optical profiles are subjected to the Chip 12 power, spectrum and spacing screens. The matched-rate comparison holds receiver sensitivity fixed by construction. It isolates the assumed transport service, so it cannot predict the behavior of a real transceiver when its rate changes.

## Additional equations and units

All GB are decimal and rates are useful GB/s unless stated. Let W be logical bytes converted to GB crossing the host-to-accelerator link per token, B_i the independent accelerator ingress payload ceiling and T the number of decoded tokens. Define S as the largest host-stage service time (storage, host RAM, controller and transport) from the original model.

- Ingress service t_i = W/B_i. For ideal pipelining the host transfer cost increases by Δt = max(0, t_i − S), preserving the parent model's optical flight term. Each token therefore costs t_base + Δt. This ingress cap represents a receive/write or fabric path. It has no independent cache simulation and is not a fitted L2 throughput model.
- Effective host transfer = W / adjusted transfer seconds while payload moves. Decode tokens/s are the reciprocal of adjusted seconds/token. SSD GB/token, host GB/token, link GB/token, active weights, peak KV capacity and local KV traffic remain independently exported. Local weight/KV access, compute and other costs keep the original serialized teaching boundary.
- Extend the static host platform and, when active, the optical pump plus bias energy by their assumed watts × T × Δt. All bytes and dynamic coefficients stay fixed. Energy records separate storage, host memory, link, local memory, compute and platform. J/output token = total J/T. Optical link pJ/payload bit includes bias. Unavailable comparisons and metrics without transferred payload are null/blank.
- With N = 8×10⁹×W×T payload bits, optical dynamic pJ/payload bit at system energy break-even is p_current + (E_pcie − E_opt)/(N×10⁻¹²). This varies only the dynamic link coefficient at the predicted workload/bandwidth. A negative value means the modeled fixed costs alone exceed the electronic comparator. Include both link and system boundary in measurements.

The inherited warm uniform expert activity, layer sizes, optional partial weight residency, fixed KV geometry, ability checks, assumed efficiencies and static powers are teaching assumptions, not calibrated device parameters. Return signals, receive DMA contention, accelerator ingress dynamic power, thermal and clock coupling, protocol loss and dropped/retried packets need independent characterization. The numerical outputs exclude cold startup, prefill, batching, training and hardware cost. No BER is computed from a receiver sensitivity threshold.

## Acceptance and calibration

The automated tests require equivalent payload service for a matched-rate substitution, isolated bottleneck conservation, positive/finite input rate checks, clear blocked/resident cases, MoE traffic accounting and energy break-even closure. No positive speedup is required for a research result to be publishable.

Next within M-001, pick a small open dense model and a sparse MoE model, pin inference runtime and checkpoint licenses, and calibrate only after capturing an accessible electrical baseline. Capture memory-resident and offload regimes separately. Sweep batch 1 first, context and output length, then controlled larger batches. Record pinned model/backend/hardware/driver, capacities, actual host and GPU bytes, disk reads, latency distributions, accelerator utilization, cache/ingress activity where observable, and synchronized power. Keep cold load, prefill/TTFT, and warm decode separate. Use at least one held-out context or traffic pattern to report signed and absolute prediction errors and uncertainty. Record unknown counters as unavailable. Use predicted link/energy break-even intervals for M-002/003 only after identifying which assumptions dominate. Qualify affordability later from actual components, calibration effort and access, with uncertainty and geographic context.

Run locally from the repository root:

```sh
node --test simulations/interconnect/memory-bottlenecks.test.mjs
node simulations/interconnect/run_m_001.mjs
```

The `opa-m-001` registry entry runs these and writes `results/opa-m-001/result.json` and `results.csv`. JSON contains settings, coefficients, blocked reasons, breakdowns and evidence status. CSV contains the cross-architecture comparison. The shared workflow records the runner and dependencies. The original [CI report](../results/opa-m-001/result.json), [comparison CSV](../results/opa-m-001/results.csv) and [provenance](../results/opa-m-001/provenance.json) are archived byte-for-byte.

## Literature review

### Optically connected HBM

Ou, Zhang, Rovinski, Wentzlaff and Batten, *Optically Connected Multi-Stack HBM Modules for Large Language Model Training and Inference*, IEEE Computer Architecture Letters 24(1), 49–52 (2025), [DOI](https://doi.org/10.1109/LCA.2025.3540058), [Cornell-hosted paper](https://www.csl.cornell.edu/~cbatten/pdfs/ou-optical-mem-llm-cal2025.pdf), §§ II–III, Figures 3 and 6. The proposed architecture replaces six on-package HBM stack positions with electrical/photonic interface pairs on an A100-class compute package. Fiber connects to distinct HBM2e packages. The example uses 64 wavelengths at 16 Gb/s on each signal fiber and specifies 576 GB and 12 TB/s aggregate memory capacity/bandwidth. These are design figures, with more memory devices and a different packaging topology than the electrical reference.

Figure 6 reports **per-layer simulations**, batch 8, averaged over the tested contexts. With the baseline 7 TB/s L2, mean decode gains are 1.53× (175B) and 1.67× (1T). Raising modeled L2 bandwidth to 24 TB/s gives 3.17× and 4.23×, with approximately 1.14× mean prefill gain. The training result is a model FLOPs utilization improvement of up to 1.4× for the studied configuration. The paper leaves end-to-end inference and packaging economics for future work. The numbers do not measure a link, show lower wall power or forecast a consumer PCIe/NVMe retrofit. OPA-M uses the architectural lesson about bandwidth inversion, exercising an independent receive-side ceiling. The current study does not reproduce the authors' A100 or HBM system.

### Primary evidence map

| Topic and source | Evidence and consequence |
| --- | --- |
| [Beamer et al., PIDRAM, ISCA 2010](https://people.eecs.berkeley.edu/~krste/papers/pidram-isca2010.pdf), [Anderson et al., OFC 2018](https://doi.org/10.1364/OFC.2018.Tu3F.3), [Wu & Bergman, OFC 2025](https://lightwave.ee.columbia.edu/sites/lightwave.ee.columbia.edu/files/content/docs/Papers/2025/Wu_SiPAM.pdf) | Memory disaggregation ranges from architecture proposals to experimental CPU/memory-node links. Anderson reports 10 Gb/s streams in a silicon photonic connection. SiPAM evaluates a resource-allocation and optical switch topology. Pooling or switching results do not determine decode performance at a target endpoint. |
| [Jørgensen et al., Nature Photonics 2022](https://doi.org/10.1038/s41566-022-01082-z), [Liang et al., CLEO 2026](https://doi.org/10.1364/CLEO_SI.2026.STH1F.4) | Microcomb transmission and integrated WDM switching are precedents for M-004. Jørgensen's 1.84 Pbit/s is measured across 223 wavelengths and 37 fiber cores; the scope differs from a short memory link. |
| [IBM IEDM 2025 CPO module](https://research.ibm.com/publications/co-packaged-optics-module-with-single-mode-polymer-waveguide), [56 Gb/s SiPh/CMOS transceiver, IEEE JSSC 2026](https://doi.org/10.1109/JSSC.2026.3655295) | Polymer routing/packaging and digital receiver/driver integration are distinct physical problems. The latter reports BER below 10⁻¹² at −11 dBm RX OMA and 2.8 pJ/bit for its tested optical link. The number does not include the memory workstation; preserve receiver conditions and boundary before reusing data. |
| [Intel OCI demonstration](https://www.intel.com/content/www/us/en/newsroom/news/intel-unveils-first-integrated-optical-io-chiplet.html), [Ayar Labs TeraPHY](https://ayarlabs.com/teraPHY/), [Lightmatter Passage](https://lightmatter.co/Products/), [Marvell/Celestial AI Photonic Fabric](https://www.marvell.com/company/newsroom/marvell-completes-acquisition-of-celestial-ai.html) | Intel's vendor-reported CPU co-package demo carried live traffic on a link rated up to 4 Tb/s bidirectionally. Ayar describes optical chiplets, UCIe attachment and external multi-line lasers. Passage describes photonic packaging and separate sources. Celestial AI's Photonic Fabric targets scale-up links. These are architecture and product disclosures with different directions, ports and payload definitions. They establish neither OPA performance nor pricing/access. |
| [FlexGen, ICML 2023](https://proceedings.mlr.press/v202/sheng23a.html), [Splitwise, ISCA 2024](https://www.microsoft.com/en-us/research/publication/splitwise-efficient-generative-llm-inference-using-phase-splitting/), [PagedAttention, SOSP 2023](https://arxiv.org/abs/2309.06180), [Switch Transformers, JMLR 2022](https://www.jmlr.org/papers/v23/21-0998.html), [MLCommons Power](https://mlcommons.org/working-groups/benchmarks/power/) | Offload scheduling and batching, different prefill/decode regimes, KV-cache allocation and sparse expert routing all affect transfer volume and energy. Separate latency from batched throughput and report metered energy boundaries. |
| [Ramulator 2, IEEE CAL](https://doi.org/10.1109/LCA.2023.3333759), [PCI-SIG PCIe 6.0](https://pcisig.com/pci-express-6.0-specification) | M-002 can model channel timing with pinned DRAM configurations covering DDR5, LPDDR5, GDDR6 and HBM3. PCIe physical rates require one-way and encoding/protocol normalization before comparisons. |

### Open runtime candidates

| Runtime | What to instrument in OPA-M-007 |
| --- | --- |
| [AirLLM](https://github.com/lyogavin/airllm) | Layer/expert streaming and packed transfer, prefetch distance, SSD/RAM cache behavior and stalls. Re-run with a fixed checkpoint; release results are workload-specific. |
| [Deltafin](https://github.com/gavamedia/deltafin) | Selected expert fetches, local cache misses, speculative execution and target verification. Disable remote fetches or account for them explicitly; distinguish generated and accepted tokens. |
| [Colibri](https://github.com/JustVugg/colibri) | Hot, warm and cold expert tiers plus CPU/GPU placement. Record expert routing, reads across tiers and asynchronous overlap from trace replay. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | GGUF layout and quantization overhead, CPU/GPU offload, mmap/caching and backend-specific memory traffic. Compare at the same quality and context. |

Chip 10, Chip 11 and Chip 12 demonstrate carrier generation, reception/energy accounting, and system bottlenecks, respectively. They serve as public teaching context for the measured-workload and link experiments that follow.
