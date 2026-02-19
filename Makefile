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
	uv run --extra test pytest tests/ -v

test-cov:
	uv run --extra test pytest tests/ -v --cov=pyplet --cov-report=html --cov-report=term

endif