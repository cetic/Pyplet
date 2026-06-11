# Pyplet Tests

This directory contains comprehensive tests for Pyplet, including unit tests
 and end-to-end tests.

## Overview

The test suite verifies:

- **CLI functionality**: Project creation, argument parsing, logging
- **Server functionality**: Server startup and routing
- **Client functionality**: Pyodide initialization in the browser
- **WebSocket communication**: Between client and server
- **DOM manipulation**: Updates and rendering
- **Application performance**: Load times and reliability

## Test Structure

### Unit Tests

#### `test_cli.py`

Unit tests for the CLI module (`pyplet.server.cli`):

**Test Classes:**

1. **`TestCreateProject`**: Project creation functionality
   - Successful project creation
   - Invalid project name validation
   - Duplicate project detection
   - Template file validation
   - Apps directory creation
   - Valid project name patterns

2. **`TestCLILogging`**: Logging functionality
   - Logger configuration
   - Success message logging
   - Error message logging

3. **`TestStartServer`**: Server startup
   - Successful server start
   - Keyboard interrupt handling
   - Exception handling

4. **`TestCLIArgumentParsing`**: Command-line argument parsing
   - Init command handling
   - Path management

5. **`TestCLIIntegration`**: Integration tests
   - Full project creation workflow

**Coverage**: 82% of CLI module code

### End-to-End Tests

#### `conftest.py`

Contains pytest fixtures for:

- **`server`**: Starts the Pyplet server in a separate process for the test session
- **`driver`**: Creates a Selenium WebDriver instance for each test (headless Chrome)
- **`wait`**: Provides a WebDriverWait instance with a 30-second timeout

#### `test_template_app.py`

Contains three test classes:

1. **`TestTemplateApp`**: Core functionality tests
   - Homepage loading
   - Template app page structure
   - Pyodide initialization
   - WebSocket message display
   - Page structure verification
   - Multiple page loads
   - JavaScript error detection

2. **`TestTemplateAppPerformance`**: Performance tests
   - App load time verification
   - Pyodide bootstrap completion

3. **`TestTemplateAppEdgeCases`**: Edge case handling
   - Container element existence
   - Page refresh functionality

## Prerequisites

Install test dependencies:

```bash
# Using uv (recommended)
uv sync --group test

# Or using pip
pip install -e ".[test]"
```

### System Requirements

- **Chrome/Chromium**: Required for Selenium WebDriver
- **ChromeDriver**: Should be installed and in PATH
  - On Ubuntu/Debian: `sudo apt-get install chromium-chromedriver`
  - On macOS: `brew install chromedriver`
  - Or download from: <https://chromedriver.chromium.org/>

## Running Tests

### Run all tests

```bash
pytest tests/
```

### Run unit tests only

```bash
pytest tests/test_cli.py
```

### Run end-to-end tests only

```bash
pytest tests/test_template_app.py
```

### Run specific test file

```bash
pytest tests/test_template_app.py
```

### Run CLI tests with coverage

```bash
pytest tests/test_cli.py --cov=pyplet.server.cli --cov-report=term-missing
```

### Run specific test class

```bash
pytest tests/test_template_app.py::TestTemplateApp
```

### Run specific test

```bash
pytest tests/test_template_app.py::TestTemplateApp::test_websocket_message_display
```

### Run with verbose output

```bash
pytest tests/ -v
```

### Run with browser console output

```bash
pytest tests/ -s
```

### Run with coverage

```bash
pytest tests/ --cov=pyplet --cov-report=html
```

## Test Configuration

Tests can be configured via environment variables:

- `PYPLET_ADDR`: Server address (default: `127.0.0.1`)
- `PYPLET_PORT`: Server port (default: `8080`)
- `PYPLET_APPS`: Apps directory (default: `apps`)
- `PYPLET_DEBUG`: Debug mode (default: `1`)

Example:

```bash
PYPLET_PORT=9000 pytest tests/
```

## Debugging Tests

### View browser in non-headless mode

Modify `conftest.py` and comment out the headless option:

```python
# chrome_options.add_argument("--headless")
```

### Capture screenshots on failure

Add this to your test:

```python
def test_something(driver, server):
    try:
        # ... test code ...
    except Exception:
        driver.save_screenshot("failure.png")
        raise
```

### View browser console logs

Browser console logs are automatically printed when tests complete. Look for:

```js
Browser console: {'level': 'INFO', 'message': '...', ...}
```

## Writing New Tests

### Basic test structure

```python
def test_my_feature(driver, server, wait):
    # Navigate to the app
    driver.get(f"{server}/apps/myapp/myapp")

    # Wait for an element
    element = wait.until(
        EC.presence_of_element_located((By.ID, "my-element"))
    )

    # Assert expected behavior
    assert element.text == "Expected value"
```

### Common assertions

```python
# Check element exists
assert driver.find_element(By.ID, "container") is not None

# Check element text
assert element.text == "Hello world!"

# Check element visibility
wait.until(EC.visibility_of_element_located((By.ID, "container")))

# Check for JavaScript errors
logs = driver.get_log("browser")
errors = [log for log in logs if log["level"] == "SEVERE"]
assert len(errors) == 0
```

## Continuous Integration

These tests are designed to run in CI environments. Ensure your CI configuration:

1. Installs Chrome/Chromium and ChromeDriver
2. Installs Python dependencies including test group
3. Sets appropriate environment variables if needed

Example GitHub Actions workflow:

```yaml
- name: Install Chrome
  run: |
    sudo apt-get update
    sudo apt-get install -y chromium-browser chromium-chromedriver

- name: Install dependencies
  run: uv sync --group test

- name: Run tests
  run: pytest tests/ -v
```

## Troubleshooting

### ChromeDriver version mismatch

Ensure ChromeDriver version matches your Chrome version:

```bash
chromedriver --version
google-chrome --version
```

### Timeout errors

- Increase wait timeout in `conftest.py`
- Check if Pyodide is loading correctly (slow network)
- Verify server started successfully

### WebSocket connection failures

- Check firewall settings
- Verify server is listening on correct port
- Check browser console for CORS or connection errors

### Pyodide initialization failures

- Verify internet connection (Pyodide loads from CDN)
- Check browser compatibility
- Review browser console logs for specific errors
