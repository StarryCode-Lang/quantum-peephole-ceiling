# GUOQ third-artifact go/no-go record (2026-08-11)

## Disposition

**GO for a future bounded rewrite-only pilot; NO-GO for the official Docker
workflow on this host; NOT ASSESSED for BQSKit resynthesis; NOT RUN for the
shared 520 confirmatory benchmark.** The three rows produced here are smoke
evidence only and are explicitly ineligible for manuscript comparison.

## Official identity and execution boundary

- Official project page: <https://qqq-wisc.github.io/>
- Official repository: <https://github.com/qqq-wisc/guoq>
- Repository `main` HEAD observed by `git ls-remote`:
  `8c4c3a5a6dfc9f7fc375ec16c2180139f0a8cb1a`
- Repository license at that commit: Apache-2.0.
- Paper DOI: <https://doi.org/10.1145/3669940.3707240>
- Artifact concept DOI: <https://doi.org/10.5281/zenodo.14055562>, resolving
  on 2026-08-11 to version DOI <https://doi.org/10.5281/zenodo.14057840>.
- The resolved Zenodo record has no declared semantic version. Therefore the
  execution identity is the version DOI plus file checksums, not an invented
  release number. The official JAR used here has SHA-256
  `df09a32ea7d3df8e6c7877f833531f1f250d58590439cafcfc08d7a9a6ba8895`.
- The current repository HEAD is recorded as a source anchor only. This review
  does not assert that the older Zenodo JAR was built from that HEAD.

The official README recommends Linux with at least 32 GiB RAM for the artifact
and says its image targets `linux/amd64`. It separately states that GUOQ itself
can be installed natively. The official source requires Java 21, Maven 3, and
Python 3.8+; the artifact README uses Python 3.12. The source's default/current
GUOQ path combines rewriting with BQSKit resynthesis, while `-resynth NONE` is
an officially documented rewrite-only mode.

## Current-host preflight

The host had Windows 11 AMD64, 8 logical CPUs, 15.79 GiB RAM, no Docker
executable, Java 8 on the system PATH, and no Maven. A checksum-pinned portable
Temurin JRE 21.0.12+8 was used only for the isolated smoke. Consequently:

| Path | Decision | Exact reason |
|---|---|---|
| Official Docker image | NO-GO | Docker absent; host RAM is below the official 32 GiB recommendation |
| Native build from current source | NO-GO as-is | PATH Java is 8 and Maven is absent |
| Official prebuilt JAR, rewrite only | GO | Portable Java 21, JAR, and both Nam rule hashes passed preflight |
| BQSKit resynthesis | NOT ASSESSED | `bqskit` is absent and no resynthesis server was started |
| Shared 520 | NOT RUN | Go/no-go phase only; no authorization for a formal full run |

Machine-readable evidence is in
`data/v10/prepaper/external_baselines/guoq/preflight/preflight.json` and
`official_artifact_record.json`.

## Three-input smoke

The adapter ran `NAM`, objective `TWO_Q`, `-resynth NONE`, seed 0, an 8-second
external timeout, and a 4 GiB Java heap cap. Each run emitted an incumbent
before timeout and each incumbent passed exact `Operator.equiv` verification
against the original common-basis circuit.

| Input | Status | Gates in -> out | 2Q in -> out | Exact equivalent |
|---|---:|---:|---:|---:|
| `cnot_chain_4` | `ok_timeout_incumbent` | 24 -> 0 | 24 -> 0 | yes |
| `ghz_4` | `ok_timeout_incumbent` | 8 -> 4 | 3 -> 3 | yes |
| `qft_4` | `ok_timeout_incumbent` | 50 -> 28 | 12 -> 12 | yes |

These outcomes establish executability and I/O/verification compatibility.
They do not estimate GUOQ's comparative performance: rewrite-only differs from
the paper's stronger resynthesis-enabled configuration, the sample is chosen
and tiny, the timeout is only eight seconds, and there is one seed.

## Reproduction

After acquiring the official JAR and `queso_rules.tar.gz`, verifying the Zenodo
checksums, extracting the rule archive, and providing Java 21:

```powershell
python experiments/external_guoq_benchmark.py smoke `
  --java <java-21.exe> `
  --jar <GUOQ-1.0-jar-with-dependencies.jar> `
  --rules-dir <extracted-queso_rules> `
  --manifest data/v10/prepaper/external_baselines/quartz/shared_520/inputs/benchmark_manifest.csv `
  --circuit-id cnot_chain_4 --circuit-id ghz_4 --circuit-id qft_4 `
  --timeout-seconds 8 --seed 0
```

Before any formal GUOQ addition, the next gate is a 3--10 input pilot using the
paper-faithful BQSKit resynthesis server, multiple fixed seeds, a justified
timeout, resource telemetry, and the same exact-equivalence/ITT rules. Only a
successful pilot should unlock a separately authorized shared-520 run.
