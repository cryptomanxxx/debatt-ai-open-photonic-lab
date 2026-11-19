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

PR CI produces artifact `opa-lib-002` (seven GDS files, seven sidecars, result, license, specification and environment records). This PR contains the generator, license and manifest, **not yet generated GDS bytes**. After successful CI, pin that exact artifact identity and archive its original generated outputs in a separate reviewed PR rather than silently generating substitutes. SiEPIC original GDS remain separate. No DRC run, measured data, model import or fabrication qualification. LIB003 will address complex S data with explicit geometry/model correspondence and port conventions.
