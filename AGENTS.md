<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Agent Development Guidelines

This document codifies git and development practices for AI agents working on
this repository. These practices are derived from the project constitution and
established development conventions.

## Constitution

If `.specify/memory/constitution.md` exists in this repository, read it and
follow its principles. The constitution takes precedence over this file if
there is any conflict between the two documents.

## Git Commit Requirements

### Commit Message Format

Use **Conventional Commits** with **capitalized types**:

```plaintext
Type(scope): Short description

Optional body with more details, wrapped per `.gitlint`.

Co-Authored-By: <AI Model Name> <appropriate-email@provider.com>
```

**Allowed types** (capitalized):

- `Fix` - Bug fixes
- `Feat` - New features
- `Chore` - Maintenance tasks
- `Docs` - Documentation changes
- `Style` - Code style/formatting (no logic change)
- `Refactor` - Code refactoring (no behavior change)
- `Perf` - Performance improvements
- `Test` - Adding or updating tests
- `Revert` - Reverting previous commits
- `CI` - CI/CD configuration changes
- `Build` - Build system changes

### Commit Command

Always use the `-s` flag for Developer Certificate of Origin sign-off:

```bash
git commit -s -m "Type(scope): Description

Body text here.

Co-Authored-By: <AI Model> <email@provider.com>"
```

### Line Length Limits

Subject and body line lengths are defined in `.gitlint`, which is the
single source of truth. They are enforced automatically by the gitlint
pre-commit hook and by the `commit-message-linting` CI job, so consult
that file rather than relying on a number repeated here.

- **Subject line**: see `title-max-length` in `.gitlint`
- **Body lines**: gitlint's `body-max-line-length` rule; `.gitlint` does
  not override the gitlint default
- URLs in body are exempt from line length (gitlint configured)

### Co-Authorship

All AI-assisted commits MUST include a Co-Authored-By trailer identifying the
AI model used. Use the appropriate name and email for your model:

| Model | Co-Authored-By |
| ------- | ---------------- |
| Claude | `Co-Authored-By: Claude <claude@anthropic.com>` |
| ChatGPT | `Co-Authored-By: ChatGPT <chatgpt@openai.com>` |
| Gemini | `Co-Authored-By: Gemini <gemini@google.com>` |
| Copilot | `Co-Authored-By: GitHub Copilot <copilot@github.com>` |

This trailer goes at the end of the commit message body.

## Pre-Commit Hooks

This repository uses pre-commit hooks that run automatically on `git commit`.
The hooks may enforce (non-exhaustive list):

- **reuse** - SPDX license header compliance
- **ruff** - Python linting and formatting
- **mypy** - Python type checking
- **interrogate** - Docstring coverage
- **yamllint** - YAML linting
- **gitlint** - Commit message format validation
- **actionlint** - GitHub Actions workflow validation

Additional hooks may be configured. Check `.pre-commit-config.yaml` for the
complete list.

### If Pre-Commit Fails

**CRITICAL**: Do NOT use `git reset` after a failed commit attempt.

1. Fix the issues identified by the pre-commit hooks
2. Stage the fixes: `git add <files>`
3. Attempt the commit again as if you hadn't tried before
4. The pre-commit hooks will run again on the new attempt

Pre-commit hooks may auto-fix some issues (e.g., ruff format). If files were
modified by hooks, stage them and commit again.

### Never Bypass Hooks

Using `--no-verify` to bypass pre-commit hooks is **PROHIBITED**.

## Atomic Commits

Each commit MUST represent exactly one logical change:

- ✅ One feature per commit
- ✅ One bug fix per commit
- ✅ One refactor per commit
- ❌ Multiple unrelated changes in one commit

### Task List Updates Are Separate Commits

Changes to task tracking documents (e.g., `tasks.md`) MUST be committed
separately from the code or documentation they track. Bundling a task
list update into the same commit as the work it describes breaks commit
atomicity — even when both changes are classified as documentation.

- ✅ Commit 1: `Feat(core): Add HTTP client` (code + tests)
- ✅ Commit 2: `Docs(tasks): Mark T015 complete` (tasks.md only)
- ❌ Single commit with code changes **and** tasks.md update

## SPDX License Headers

All new source files MUST include SPDX headers:

```python
# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0
```

Check `REUSE.toml` for file-type-specific header requirements.

## Testing Requirements

The Python project lives under `custom_components/`. Run commands
from the repository root using `uv`:

- Run tests before committing: `uv run pytest tests/`
- Run linting before committing: `uv run ruff check custom_components/ tests/`
- All tests must pass before pushing
- New features should include appropriate test coverage

## Development Workflow Summary

1. Make changes to code
2. Run tests locally to verify: `uv run pytest tests/ -x -q`
3. Run linting: `uv run ruff check custom_components/ tests/`
4. Stage changes: `git add <files>`
5. Commit with sign-off and co-authorship:

   ```bash
   git commit -s -m "Type(scope): Description

   Body if needed.

   Co-Authored-By: <AI Model> <email@provider.com>"
   ```

6. If pre-commit fails, fix issues and commit again (don't reset)
7. Push when ready

## Quick Reference

| Requirement | Command/Format |
| ------------ | ---------------- |
| Sign-off | `git commit -s` |
| Co-author | `Co-Authored-By: <Model> <email@provider.com>` |
| Subject format | `Type(scope): description` |
| Type case | Capitalized (e.g., `Fix`, `Feat`) |
| Subject length | Per `title-max-length` in `.gitlint` |
| Body line length | gitlint `body-max-line-length` default |
| After failed commit | Fix and retry (no reset) |
