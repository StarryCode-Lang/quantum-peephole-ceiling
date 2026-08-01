# v9 Rerun Evidence

`v9` contains current-code reruns and reconciliation artifacts. It is not a
canonical release data version and is intentionally excluded from
`release/release_manifest.json`.

- `e12` through `e21`: rerun outputs used to assess source drift against frozen
  canonical datasets.
- `*_partial/`: checkpointed or incomplete runs. Preserve `partial.csv`,
  `deferred.json`, and `run_id*.txt` when resumption remains possible.
- `reconciliation_results.json` at `data/v9/` records row-level overlap and
  divergence decisions.

Do not replace canonical files with v9 outputs without creating a new data
version, updating metadata, refreshing the release manifest, and rerunning the
full evidence audit.
