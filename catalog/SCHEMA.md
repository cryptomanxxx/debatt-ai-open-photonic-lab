# Design datasheet (`design.json`)

Every layout script writes a `design.json` next to the GDS it generates, in
`results/<layout-id>/`. [`tools/build_catalog.py`](../tools/build_catalog.py)
validates the datasheets and builds [`README.md`](README.md) and
[`designs.json`](designs.json) from them. CI fails if a datasheet is invalid or
the catalog is out of date.

The datasheet answers "what is this chip?" without opening the GDS file.

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | Unique design id, for example `OPA-LAYOUT-001` |
| `title` | string | One-line name |
| `function` | string | What the circuit does, for example `programmable 2x2 MZI (unitary 2x2)` |
| `status` | string | `exploratory`, `drc-clean`, `submitted` or `fabricated` |
| `pdk` | object | `name`, `version`, `open_source` (bool), `platform` (for example `Si 220 nm SOI`) |
| `wavelength_um` | object | `design` wavelength; optional `band` [min, max] where the design meets its spec |
| `footprint_um` | [x, y] | Bounding box of the layout |
| `optical_ports` | object | `inputs`, `outputs`, optional `pitch_um` and `type` (for example `waveguide`, `grating coupler`) |
| `controls` | object | Count of each control element, for example `{"heaters": 6}` |
| `files` | object | `gds` and `preview` (PNG), relative to the datasheet |
| `generator` | object | `script` and `environment` that produce the GDS |
| `checks` | object | `passed` and `total` from the layout's own checks |
| `key_results` | list | Measured or simulated properties: each item has `name`, `value` and `source` (the experiment or file it comes from) |
| `limitations` | list of strings | What the design does not do or has not been checked for |
| `tags` | list of strings | Free keywords for filtering, for example `mzi`, `phase-shifter`, `generic-pdk` |
| `supersedes` | string, optional | Id of the design this one replaces, for example `OPA-LAYOUT-004`; the catalog shows the chain in both directions and fails if the id is unknown |

Released, frozen copies of a design go to [`gds/`](../gds/README.md); the
catalog describes the working designs.
