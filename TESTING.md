# Pyplet Testing Guide

This document provides an overview of the testing infrastructure for Pyplet applications.

## Overview

The Pyplet test suite uses **Selenium WebDriver** for end-to-end testing of applications. Tests verify the complete stack including:

- Server startup and HTTP routing
- Pyodide (WebAssembly Python) initialization in the browser
- WebSocket communication between client and server
- DOM manipulation and rendering
- Application performance and reliability

## Quick Start

### Install test dependencies

```bash
# Using uv (recommended)
uv sync --group test

# Or using pip
pip install -e ".[test]"
```

### Install ChromeDriver

```bash
# Ubuntu/Debian
sudo apt-get install -y chromium-browser chromium-chromedriver

# macOS
brew install chromedriver
```

### Run tests

```bash
pytest tests/
```

For more details, see [`tests/QUICKSTART.md`](tests/QUICKSTART.md).

## Test Structure

```
tests/
├── __init__.py           # Package marker
├── conftest.py           # Pytest fixtures (server, driver, wait)
├── test_template_app.py  # End-to-end tests for template app
├── README.md             # Detailed testing documentation
└── QUICKSTART.md         # Quick start guide
```

## Test Coverage

The current test suite covers the **template application** with the following test categories:

### Core Functionality (`TestTemplateApp`)
- ✅ Homepage loading
- ✅ Template app page structure
- ✅ Pyodide initialization
- ✅ WebSocket message display
- ✅ Page structure verification (scripts, styles)
- ✅ Multiple page loads
- ✅ WebSocket connection establishment
- ✅ JavaScript error detection

### Performance (`TestTemplateAppPerformance`)
- ✅ App load time verification (< 30 seconds)
- ✅ Pyodide bootstrap completion

### Edge Cases (`TestTemplateAppEdgeCases`)
- ✅ Container element existence
- ✅ Page refresh functionality

**Total: 15 tests**

## Writing Tests

### Basic test pattern

```python
def test_my_feature(driver, server, wait):
    """Test description."""
    # Navigate to app
    driver.get(f"{server}/apps/myapp/myapp")
    
    # Wait for element
    element = wait.until(
        EC.presence_of_element_located((By.ID, "my-element"))
    )
    
    # Assert
    assert element.text == "Expected value"
```

### Available fixtures

- **`server`**: Server URL (e.g., `http://127.0.0.1:8080`)
- **`driver`**: Selenium WebDriver instance (headless Chrome)
- **`wait`**: WebDriverWait with 30-second timeout

## Continuous Integration

A GitHub Actions workflow is provided at `.github/workflows/test.yml` that:

1. Sets up Python 3.12
2. Installs Chrome and ChromeDriver
3. Installs dependencies with `uv`
4. Downloads Pyodide
5. Runs the test suite
6. Uploads coverage reports to Codecov

The workflow runs on:
- Push to `master`, `main`, or `develop` branches
- Pull requests targeting those branches

## Test Configuration

Tests respect Pyplet environment variables:

```bash
PYPLET_ADDR=127.0.0.1    # Server address
PYPLET_PORT=8080         # Server port
PYPLET_APPS=apps         # Apps directory
PYPLET_DEBUG=1           # Debug mode
```

Pytest configuration is in [`pytest.ini`](pytest.ini).

## Running Specific Tests

```bash
# All tests
pytest tests/

# Specific file
pytest tests/test_template_app.py

# Specific class
pytest tests/test_template_app.py::TestTemplateApp

# Specific test
pytest tests/test_template_app.py::TestTemplateApp::test_websocket_message_display

# With coverage
pytest tests/ --cov=pyplet --cov-report=html
```

## Debugging Tests

### View browser console logs
Browser logs are automatically printed after each test. Run with `-s` to see all output:

```bash
pytest tests/ -s
```

### Run in non-headless mode
Edit `tests/conftest.py` and comment out:
```python
# chrome_options.add_argument("--headless")
```

### Save screenshots on failure
```python
def test_something(driver, server):
    try:
        # ... test code ...
    except Exception:
        driver.save_screenshot("failure.png")
        raise
```

## Dependencies

### Runtime Dependencies
- `tornado` - Async web server
- `pyodide-build` - Pyodide integration

### Test Dependencies
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `selenium` - Browser automation

### System Dependencies
- Chrome/Chromium browser
- ChromeDriver (matching Chrome version)

## Common Issues

### Timeout errors
- Pyodide initialization can take up to 30 seconds
- Check internet connection (Pyodide loads from CDN)
- Increase timeout in `conftest.py` if needed

### ChromeDriver version mismatch
```bash
chromedriver --version
google-chrome --version
# Versions should match
```

### Port already in use
```bash
PYPLET_PORT=9000 pytest tests/
```

## Future Enhancements

Potential areas for test expansion:

- [ ] Unit tests for individual modules (server, client, WebSocket)
- [ ] Integration tests for multi-app scenarios
- [ ] Performance benchmarks
- [ ] Browser compatibility tests (Firefox, Safari)
- [ ] WebSocket reconnection and error handling tests
- [ ] Tests for other example applications
- [ ] Visual regression testing

## Resources

- **Detailed documentation**: [`tests/README.md`](tests/README.md)
- **Quick start guide**: [`tests/QUICKSTART.md`](tests/QUICKSTART.md)
- **Pytest docs**: https://docs.pytest.org/
- **Selenium docs**: https://www.selenium.dev/documentation/
- **Pyodide docs**: https://pyodide.org/

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use descriptive test names that explain what is being tested
3. Add docstrings to test functions
4. Group related tests into test classes
5. Use appropriate markers (`@pytest.mark.slow`, etc.)
6. Ensure tests are isolated and don't depend on each other
7. Update this document if adding new test categories

---

For questions or issues, please refer to the main [README.md](README.md) or open an issue on GitHub.
