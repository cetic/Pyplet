"""
End-to-end tests for the template application using Selenium.

These tests verify that:
1. The application loads correctly
2. Pyscript initializes successfully
3. WebSocket communication works between client and server
4. The DOM is updated as expected
"""

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class TestTemplateApp:
    """Test suite for the template application."""

    def test_homepage_loads(self, driver, server):
        """Test that the main homepage loads successfully."""
        driver.get(server)
        assert "Pyplet" in driver.title or driver.title != ""

    def test_template_app_page_loads(self, driver, server, wait):
        """Test that the template app page loads and
        has the container element."""
        driver.get(f"{server}/apps/template/template")

        # Wait for the container div to be present
        container = wait.until(
            EC.presence_of_element_located((By.ID, "container"))
        )
        assert container is not None

    def test_pyscript_initialization(self, driver, server, wait):
        """Test that Pyscript loads successfully."""
        driver.get(f"{server}/apps/template/template")

        # Wait for container to be present
        wait.until(EC.presence_of_element_located((By.ID, "container")))

        # Check browser console for Pyscript loading errors
        time.sleep(2)  # Give Pyscript time to initialize

        logs = driver.get_log("browser")
        severe_errors = [log for log in logs if log["level"] == "SEVERE"]

        # Filter out expected errors (some browser warnings are normal)
        pyscript_errors = [
            err
            for err in severe_errors
            if "pyscript" in err["message"].lower()
        ]

        assert len(pyscript_errors) == 0, (
            f"Pyscript errors found: {pyscript_errors}"
        )

    def test_websocket_message_display(self, driver, server, wait):
        """Test that the WebSocket message from server is
        displayed in the container."""
        driver.get(f"{server}/apps/template/template")

        # Wait for the container element
        container = wait.until(
            EC.presence_of_element_located((By.ID, "container"))
        )

        # Wait for the message to appear
        # (WebSocket communication + Pyscript initialization)
        # The server sends "Hello world!"
        # which should be displayed in the container
        wait.until(
            EC.text_to_be_present_in_element(
                (By.ID, "container"), "Hello world!"
            )
        )

        # Verify the exact text
        assert container.text == "Hello world!"

    def test_page_structure(self, driver, server, wait):
        """Test that the page has the expected HTML structure."""
        driver.get(f"{server}/apps/template/template")

        # Check for Pyscript script tag
        scripts = driver.find_elements(By.TAG_NAME, "script")
        pyscript_script = any(
            "pyscript" in script.get_attribute("src") or ""
            for script in scripts
        )
        assert pyscript_script, "Pyscript script not found"

    def test_multiple_page_loads(self, driver, server, wait):
        """Test that the app works correctly across multiple page loads."""
        for _ in range(3):
            driver.get(f"{server}/apps/template/template")

            container = wait.until(
                EC.presence_of_element_located((By.ID, "container"))
            )

            wait.until(
                EC.text_to_be_present_in_element(
                    (By.ID, "container"), "Hello world!"
                )
            )

            assert container.text == "Hello world!"

    def test_websocket_connection_established(self, driver, server, wait):
        """Test that WebSocket connection is established successfully."""
        driver.get(f"{server}/apps/template/template")

        # Wait for container to have content (indicates WebSocket worked)
        container = wait.until(
            EC.presence_of_element_located((By.ID, "container"))
        )

        # Wait for non-empty text (message received via WebSocket)
        wait.until(lambda d: container.text != "")

        # If we got here, WebSocket communication succeeded
        assert container.text != "", (
            "Container should have received WebSocket message"
        )

    def test_no_javascript_errors(self, driver, server, wait):
        """Test that no severe JavaScript errors occur during app execution."""
        driver.get(f"{server}/apps/template/template")

        # Wait for the app to fully load
        wait.until(
            EC.text_to_be_present_in_element(
                (By.ID, "container"), "Hello world!"
            )
        )

        # Additional wait to ensure all async operations complete
        time.sleep(1)

        # Check for severe JavaScript errors
        logs = driver.get_log("browser")
        severe_errors = [log for log in logs if log["level"] == "SEVERE"]

        # Some errors might be acceptable (e.g., network errors in dev mode)
        # Filter for critical errors only
        critical_errors = [
            err
            for err in severe_errors
            if not any(
                ignorable in err["message"].lower()
                for ignorable in ["favicon", "css", "net::err"]
            )
        ]

        assert len(critical_errors) == 0, (
            f"Critical JavaScript errors: {critical_errors}"
        )


class TestTemplateAppPerformance:
    """Performance and timing tests for the template application."""

    def test_app_loads_within_reasonable_time(self, driver, server, wait):
        """Test that the app loads and displays content within a
        reasonable time."""
        start_time = time.time()

        driver.get(f"{server}/apps/template/template")

        # Wait for message to appear
        wait.until(
            EC.text_to_be_present_in_element(
                (By.ID, "container"), "Hello world!"
            )
        )

        end_time = time.time()
        load_time = end_time - start_time

        # Pyscript initialization can take a while,
        # but should be under 30 seconds
        assert load_time < 30, (
            f"App took too long to load: {load_time:.2f} seconds"
        )

    def test_pyscript_bootstrap_completes(self, driver, server, wait):
        """Test that the Pyscript bootstrap process completes successfully."""
        driver.get(f"{server}/apps/template/template")

        # The bootstrap process should result in the message being displayed
        # If bootstrap fails, the container will remain empty
        container = wait.until(
            EC.presence_of_element_located((By.ID, "container"))
        )

        # Wait up to 30 seconds for bootstrap to complete
        wait.until(
            EC.text_to_be_present_in_element(
                (By.ID, "container"), "Hello world!"
            )
        )

        assert container.text == "Hello world!"


class TestTemplateAppEdgeCases:
    """Edge case and error handling tests."""

    def test_container_element_exists(self, driver, server, wait):
        """Test that container element exists immediately on page load."""
        driver.get(f"{server}/apps/template/template")

        # Container should exist in the initial HTML
        container = driver.find_element(By.ID, "container")
        assert container is not None

    def test_page_refresh_preserves_functionality(self, driver, server, wait):
        """Test that refreshing the page maintains app functionality."""
        driver.get(f"{server}/apps/template/template")

        # Wait for initial load
        wait.until(
            EC.text_to_be_present_in_element(
                (By.ID, "container"), "Hello world!"
            )
        )

        # Refresh the page
        driver.refresh()

        # Verify it still works
        wait.until(
            EC.text_to_be_present_in_element(
                (By.ID, "container"), "Hello world!"
            )
        )

        container = driver.find_element(By.ID, "container")
        assert container.text == "Hello world!"
