# SiEPIC EBeam — original external geometry archive

OPA-LIB-001 imports three original, unmodified GDS files from the [official core EBeam library](https://github.com/SiEPIC/SiEPIC_EBeam_PDK/tree/363fbb52eefa8669100499ab531d3fe7befc4867/klayout/EBeam/gds/EBeam), exact commit `363fbb52eefa8669100499ab531d3fe7befc4867`. The project README explicitly documents the GDS library and the project-level [MIT license](LICENSE.md) is included byte-for-byte. No separate license was found in the selected core GDS directory or its parent GDS directory. This limited import does not extend to partner, beta or restricted libraries or authorize fabrication. Credit Lukas Chrostowski and contributors; see upstream component references and original GDS text markers.

| Original layout | Purpose | On-chip pin labels |
|---|---|---|
| [ebeam_bdc_te1550.gds](gds/ebeam_bdc_te1550.gds) | Broadband 2×2 directional coupler, nominal TE 1550 nm | opt1–opt4 |
| [ebeam_gc_te1550.gds](gds/ebeam_gc_te1550.gds) | TE grating coupler | opt1 |
| [ebeam_y_1550.gds](gds/ebeam_y_1550.gds) | Y-branch splitter | opt1–opt3 |

[Manifest](manifest.json) records exact upstream paths, Git blob SHA-1 identifiers, byte counts and conservative evidence status. Git blob identifiers matched between source and destination before commit. CI independently calculates Git blob identity and SHA-256 and parses named GDS cells, silicon layer and pin labels with KLayout 0.30.6. It reports dimensions and layer inventory, not a DRC pass or modal port extraction. Original GDS bytes remain untouched, including metadata and hierarchy. The prior ubcpdk 3.3.0 references remain distinct; matching cell names do not demonstrate identical revision or models.

Upstream [BDC documentation](https://github.com/SiEPIC/SiEPIC_EBeam_PDK/blob/363fbb52eefa8669100499ab531d3fe7befc4867/docs/components/ebeam/ebeam_bdc/ebeam_bdc.md) links experimental design-family evidence, but it does not certify the exact imported GDS or establish a measured complex S matrix. No model, measurement or qualification claim is made here. The original grating geometry has one on-chip pin, not a complete fiber-to-chip two-port characterization.

Run `python tools/audit_siepic_lib001.py` with KLayout 0.30.6. The geometry audit is pending PR CI; no verified physical performance. Next: LIB002 pinned Luxtelligence layouts, kept separate from SiEPIC silicon. LIB003 complex S datasets must record model provenance and geometry correspondence independently.
