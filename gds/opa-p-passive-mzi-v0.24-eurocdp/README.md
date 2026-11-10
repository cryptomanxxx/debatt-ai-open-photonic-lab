# OPA 0.24: passive 2×2 MZI in Luxtelligence lnoi400 (sent to EuroCDP)

The design package the lab shared with EuroCDP on 2026-11-09, archived
unchanged. A passive 2×2 Mach–Zehnder interferometer in thin-film lithium
niobate (Luxtelligence lnoi400 PDK, via
[lxt_pdk_gf](https://github.com/Luxtelligence/lxt_pdk_gf)). The PDK's MZI uses
2×2 MMIs and has no electrodes. Inverse-taper edge couplers sit on two facets
10 mm apart, and the two ports on each facet are 127 µm apart.

| File | |
|------|---|
| `opa_p_four_facet_ports_exploratory.gds` | the layout as sent |
| `opa_p_four_facet_ports_manifest.json` | its manifest (ports, internal checks) |
| `OPA_0.24_README.txt` | the package README as sent |
| `OPA_P_pre_review_package_v030_manifest.json` | manifest of a later, unsent package with the same GDS |
| `LICENSE-lxt_pdk_gf.txt` | MIT licence of the PDK whose cells the layout contains |

**Status: `exploratory`.** As the package README says, the layout has not
passed the foundry's DRC. The lnoi400 DRC runset is distributed by
Luxtelligence on request, so it cannot be run here yet.

What this repository can see in the file:
- layers LN_RIDGE (2/0), LN_SLAB (3/0) and SLAB_NEGATIVE (3/1) only;
- 10 000 × 513.5 µm, facet ports at y = 1750 and 1877 µm on both sides;
- no text labels and no chip contour (6/0).

The script that generated it is not in this repository, so the file cannot be
regenerated here; `provenance.json` records the package checksum instead.
