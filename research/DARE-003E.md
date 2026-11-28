# DARE-003E · Reproducible test execution

Date: 2026-11-28. Tested source revision: 7e9df3b0a8d5e86e94e2370b1472faaf831dd6f7 (PR 343 merge). Scope: the 18 known DARE Python source/test files from DARE-002 through DARE-003D, offline synthetic tests only.

## Actual execution

A Git clone into the local container failed with exit 128 (Could not resolve host: github.com). The GitHub connector successfully returned the individual revision-pinned sources and their Git blob identities. All 18 files were transcribed into an isolated local directory, verified using git hash-object against the returned blob identities, and hashed with SHA-256. A first partial run of 17 tests passed in 0.002 s; its [output](evidence/dare-003e/partial-17.log) is retained. The complete known suite then ran in Python 3.13.5 on Linux, using the standard library only.

```text
Ran 100 tests in 0.094s

OK
```

Exit status 0. [Full original output](evidence/dare-003e/full-100.log) and [machine-generated provenance](evidence/dare-003e/provenance.json) were transferred to the GitHub branch; fetched archive blob IDs matched local original file blob IDs. The full log SHA-256 is e72caf5fa71e6e8eaa2bf26c8659ad89a0f08125511fae6eca776f2e383ce12e. The provenance SHA-256 is 9c60deb4350687ee81b104b80b862d5742dd38eebc4706e16760103aae3f347f. The partial log SHA-256 is 710e2171c487f76a82601b97f5d2a67ba6f85874b3ec7b2fc2ece8207a8bd317. No GitHub Actions run is asserted.

## Reproduction instructions

1. Obtain the exact tested source revision using an authorized local checkout or the manifest-listed individual source blobs. Check that the local file inventory is complete; this run covers the known 18 files, not an independently enumerated full repository tree.
2. Compare each source file's Git blob SHA-1 and SHA-256 with the provenance manifest before execution. Use a fresh directory; inspect any source discrepancy before proceeding.
3. Run with Python 3.13.5: `python -m unittest discover -s dare -p 'test_*.py' -v > full-100.log 2>&1`. Record the actual exit status, environment, source identities and log digests. Preserve failure output as well as successful output. Elapsed time is environment dependent.
4. Archive original output in a new run directory; if transferring via text, compare the destination blob identity with the original file. Never synthesize a log from expected test names. Do not overwrite any historical run.

## Qualification decision

The new run provides positive evidence for the test-defined offline software screen at the tested revision. Recommend reinstating scoped offline qualification upon human review of this PR, not qualification for production or autonomous operation. Prior purported runs remain unverified and their files remain unchanged; this new execution does not authenticate past runs or their timings. Independent reproduction by another operator remains outstanding.

DARE-003 historical and prospective real-observation evaluation remains incomplete: seven historical candidates, zero qualified real observations, no independent reference labels. Provider authentication, actual included quota/billing, external sequence authority and production crash safety remain unresolved. No live collection, agent execution, new workflow dispatch or paid service was initiated. Zero Additional Cost Policy unchanged.

Next: review new evidence, establish independent reproduction when available, and separately approve bounded human-triggered metadata collection only after the remaining cost/access conditions are verified.
