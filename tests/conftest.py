"""
Pytest configuration and fixtures for Pyplet end-to-end tests.
"""

import asyncio
import multiprocessing
import os
import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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


# @pytest.fixture(scope="function")
# def driver():
#     chrome_options = Options()
#     chrome_options.add_argument("--headless=new")
#     chrome_options.add_argument("--no-sandbox")
#     chrome_options.add_argument("--disable-dev-shm-usage")

#     # 1. Use the environment (from GitHub Actions)
#     # or fallback to system PATH for Chrome binary
#     chrome_bin = os.environ.get("CHROME_BIN") or shutil.which("chromium")

#     if chrome_bin:
#         chrome_options.binary_location = chrome_bin

#     # 2. Use the corrected ChromeDriver path
#     chromedriver_path = os.environ.get("CHROMEDRIVER") or shutil.which(
#         "chromedriver"
#     )

#     service = (
#         Service(executable_path=chromedriver_path)
#         if chromedriver_path
#         else Service()
#     )

#     driver = webdriver.Chrome(service=service, options=chrome_options)
#     driver.implicitly_wait(10)

#     yield driver
#     driver.quit()


@pytest.fixture(scope="function")
def driver():
    """Create a Selenium WebDriver instance for each test."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    if os.environ.get("CI"):
        chrome_options.binary_location = "/usr/bin/chromium-browser"
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
