# Chip 11 Site integration

The public research repository holds the feature source, tests and a minimal
integration patch for the separately hosted Sites checkout. It does not
contain a copy of the other chips or their assets. The shared physics model and assertions live in `simulations/logic/`, where changes trigger the Experiments workflow. The patch was checked
against Sites source revision `b7e2bc04195671705db546bbe09d94188ef0236c`.
From the research checkout, apply it to a clean Sites worktree:

```sh
bash web/chip11/apply.sh /path/to/sites-worktree
node --test simulations/logic/optical-logic.test.mjs
```

The implementation uses the existing static `dist/` root, chip selector,
shared ZIP exporter and tab navigation. Open
`#photonic-circuit-lab/optical-logic` in the Site preview. Validate the
deep link, four gates, mobile layout and the export before deploying via
the existing Sites project.
