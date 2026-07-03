<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contributing to Local Akuvox Integration

Thank you for your interest in contributing! This document explains how
to set up your development environment, run tests, and submit changes.

## Prerequisites

- Python 3.14.2 or later
- [uv](https://docs.astral.sh/uv/) for dependency management
- [pre-commit](https://pre-commit.com/) for automated code quality
  checks
- Git with GPG or DCO sign-off capability

## Getting Started

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/<your-username>/homeassistant-local-akuvox.git
   cd homeassistant-local-akuvox
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Install pre-commit hooks (including commit message checks):

   ```bash
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

## Development Workflow

### Running Tests

```bash
uv run pytest tests/ -x -q
```

### Running Linting and Formatting

```bash
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
```

### Running Type Checks

```bash
uv run mypy custom_components/
```

### Running All Pre-Commit Hooks

```bash
pre-commit run --all-files
```

## Code Standards

### Style and Quality

- All code must pass **ruff** linting and formatting.
- All functions and classes must have **docstrings** (CI enforces
  100% coverage via `interrogate`).
- All function signatures must have **type annotations**.
- Cyclomatic complexity must not exceed 10 per function.
- All new source files must include **SPDX license headers**:

  ```python
  # SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
  # SPDX-License-Identifier: Apache-2.0
  ```

### Test-Driven Development

This project follows strict TDD. For every change:

1. **Red** — Write a failing test that defines the desired behavior.
2. **Green** — Implement the minimum code to make the test pass.
3. **Refactor** — Clean up while keeping all tests green.

### Commit Messages

We use **Conventional Commits** with capitalized types:

```text
Type(scope): Short description (≤50 chars)

Optional body wrapped at 80 characters.

Signed-off-by: Your Name <your-email@example.com>
```

**Types:** `Fix`, `Feat`, `Chore`, `Docs`, `Style`, `Refactor`,
`Perf`, `Test`, `Revert`, `CI`, `Build`

**Rules:**

- Always sign off commits: `git commit -s`
- Subject line must not exceed 50 characters.
- Body lines must not exceed 80 characters.
- Each commit must represent exactly one logical change.
- For single-commit PRs, the commit message must match
  the PR title.
- Never bypass pre-commit hooks with `--no-verify`.

### Pre-Commit Hooks

The following hooks are among those that run automatically on commit
(see `.pre-commit-config.yaml` for the full list):

| Hook              | Purpose                             |
| ----------------- | ----------------------------------- |
| **ruff**          | Python linting and formatting       |
| **mypy**          | Static type checking                |
| **interrogate**   | Docstring coverage                  |
| **reuse**         | SPDX license header compliance      |
| **yamllint**      | YAML file validation                |
| **gitlint**       | Commit message format               |
| **markdownlint**  | Markdown style enforcement          |
| **codespell**     | Spell checking                      |
| **actionlint**    | GitHub Actions workflow validation  |

If a hook fails:

1. Fix the reported issues.
2. Stage your fixes: `git add <files>`
3. Commit again — do **not** use `git reset`.

Some hooks (like ruff format) auto-fix files. If files were modified
by hooks, stage the changes and commit again.

## Project Structure

```text
custom_components/local_akuvox/
├── __init__.py          # Integration setup and lifecycle
├── config_flow.py       # Configuration and options flows
├── const.py             # Constants and configuration keys
├── coordinator.py       # Data update coordinator
├── entity.py            # Base entity class
├── lock.py              # Lock platform entities
├── manifest.json        # Integration manifest
├── sanitize.py          # Webhook payload sanitization
├── services.yaml        # Service definitions
├── strings.json         # User-facing strings
├── translations/
│   └── en.json          # English translations
└── webhook.py           # Webhook handler and lifecycle

tests/
├── conftest.py          # Shared test fixtures
├── test_config_flow.py  # Config and options flow tests
├── test_coordinator.py  # Coordinator tests
├── test_init.py         # Integration lifecycle tests
├── test_lock.py         # Lock entity tests
├── test_sanitize.py     # Sanitization tests
├── test_services.py     # Service call tests
└── test_webhook.py      # Webhook handler tests
```

## Submitting Changes

1. Create a feature branch from `main`.
2. Make your changes following the standards above.
3. Ensure all tests pass and linting is clean.
4. Push your branch and open a pull request.
5. The CI pipeline and Copilot reviewer will check your changes.
6. Address any review feedback and push updates.

## Reporting Issues

Please use the GitHub issue tracker to report bugs or request features.
Include:

- Home Assistant version
- Integration version
- Akuvox device model and firmware version
- Relevant log entries from Home Assistant

## License

By contributing, you agree that your contributions will be licensed
under the Apache License 2.0.
