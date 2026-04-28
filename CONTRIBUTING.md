# Contributing Guidelines

First off, thanks for considering to contribute to this project!

These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Git hooks

We use git hooks through [pre-commit](https://pre-commit.com/) to enforce and automatically check some "rules". Please install them (`pre-commit install`) before to push any commit.

See the relevant configuration file: `.pre-commit-config.yaml`.

## Code Style

Make sure your code *roughly* follows [PEP-8](https://www.python.org/dev/peps/pep-0008/) and keeps things consistent with the rest of the code:

- docstrings: [sphinx-style](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html#the-sphinx-docstring-format) is used to write technical documentation.
- formatting: [black](https://black.readthedocs.io/) is used to automatically format the code without debate.
- sorted imports: [isort](https://pycqa.github.io/isort/) is used to sort imports
- static analisis: [flake8](https://flake8.pycqa.org/en/latest/) is used to catch some dizziness and keep the source code healthy.

## Tests

Two layers, both runnable from the repo root:

### Unit tests — pure Python, no Docker

```bash
python -m unittest discover -s tests/unit -v
```

These stub out PyQGIS and the native ADBC driver (see `tests/_stubs.py`),
so they run anywhere with Python 3.12+ and finish in well under a second.

### Integration tests — live GizmoSQL container

```bash
pip install pytest adbc-driver-gizmosql adbc-driver-flightsql docker
python -m pytest tests/integration -v -m integration
```

The session-scoped fixture in `tests/integration/conftest.py` does one of:

1. **Reuse**: if something is already listening on `localhost:41337` (or
   `$GIZMOSQL_TEST_PORT`), use it.
2. **Spin up**: otherwise, launch a `gizmodata/gizmosql:latest` container
   on host port `41337` (Flight SQL) and `41338` (health) — non-default
   so it can coexist with a regular GizmoSQL the developer is running on
   the standard `31337`.
3. **CI sidecar**: in GitHub Actions, the workflow's `services:` block
   provisions the container and the fixture is a no-op (controlled by
   `GIZMOSQL_TEST_HOST`).

The integration job is wired into `.github/workflows/ci.yml` and gates
`package` / `release` along with lint and unit tests.
