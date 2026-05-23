# Contributing

Thanks for considering a contribution!

## Development setup

```bash
git clone https://github.com/embedded-pro/cortex-memory-budget.git
cd cortex-memory-budget
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

ARM toolchain (required for integration tests):

```bash
sudo apt-get install -y --no-install-recommends gcc-arm-none-eabi
```

## Quality gates

All of these must pass before a PR will be reviewed:

```bash
ruff check src tests
mypy src/cortex_memory_budget
pytest -v
```

## Adding tests

- One module per test file under `tests/unit/`, matching the source layout.
- Use `pytest` parametrize for matrix-style coverage.
- Integration tests live in `tests/integration/` and require the ARM
  toolchain; they're skipped automatically when it isn't available.
- All test code targets Python ≥ 3.11; do not use `typing.Optional` style —
  use `X | None`.

## Style

- Ruff config in `pyproject.toml` is the source of truth.
- `mypy --strict` — no untyped functions, no implicit `Any`.
- Run `ruff format` before committing.

## Releases

Tags `v*.*.*` on `main` trigger `.github/workflows/release.yml`, which
builds an sdist + wheel and publishes to PyPI via OIDC trusted publishing.
Update `CHANGELOG.md` and bump the `__version__` in
`src/cortex_memory_budget/__init__.py` and `pyproject.toml` in the same PR
that introduces user-visible changes.

## Code of conduct

Be kind, be precise, prefer code over arguing.
