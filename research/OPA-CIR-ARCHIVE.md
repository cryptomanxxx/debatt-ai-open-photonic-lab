# OPA-CIR evidence archive

Pin the eight original experiment-specific artifacts, not later reruns or the aggregate CIR001 bundle. [Manifest](cir_archive_manifest.json) records run, artifact, digest, bytes, PR, head and workflow. All eight artifacts were present and unexpired at preparation. No result bytes are yet committed.

The read-only PR preflight downloads and verifies metadata, exact ZIP size/digest, CRC, safe names, all report gates and cross-experiment source identities. Preserve the negative WDM result and original nested ZIPs. The manually confirmed main-only workflow repeats these checks and preserves original ZIPs, every extracted member and generated provenance under research/evidence/opa-cir, separate from live result directories. Verify staged Git bytes before pushing a new review branch. Never overwrite an existing archive. No experiment reruns and no write to main. Final archive requires a separate PR and review.

After merge, run OPA archive CIR001-008 evidence on main with confirm_archive=true. Review research/opa-cir001-008-evidence against main, then complete the final report from archived exact evidence. No new research experiment authorized here.
