"""
Pytest configuration and fixtures for Pyplet end-to-end tests.
"""

import asyncio
import multiprocessing
import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from pyplet.server import config
from pyplet.server._server import astart


def run_server():
    """Run the Pyplet server in a separate process."""
    asyncio.run(astart())


@pytest.fixture(scope="session")
def server():
    """Start the Pyplet server for the test session."""
    # Start server in a separate process
    server_process = multiprocessing.Process(target=run_server, daemon=True)
    server_process.start()

    # Wait for server to be ready
    time.sleep(3)

    yield f"http://{config.address}:{config.port}"

    # Cleanup
    server_process.terminate()
    server_process.join(timeout=5)
    if server_process.is_alive():
        server_process.kill()


@pytest.fixture(scope="function")
def driver():
    """Create a Selenium WebDriver instance for each test."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Enable browser logging
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)

    yield driver

    # Print browser console logs on teardown (useful for debugging)
    for entry in driver.get_log("browser"):
        print(f"Browser console: {entry}")

    driver.quit()


@pytest.fixture(scope="function")
def wait(driver):
    """Create a WebDriverWait instance with a reasonable timeout."""
    return WebDriverWait(driver, 30)
