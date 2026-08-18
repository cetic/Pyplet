"""
Pytest configuration and fixtures for Pyplet end-to-end tests.
"""

import asyncio
import multiprocessing
import os
import socket
import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from pyplet.server._server import astart
from pyplet.server.config import config

# The e2e suite must boot ANONYMOUSLY and deterministically. Any app in
# apps/ may load developer OAuth credentials from its own local .env at
# import time during server boot, flipping auth_enabled() to
# True — every app page then 302s to /login and the DOM assertions time out.
# Empty strings (not pop) are deliberate: the keys stay PRESENT in the
# environment, so an app-level load_dotenv(override=False) ("shell wins")
# cannot re-populate them from its .env, while the empty value stays falsy
# for oauth.enabled_providers() / magiclink.enabled().
_ANON_AUTH_ENV = {
    "PYPLET_REQUIRE_AUTH": "",
    "PYPLET_ALLOW_MAGICLINK": "",
    "OAUTH_GOOGLE_CLIENT_ID": "",
    "OAUTH_GOOGLE_CLIENT_SECRET": "",
    "OAUTH_MICROSOFT_CLIENT_ID": "",
    "OAUTH_MICROSOFT_CLIENT_SECRET": "",
    "MAGICLINK_SMTP_HOST": "",
}


def _free_port() -> int:
    """Ask the OS for a free ephemeral port.

    The default port (8080) is routinely held by another dev server on
    contributor machines — binding it makes the whole e2e suite
    silently exercise the WRONG server (404s / stale pages), so the suite
    must always run on its own fresh port.
    """
    with socket.socket() as sock:
        sock.bind((config.address, 0))
        return sock.getsockname()[1]


def run_server(port: int):
    """Run the Pyplet server in a separate process (anonymous mode)."""
    os.environ.update(_ANON_AUTH_ENV)
    os.environ["PYPLET_PORT"] = str(port)
    asyncio.run(astart())


@pytest.fixture(scope="session")
def server():
    """Start the Pyplet server for the test session on a free port."""
    port = _free_port()
    server_process = multiprocessing.Process(
        target=run_server, args=(port,), daemon=True
    )
    server_process.start()

    # Wait for the server to actually accept connections (fail fast if the
    # child died, e.g. import error) instead of a blind sleep.
    deadline = time.monotonic() + 30
    while True:
        if not server_process.is_alive():
            raise RuntimeError(
                "Pyplet test server process exited during startup"
            )
        try:
            with socket.create_connection((config.address, port), timeout=1):
                break
        except OSError:
            if time.monotonic() > deadline:
                server_process.terminate()
                raise RuntimeError(
                    f"Pyplet test server not reachable on port {port} "
                    "after 30s"
                )
            time.sleep(0.2)

    yield f"http://{config.address}:{port}"

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
