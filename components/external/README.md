# External Components

Canonical records: [registry.json](../registry.json). Existing repo use is the initial selection, not an endorsement of all PDK cells.

| ID | Cell | PDK | Model status |
|---|---|---|---|
| siepic-bdc-te1550 | `ebeam_bdc_te1550` | SiEPIC EBeam via ubcpdk | upstream_compact_model_candidate |
| siepic-gc-te1550 | `ebeam_gc_te1550` | SiEPIC EBeam via ubcpdk | placeholder |
| siepic-heater | `straight_heater_metal` | SiEPIC EBeam via ubcpdk | not_audited |
| lnoi400-mmi2x2 | `mmi2x2_optimized1550` | Luxtelligence lnoi400 | upstream_compact_model_candidate |
| lnoi400-edge | `double_linear_inverse_taper` | Luxtelligence lnoi400 | upstream_compact_model_candidate |
| lnoi400-mzm | `mzm_unbalanced` | Luxtelligence lnoi400 | pdk_sax_model_evaluated |

Sources: [ubcpdk](https://github.com/gdsfactory/ubc), [SiEPIC EBeam](https://github.com/SiEPIC/SiEPIC_EBeam_PDK), [Luxtelligence documentation](https://luxtelligence.github.io/lxt_pdk_gf/). See pinned locks and local evidence in the registry. Model discovery is not model import. No mixing of PDKs.
