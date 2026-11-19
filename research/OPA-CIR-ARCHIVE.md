# OPA-CIR evidence archive

Pin the eight original experiment-specific artifacts, not later reruns or the aggregate CIR001 bundle. [Manifest](cir_archive_manifest.json) records run, artifact, digest, bytes, PR, head and workflow. All eight artifacts were present and unexpired at preparation. No result bytes are yet committed.

The read-only PR preflight downloads and verifies metadata, exact ZIP size/digest, CRC, safe names, all report gates and cross-experiment source identities. Preserve the negative WDM result and original nested ZIPs. The manually confirmed main-only workflow repeats these checks and preserves original ZIPs, every extracted member and generated provenance under research/evidence/opa-cir, separate from live result directories. Verify staged Git bytes before pushing a new review branch. Never overwrite an existing archive. No experiment reruns and no write to main. Final archive requires a separate PR and review.

After merge, run OPA archive CIR001-008 evidence on main with confirm_archive=true. Review research/opa-cir001-008-evidence against main, then complete the final report from archived exact evidence. No new research experiment authorized here.

## Completed archive (2026-11-19)

[Run 44531822192](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44531822192) successfully verified eight original ZIPs and staged bytes: 41 files, 3,222,234 bytes. [PR221](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/221) merged as 629aa6bbf401c109a9ae46f440cafb4799d88854. [Permanent evidence](evidence/opa-cir) and offline audit now in main. See [final report](OPA-CIR-FINAL-REPORT.md).
