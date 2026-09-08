# Contributing

Contributions should preserve the repository's separation between reusable
code, experiment drivers, frozen evidence, and derived outputs.

## Development setup

Use Python 3.12 and install the pinned dependencies from `requirements.txt` or
create the Conda environment from `environment.yml`. Run tests from the
repository root:

```bash
python -m pytest tests/ -q
python -m compileall -q src experiments scripts analysis
```

## Evidence changes

- Do not edit canonical or sealed rows in place.
- Add new experiments under a new versioned output directory.
- Record parameters, source hashes, failures, and resource limits.
- Keep semantic and resource failures visible rather than filtering them out.
- Add or update an independent verifier for a new evidence package.
- State the exact panel and metric scope supported by the result.

Small documentation or code corrections should run the checks relevant to the
changed files. Evidence or optimizer changes should also run the corresponding
receipt verifier listed in the root README.

Pull requests should explain the problem, the resulting behavior, the evidence
boundary, and the validation performed.
