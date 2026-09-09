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
LINT_PATHS := pyplet tests apps/template apps/tutorial

lint:
	uv run --extra test ruff check --no-fix $(LINT_PATHS)
	uv run --extra test ruff format --check $(LINT_PATHS)

fmt:
	uv run --extra test ruff check --fix $(LINT_PATHS)
	uv run --extra test ruff format $(LINT_PATHS)

precommit: lint

prepush: lint test

.PHONY: start test test-cov lint fmt precommit prepush

endif
