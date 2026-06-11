# Quick Start Guide - Running Pyplet Tests

## Installation

### 1. Install test dependencies

Using `uv` (recommended):

```bash
uv sync --group test
```

Or using `pip`:

```bash
pip install -e ".[test]"
```

### 2. Install ChromeDriver

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver
```

**macOS:**

```bash
brew install chromedriver
```

**Manual installation:**
Download from <https://chromedriver.chromium.org/> and add to PATH

Verify installation:

```bash
chromedriver --version
```

## Running Tests

### Quick run (all tests)

```bash
pytest tests/
```

### Run with detailed output

```bash
pytest tests/ -v -s
```

### Run specific test

```bash
# Run all template app tests
pytest tests/test_template_app.py

# Run specific test class
pytest tests/test_template_app.py::TestTemplateApp

# Run single test
pytest tests/test_template_app.py::TestTemplateApp::test_websocket_message_display
```

### Run with coverage

```bash
pytest tests/ --cov=pyplet --cov-report=html
# Open htmlcov/index.html in browser to see coverage report
```

## Expected Output

Successful test run:

```bash
tests/test_template_app.py::TestTemplateApp::test_homepage_loads PASSED
tests/test_template_app.py::TestTemplateApp::test_template_app_page_loads PASSED
tests/test_template_app.py::TestTemplateApp::test_pyodide_initialization PASSED
tests/test_template_app.py::TestTemplateApp::test_websocket_message_display PASSED
...
======================== 15 passed in 45.23s =========================
```

## Troubleshooting

### Test fails with "ChromeDriver not found"

- Make sure ChromeDriver is installed and in your PATH
- Try: `which chromedriver` (should show path)

### Test fails with timeout

- Pyodide takes time to initialize (up to 30 seconds is normal)
- Check your internet connection (Pyodide loads from CDN)
- Increase timeout in `conftest.py` if needed

### Server port already in use

```bash
# Change port before running tests
PYPLET_PORT=9000 pytest tests/
```

### Browser console errors

- Tests automatically print browser console logs
- Look for "Browser console:" in test output
- Run with `-s` flag to see all output: `pytest tests/ -s`

## Next Steps

- Read `tests/README.md` for detailed documentation
- Write your own tests following the examples in `test_template_app.py`
- Configure CI/CD to run tests automatically
