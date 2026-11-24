# Chip 12 Site integration

This directory contains the interactive UI, responsive styling and Lab integration patch for the separately hosted Site. The simulator uses the same numerical module as the OPA-MEM-001 tests and runner. See [OPA-MEM methods and evidence](../../research/OPA-MEM.md).

The patch targets the Chip 11 publication's Sites source, revision `3b2aeee7cd8eea61ac3d093cce98d8cb3dcf92f9`. Apply from the research checkout:

```sh
bash web/chip12/apply.sh /path/to/sites-worktree
```

Open `#photonic-circuit-lab/photonic-memory`. Verify that the Chip 12 selector, Chip 10/11 cross-links, step and play, all eight presets, controls, result tables and CSV/JSON downloads function. Check for horizontal overflow at phone and tablet widths and confirm that selecting an earlier chip hides the new panel.
