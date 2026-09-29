ifeq ($(firstword $(MAKECMDGOALS)),sandbox)

# Remove "sandbox" from the goals before forwarding
SANDBOX_GOALS := $(filter-out sandbox,$(MAKECMDGOALS))
.PHONY: sandbox
sandbox:
	cd .sandbox && $(MAKE) $(SANDBOX_GOALS)
# Prevent "No rule to make target" errors for forwarded goals
$(SANDBOX_GOALS):
	@:

else ifeq ($(firstword $(MAKECMDGOALS)),new-tree)

TREE_TARGETS := $(filter-out new-tree,$(MAKECMDGOALS))
# Remove "sandbox" from the goals before forwarding
new-tree:

$(TREE_TARGETS):
	git clone --depth=1 ./ $@
	cd $@ && git checkout -b $@

else

sandbox:

new-tree:

start:
	uv run -m pyplet start

test:
	uv run --extra test pytest tests/ -v -W always # -n auto

test-cov:
	uv run --extra test pytest tests/ -v --cov=pyplet --cov-report=html --cov-report=term

# Gates. pyproject sets `fix = true` and `respect-gitignore = false`, so the
# recipes pass --no-fix and scope to the package + tests (never `.`, which
# would sweep local apps/* checkouts).
LINT_PATHS := pyplet tests

lint:
	uv run --extra test ruff check --no-fix $(LINT_PATHS)
	uv run --extra test ruff format --check $(LINT_PATHS)

fmt:
	uv run --extra test ruff check --fix $(LINT_PATHS)
	uv run --extra test ruff format $(LINT_PATHS)

precommit: lint

prepush: lint test

# Guard chain: gitignored here, owned by apps/QualiSpectra and shared by
# symlink, so a fresh clone has none of it. `env` creates the links (plus
# the bmad-loop hook script that settings.json calls), `doctor`
# reports drift. Both act on the current directory, so `make -C <root> doctor`
# checks another checkout without touching it. A hook script is judged
# runnable as it is invoked: +x only when the command runs it directly, since
# an interpreted one (`python3 x.py`) needs no exec bit.
# A linked worktree has no `apps/` of its own: the owner is looked up next to
# the common git dir, i.e. in the main checkout, and linked by absolute path.
CHAIN_COMMON := $(or $(shell git rev-parse --git-common-dir 2>/dev/null),.git)
CHAIN_OWNER := $(if $(filter .git,$(CHAIN_COMMON)),,$(patsubst %/.git,%,$(CHAIN_COMMON))/)apps/QualiSpectra
# The owner as seen from inside `.claude/`: one level up when relative.
CHAIN_OWNER_UP := $(if $(filter .git,$(CHAIN_COMMON)),../,)$(CHAIN_OWNER)
# What Claude Code puts in $CLAUDE_PROJECT_DIR: the main checkout, even when a
# hook fires inside a linked worktree.
CHAIN_ROOT := $(if $(filter .git,$(CHAIN_COMMON)),.,$(patsubst %/.git,%,$(CHAIN_COMMON)))
CHAIN_LINKS := settings.json hooks skills
CHAIN_GITHOOKS := .githooks
CHAIN_SETTINGS := .claude/settings.json
CHAIN_BMAD := .bmad-loop/bmad_loop_hook.py
# Links are compared by the exact target `env` would write; core.hooksPath by
# where it lands, since git accepts an absolute path there and a worktree
# inherits it as such. `env` reads and writes the *local* config only, so a
# global core.hooksPath is overridden, never mistaken for a local choice.
CHAIN_RESOLVE := resolve() { cd -P -- "$$1" 2>/dev/null && pwd -P; }

doctor:
	@rc=0; \
	check() { \
	  if [ -L "$$1" ]; then \
	    cur=$$(readlink "$$1"); \
	    if [ ! -e "$$1" ]; then echo "KO   $$1: dangling link -> $$cur"; return 1; \
	    elif [ "$$cur" != "$$2" ]; then \
	      echo "KO   $$1 -> $$cur (expected $$2)"; return 1; \
	    else echo "ok   $$1 -> $$cur"; fi; \
	  elif [ -e "$$1" ]; then \
	    echo "KO   $$1: real file/dir, expected a link -> $$2"; return 1; \
	  else echo "KO   $$1: missing link (expected -> $$2)"; return 1; fi; \
	}; \
	for n in $(CHAIN_LINKS); do \
	  check ".claude/$$n" "$(CHAIN_OWNER_UP)/.claude/$$n" || rc=1; \
	done; \
	check "$(CHAIN_GITHOOKS)" "$(CHAIN_OWNER)/$(CHAIN_GITHOOKS)" || rc=1; \
	$(CHAIN_RESOLVE); \
	hp=$$(git config --get core.hooksPath 2>/dev/null); \
	if [ -z "$$hp" ]; then \
	  echo "KO   git config core.hooksPath: unset (expected $(CHAIN_GITHOOKS))"; \
	  rc=1; \
	elif [ ! -d "$$hp" ]; then \
	  echo "KO   git config core.hooksPath: $$hp is not a directory"; rc=1; \
	elif [ -d $(CHAIN_GITHOOKS) ] \
	     && [ "$$(resolve "$$hp")" != "$$(resolve $(CHAIN_GITHOOKS))" ]; then \
	  echo "KO   git config core.hooksPath: $$hp is not $(CHAIN_GITHOOKS)"; rc=1; \
	else echo "ok   git config core.hooksPath = $$hp"; fi; \
	for h in $(CHAIN_GITHOOKS)/*; do \
	  case "$$h" in *.sample|*/\*) continue;; esac; \
	  [ -f "$$h" ] || continue; \
	  if [ -x "$$h" ]; then echo "ok   $$h: git hook executable"; \
	  else echo "KO   $$h: git hook is not executable (git ignores it)"; rc=1; fi; \
	done; \
	is_script() { [ "$$1" != "$${1%.py}" ] || [ "$$1" != "$${1%.sh}" ]; }; \
	hooks=$$(if [ -r $(CHAIN_SETTINGS) ]; then \
	    sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)".*/\1/p' \
	      $(CHAIN_SETTINGS) \
	    | sed -e 's/\\"//g' -e 's|\$$CLAUDE_PROJECT_DIR|$(CHAIN_ROOT)|g' \
	    | while IFS= read -r cmd; do \
	        set -f; set -- $$cmd; set +f; \
	        if is_script "$$1"; then echo "direct $$1"; \
	        elif is_script "$$2"; then echo "interp $$2"; fi; \
	      done \
	    | sort -u \
	    | while read -r mode script; do \
	        if [ ! -f "$$script" ]; then \
	          echo "KO   $$script: hook script of $(CHAIN_SETTINGS) is missing"; \
	        elif [ "$$mode" = direct ] && [ ! -x "$$script" ]; then \
	          echo "KO   $$script: hook script is not executable"; \
	        elif [ ! -r "$$script" ]; then \
	          echo "KO   $$script: hook script is not readable"; \
	        else echo "ok   $$script: hook script runnable ($$mode)"; fi; \
	      done; \
	  fi); \
	if [ -n "$$hooks" ]; then echo "$$hooks"; fi; \
	if printf '%s\n' "$$hooks" | grep -q '^KO'; then rc=1; fi; \
	if [ $$rc -eq 0 ]; then echo "doctor: guard chain in place"; \
	else echo "doctor: 'make env' creates missing links (needs $(CHAIN_OWNER)); other KO lines are fixed by hand"; \
	fi; \
	exit $$rc

env:
	@rc=0; \
	link() { \
	  case "$$2" in /*) tgt=$$2;; *) tgt=$$(dirname "$$1")/$$2;; esac; \
	  if [ ! -e "$$tgt" ]; then \
	    echo "skip $$1: target $$tgt does not exist"; return 0; fi; \
	  if [ -L "$$1" ]; then \
	    cur=$$(readlink "$$1"); \
	    if [ "$$cur" = "$$2" ]; then echo "ok   $$1 -> $$cur"; \
	    else echo "KO   $$1 -> $$cur (expected $$2): left untouched"; return 1; fi; \
	  elif [ -e "$$1" ]; then \
	    echo "KO   $$1: real file/dir, left untouched"; return 1; \
	  else ln -s "$$2" "$$1" && echo "new  $$1 -> $$2"; fi; \
	}; \
	if [ -d $(CHAIN_OWNER)/.claude ]; then mkdir -p .claude; fi; \
	for n in $(CHAIN_LINKS); do \
	  link ".claude/$$n" "$(CHAIN_OWNER_UP)/.claude/$$n" || rc=1; \
	done; \
	link "$(CHAIN_GITHOOKS)" "$(CHAIN_OWNER)/$(CHAIN_GITHOOKS)" || rc=1; \
	if [ -f $(CHAIN_BMAD) ] && [ ! -L $(CHAIN_BMAD) ]; then \
	  echo "ok   $(CHAIN_BMAD): local file kept"; \
	else \
	  if [ -f $(CHAIN_OWNER)/$(CHAIN_BMAD) ]; then mkdir -p $(dir $(CHAIN_BMAD)); fi; \
	  link "$(CHAIN_BMAD)" "$(CHAIN_OWNER_UP)/$(CHAIN_BMAD)" || rc=1; \
	fi; \
	if [ "$$(git rev-parse --is-inside-work-tree 2>/dev/null)" != true ]; then \
	  echo "skip git config core.hooksPath: not a git work tree"; \
	elif [ "$$(git rev-parse --git-dir 2>/dev/null)" \
	     != "$$(git rev-parse --git-common-dir 2>/dev/null)" ]; then \
	  echo "skip git config core.hooksPath: linked worktree, config is shared"; \
	else \
	  $(CHAIN_RESOLVE); \
	  hp=$$(git config --local --get core.hooksPath 2>/dev/null); \
	  here=$$(resolve $(CHAIN_GITHOOKS)); \
	  if [ -z "$$hp" ]; then git config --local core.hooksPath $(CHAIN_GITHOOKS) \
	    && echo "new  git config core.hooksPath = $(CHAIN_GITHOOKS)"; \
	  elif [ -n "$$here" ] && [ "$$(resolve "$$hp")" = "$$here" ]; then \
	    echo "ok   git config core.hooksPath = $$hp"; \
	  else \
	    echo "KO   git config core.hooksPath = $$hp: left untouched"; rc=1; fi; \
	fi; \
	exit $$rc

.PHONY: start test test-cov lint fmt precommit prepush doctor env

endif
