# Contributing to Q-research

Thank you for your interest in contributing to this project! Below are guidelines to help you get started.

## How to Contribute

1. **Fork and clone** the repository to your local machine.
2. **Create a branch** for your feature or bugfix (e.g., `feature/add-experiment` or `fix/figure-rendering`).
3. **Make your changes** and commit with clear, descriptive messages.
4. **Open a pull request** against the `main` branch with a summary of your changes.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for all Python code.
- Use type hints where possible and include docstrings for all public functions and classes.
- Keep imports organized: standard library first, then third-party, then local.
- Maximum line length is 88 characters (Black-compatible).

## Testing

- Write unit tests for new functionality using `pytest`.
- Ensure all existing tests pass before submitting a PR: `pytest tests/ -v`.
- Include test data or fixtures in the `tests/data/` directory if needed.
- Aim for meaningful test coverage — test edge cases and error paths, not just happy paths.

## Pull Request Process

1. Ensure your branch is up to date with `main` before opening a PR.
2. Fill out the PR template with a description of changes, related issues, and testing notes.
3. Request a review from at least one maintainer.
4. Address review feedback promptly and keep commits clean (squash/rebase if requested).
5. Once approved and CI passes, a maintainer will merge your PR.
