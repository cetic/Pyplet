# CLAUDE.md — pyplet

Application server running Python on both sides: server (Python) and client
(PyScript / Pyodide in the browser). Public docs: [README.md](README.md),
<https://pyplet.readthedocs.io>. Package: `pyplet/`; tests: `tests/`;
shipped scaffold: `pyplet/apps/{template,tutorial}` — inside the package,
because `pyplet init` copies from it and a wheel cannot reach outside.

**Editorial rule**: this file holds only what a few tool uses cannot
rediscover — invariants and decisions, never inventories or history. A WHY
that matters becomes a test; the rest goes to `docs/` or `specs/`.

## Commands (always via `make`, from this directory)

| Task | Command |
| --- | --- |
| Tests | `make test` (all, `uv run --extra test`) / `make test-cov` |
| Lint / format | `make lint` (gate, never fixes) / `make fmt` (fix) — `pyproject.toml` `[tool.ruff]`, line 79 |
| Fast commit gate | `make precommit`; push gate `make prepush` (= lint + test) |
| Run | `make start` |
| Disposable clone | `make new-tree <name>` |
| Guard chain — check | `make doctor` (links resolve, `core.hooksPath`, hook scripts runnable; non-zero and one line per problem) |
| Guard chain — setup | `make env` (creates the missing links to `apps/QualiSpectra`, bmad-loop hook script included; idempotent, never overwrites) |

Never hand-write a `pytest`/`ruff` invocation: `pyproject.toml` has
`fix = true` and `respect-gitignore = false`, so a bare `ruff check .` would
autofix the tree and sweep every local `apps/*` checkout. The recipes scope
to `pyplet tests` and pass `--no-fix`.

## Git — two hosts, one canonical

- **GitLab `seglab/pyplet` (remote `gitlab`) is canonical**; `main` is
  protected; the tech lead pushes to it directly, everyone else through a
  merge request. Tracking lives in GitLab project 1724 (`Sprint #N`
  milestones); a GitHub issue is at most a public pointer to it.
- **GitHub `cetic/Pyplet` (remote `origin`) is a read-only reflection of
  GitLab `main`**, refreshed by a GitLab push mirror (decision 2026-09-09;
  the mirror is being re-created, seglab/pyplet#51 — until then GitHub
  lags). Do not push to `origin`; do not merge on GitHub. Package
  publication (`.github/workflows/push-pypi.yml`) fires from tags.
- `.gitlab-ci.yml` is a deliberate mirror of `.github/workflows/test.yml` +
  `prek.yml`: keep them in step, so "the tests pass" means the same thing on
  both forges.
- `apps/` is gitignored except `template`, `tutorial`, `auth_rules.json`.
  A local app such as `apps/QualiSpectra` is its **own git repo**; from this
  cwd `git` reports pyplet and ignores it — expected, not corruption.
  Before any `git status`/commit, check `git rev-parse --show-toplevel`.

## Development constraints (enforced, not advisory)

Target: the same layered chain as the apps developed on top of pyplet
(`apps/QualiSpectra` is the reference implementation). State 2026-09-09:
layers 2–4 are **live** (`main` is lint-green again since the import-sorter
conflict was settled — it had been red since `ef4a30f`, see #58; the shared git
hooks run `make precommit`/`make prepush` whenever the tracked `.lint-green`
marker exists at the toplevel). Layers 0–1 (Claude Code hooks at this root)
are **live on a workstation where `make doctor` passes**: the chain is
gitignored, so it is linked from its owner `apps/QualiSpectra` by `make env`,
never cloned — a checkout that skips that step has no layer 0–1 at all, and
`make doctor` is what says so.

| Layer | When | What |
| --- | --- | --- |
| 0 | every agent edit | no added `#` comment in `.py` (tooling directives excepted); added docstring ≤ 3 lines; `ruff check --no-fix` + `format --check` on the touched file |
| 0' | agent turn end | same scan on the uncommitted tree |
| 1 | always | the guard chain (`.claude/`, `.githooks/`) is not agent-editable; an agent that needs it changed **says so and stops** |
| 2 | `git commit` | same checks on the **staged blobs**, then `make precommit` |
| 3 | `git push` | `make prepush` |
| 4 | merge | protected `main` on GitLab |

Pre-existing comments are out of scope: the guard judges *added* lines. A
rationale becomes a test; a TODO becomes a GitLab issue. `.claude/` is
local and gitignored (skills shared by symlink with `apps/QualiSpectra`, the
owner) — nothing agent-side is committed to this public repo.
