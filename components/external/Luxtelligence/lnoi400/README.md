# Luxtelligence lnoi400 — generated external PCell references

OPA-LIB-002 uses the same [pinned MIT-licensed upstream PDK revision](https://github.com/Luxtelligence/lxt_pdk_gf/tree/d16db6a4882657feb1ce696c16c604ff6cb7ccfa) as CIR002–008 and LAYOUT005. The selected factories are in [lnoi400/cells.py](https://github.com/Luxtelligence/lxt_pdk_gf/blob/d16db6a4882657feb1ce696c16c604ff6cb7ccfa/lnoi400/cells.py). No standalone original GDS was located for these selected cells at the checked paths. The outputs are **Debatt-AI-generated exports of external PCells**, not original upstream GDS files or independently designed Debatt-AI components. [Upstream license](LICENSE) retained; no foundry rights, advanced proprietary cells or restricted runsets implied.

| Reference | Factory and settings | Optical / electrical ports expected |
|---|---|---:|
| straight-rwg1000 | `straight_rwg1000` `{"length":100}` | 2 / 0 |
| euler-bend-90 | `L_turn_bend` defaults | 2 / 0 |
| mmi-2x2 | `mmi2x2_optimized1550` defaults | 4 / 0 |
| directional-coupler | `directional_coupler_balanced` defaults | 4 / 0 |
| edge-coupler | `double_linear_inverse_taper` defaults | 2 / 0 |
| eo-phase-shifter-5mm | `eo_phase_shifter` `{"modulation_length":5000}` | 2 / 2 |
| mzm-2x2-5mm | `mzm_unbalanced` `{"modulation_length":5000,"length_imbalance":0,"splitter":"mmi2x2_optimized1550","with_heater":true}` | 4 / 4 |

The 5 mm MZM matches the PCell settings of LAYOUT005 (balanced arms, 2×2 MMI, heater). Its four optical ports must not be confused with the default 1×2 MZM compact model. The 5 mm EO phase shifter is a separate cell with its own CPW geometry and two electrical ports. The 100 µm straight provides a defined routing reference. All dimensions in µm. No claim of measured response or broadband performance.

[Generation specification](generation-spec.json) records pinned source, source blobs, parameters, evidence limits and expected port inventory. The [audit](../../../../tools/audit_lnoi400_lib002.py) exports one standalone GDS per cell with metadata disabled, then independently reads the GDS using KLayout, checks allowed and required nonempty geometry layers, dimensions, source PCell port names/counts/coordinates, file hashes and byte-identical regeneration in a fresh process. Each GDS gets a separate JSON sidecar containing PCell port metadata, not inferred modal reference planes. Existing locked environment and exact upstream checkout reused.

## Status and archive handoff

PR CI produces artifact `opa-lib-002` (seven GDS files, seven sidecars, result, license, specification and environment records). PR224 contained the generator, license and manifest. Its exact successful CI outputs are now preserved in the separate archive review branch; see the completed archive below. SiEPIC original GDS remain separate. No DRC run, measured data, model import or fabrication qualification. LIB003 will address complex S data with explicit geometry/model correspondence and port conventions.

## Verified export results and archive preparation

[Original CI run 44543077787](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44543077787) passed all six checks. The seven GDS outputs, port sidecars and exact environment records are in artifact 14539755227 (104456 bytes, SHA-256 pinned in [archive-source.json](archive-source.json)). All seven were byte-identical on fresh-process regeneration. Bounding boxes (µm): straight 100×10; bend 85×85; MMI 126.5×13.5; directional coupler 132.92×40.6; edge 360×20; EO 5400×378; MZM 7132.55×462. Total 20 optical and 6 electrical PCell ports, not independently measured modal planes. No DRC or physical measurements.

After archive-preparation PR merge, run [OPA archive LIB002 evidence](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/workflows/opa-archive-lib002.yml) on main with confirm_archive=true. It downloads the exact pinned ZIP, validates every member and GDS hash, checks staged bytes and pushes research/opa-lib002-evidence only. Review and merge separately. The future archive directory contains original.zip, gds/, ports/, evidence/ and provenance.json; permanent CI verifies committed bytes offline. No original results were rerun. The archive branch was created successfully as recorded below.

## Completed archive

[Archive run 44547625238](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44547625238) verified the pinned ZIP and all staged bytes and created archive commit `36aaa3f`. The archive contains 21 files totaling 273787 bytes. [Original ZIP](archive/original.zip) | [GDS files](archive/gds/) | [Port metadata](archive/ports/) | [Verification report](archive/evidence/result.json) | [Provenance and hashes](archive/provenance.json). These are exact CI-generated exports, not upstream original GDS or measured hardware. No DRC or imported S data. The permanent offline audit checks committed bytes on the archive PR.

## Complex model import

[LIB003 complex scattering models](s_parameters/README.md) adds original upstream coefficient files for MMI and directional coupler. The historical GDS archive remains unchanged; model evidence and passivity status are separate.
