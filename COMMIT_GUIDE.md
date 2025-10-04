COMMIT GUIDE
===========

This short guide explains the pre-commit hooks and the most efficient way to prepare commits
for the now-playing repository.

What runs before every commit
- black (code formatter)
- isort (import sorter)
- flake8 (linter / docstyle)
- end-of-file-fixer and trim-trailing-whitespace
- tests or other checks may be enforced by CI (see `.github/workflows`)

Suggested local workflow
1. Work in a feature branch for iterative changes.
2. Frequently run `black .` and `python -m isort .` to keep formatting/imports clean.
3. Run `flake8` locally to catch docstring and style issues early.
4. Stage logically grouped changes with `git add -p`.
5. Commit with a focused, descriptive message.
6. If pre-commit flags unrelated demo or doc issues you intentionally left, use `--no-verify` to bypass but prefer to fix them.

Common fixes
- isort failures: run `python -m isort <file>` or `python -m isort .` to fix ordering.
- black reformat: run `black .` and re-stage.
- flake8 D100/D103 (missing docstrings): add module/function docstrings for public modules.
- E800 (commented out code): remove or uncomment blocks; prefer leaving small TODO comments instead.

Notes
- CI enforces `make test-ci` which skips integration tests that require external credentials.
- Keep credential-requiring code gated behind env vars and mark integration tests so CI stays green.

If you want, I can add this to the README or expand it with example commands for your shell.
