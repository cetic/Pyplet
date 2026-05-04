"""
Pytest configuration and fixtures for Pyplet end-to-end tests.
"""

import asyncio
import multiprocessing
import os
import shutil
import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

from pyplet.server._server import astart
from pyplet.server.config import config


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
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Enable browser logging
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    # Ensure Selenium uses the Chromium binary installed by apt on CI
    chrome_bin = (
        os.environ.get("CHROME_BIN")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
        or "/usr/bin/chromium"
    )
    chrome_options.binary_location = chrome_bin

    # Be explicit about chromedriver too (helps avoid PATH surprises)
    chromedriver_path = (
        os.environ.get("CHROMEDRIVER")
        or shutil.which("chromedriver")
        or "/usr/bin/chromedriver"
    )
    service = Service(executable_path=chromedriver_path)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)

    yield driver

    for entry in driver.get_log("browser"):
        print(f"Browser console: {entry}")

    driver.quit()


@pytest.fixture(scope="function")
def wait(driver):
    """Create a WebDriverWait instance with a reasonable timeout."""
    return WebDriverWait(driver, 30)
