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

## Original external geometry

[OPA-LIB-001: SiEPIC EBeam original GDS](SiEPIC-EBeam/README.md) contains three byte-identical core library GDS files at a distinct pinned upstream revision. [Manifest](SiEPIC-EBeam/manifest.json). Related v1 reference IDs indicate design-family relationships, not exact revision equivalence. Geometry checks are separate from DRC, optical data and measurements.

## External PCell exports

[Luxtelligence lnoi400 / LIB002](Luxtelligence/lnoi400/README.md): seven pinned PCell export specifications, including CIR-relevant MMI, EO and balanced MZM. CI output must be archived separately; keep distinct from imported original SiEPIC files.
