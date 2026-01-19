.PHONY: test
test:
	uv run pytest tests/ -v

.PHONY: test-cov
test-cov:
	uv run pytest tests/ -v --cov=pyplet --cov-report=html --cov-report=term

ifeq ($(firstword $(MAKECMDGOALS)),sandbox)
# Remove "sandbox" from the goals before forwarding
SANDBOX_GOALS := $(filter-out sandbox,$(MAKECMDGOALS))

.PHONY: sandbox
sandbox:
	cd .sandbox && $(MAKE) $(SANDBOX_GOALS)

# Prevent "No rule to make target" errors for forwarded goals
$(SANDBOX_GOALS):
	@:
else
sandbox:
	
endif