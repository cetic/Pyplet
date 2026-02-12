start:
	uv run -m pyplet start

test:
	uv run --extra test pytest tests/ -v

test-cov:
	uv run --extra test pytest tests/ -v --cov=pyplet --cov-report=html --cov-report=term
