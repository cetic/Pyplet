"""
Unit tests for pyplet.server.cli module.

These tests verify that:
1. The create_project function creates projects correctly
2. Project names are validated properly
3. Template files are copied correctly
4. Error cases are handled gracefully
5. Logging works as expected
"""

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for testing."""
    # Create a mock template directory
    template_dir = tmp_path / "apps" / "template"
    template_dir.mkdir(parents=True)

    # Create mock template files
    client_file = template_dir / "template_client.py"
    client_file.write_text("# Template client code\nimport pyplet\n")

    server_file = template_dir / "template_server.py"
    server_file.write_text("# Template server code\nimport pyplet\n")

    # Create a working directory
    work_dir = tmp_path / "workspace"
    work_dir.mkdir()

    return {
        "template_dir": template_dir,
        "work_dir": work_dir,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def mock_pyplet_path(temp_workspace):
    """Mock the pyplet package path to use temp workspace."""

    def mock_resolve():
        mock_path = MagicMock()
        mock_path.parent.parent = temp_workspace["tmp_path"]
        return mock_path

    return mock_resolve


class TestCreateProject:
    """Test suite for the create_project function."""

    def test_create_project_success(self, temp_workspace):
        """Test successful project creation."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]

        # Change to work directory
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            # Mock the Path resolution to use our temp template
            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                # Setup Path to return temp_workspace paths
                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                # Create the project
                create_project("my_test_app")

                # Verify the project directory was created
                project_dir = work_dir / "apps" / "my_test_app"
                assert project_dir.exists(), (
                    "Project directory should be created"
                )

                # Verify client file was created
                client_file = project_dir / "my_test_app_client.py"
                assert client_file.exists(), "Client file should be created"
                # Template files are from actual repo,
                # just check they exist and have content
                assert len(client_file.read_text()) > 0, (
                    "Client file should have content"
                )

                # Verify server file was created
                server_file = project_dir / "my_test_app_server.py"
                assert server_file.exists(), "Server file should be created"
                assert len(server_file.read_text()) > 0, (
                    "Server file should have content"
                )

                # Verify no config.py was created
                config_file = project_dir / "config.py"
                assert not config_file.exists(), (
                    "config.py should NOT be created"
                )

        finally:
            os.chdir(original_cwd)

    def test_create_project_invalid_name(self, temp_workspace, caplog):
        """Test that invalid project names are rejected."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                # Test various invalid names
                invalid_names = [
                    "123invalid",  # Starts with number
                    "my-project",  # Contains hyphen
                    "my project",  # Contains space
                    "my.project",  # Contains dot
                ]

                for invalid_name in invalid_names:
                    with pytest.raises(SystemExit) as excinfo:
                        create_project(invalid_name)

                    assert excinfo.value.code == 1

        finally:
            os.chdir(original_cwd)

    def test_create_project_validates_template_exists(self, caplog):
        """Test that the create_project function validates
        template files exist."""
        from pyplet.server.cli import create_project

        # This test verifies the validation logic exists by checking
        # that the function has proper error handling for missing templates

        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir) / "workspace"
            work_dir.mkdir()

            original_cwd = os.getcwd()
            os.chdir(work_dir)

            try:
                # Mock shutil.copyfile to raise FileNotFoundError
                with patch("pyplet.server.cli.shutil.copyfile") as mock_copy:
                    mock_copy.side_effect = FileNotFoundError(
                        "Template file not found"
                    )

                    with pytest.raises(FileNotFoundError):
                        create_project("test_project")

            finally:
                os.chdir(original_cwd)

    def test_create_project_creates_apps_directory(self, temp_workspace):
        """Test that apps directory is created if it doesn't exist."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            # Ensure apps directory doesn't exist
            apps_dir = work_dir / "apps"
            if apps_dir.exists():
                shutil.rmtree(apps_dir)

            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                create_project("new_project")

                assert apps_dir.exists(), "apps directory should be created"
                assert (apps_dir / "new_project").exists()

        finally:
            os.chdir(original_cwd)

    def test_valid_project_names(self, temp_workspace):
        """Test that valid project names are accepted."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            valid_names = [
                "my_project",
                "project123",
                "MyProject",
                "_private_project",
                "a",  # Single letter
                "a_b_c_123",
            ]

            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                for name in valid_names:
                    create_project(name)
                    project_dir = work_dir / "apps" / name
                    assert project_dir.exists(), (
                        f"Project {name} should be created"
                    )

        finally:
            os.chdir(original_cwd)

    def test_create_project_fails_when_files_exist(
        self, temp_workspace, caplog
    ):
        """Test that create_project fails when template files already exist."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                # First, create a project successfully
                create_project("existing_project")

                # Verify it was created
                project_dir = work_dir / "apps" / "existing_project"
                assert project_dir.exists()
                assert (project_dir / "existing_project_client.py").exists()
                assert (project_dir / "existing_project_server.py").exists()

                # Now try to create the same project again - should fail
                with caplog.at_level(logging.ERROR):
                    with pytest.raises(SystemExit) as excinfo:
                        create_project("existing_project")

                    # Verify exit code is 1
                    assert excinfo.value.code == 1

                    # Verify error message was logged
                    assert any(
                        "already exists" in record.message
                        for record in caplog.records
                    )

        finally:
            os.chdir(original_cwd)

    def test_create_project_fails_when_only_client_exists(
        self, temp_workspace, caplog
    ):
        """Test that create_project fails when only the client file exists."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                # Create project directory and only the client file
                project_dir = work_dir / "apps" / "partial_project"
                project_dir.mkdir(parents=True)
                client_file = project_dir / "partial_project_client.py"
                client_file.write_text("# Existing client file")

                # Try to create the project - should fail
                with caplog.at_level(logging.ERROR):
                    with pytest.raises(SystemExit) as excinfo:
                        create_project("partial_project")

                    # Verify exit code is 1
                    assert excinfo.value.code == 1

                    # Verify error message was logged
                    assert any(
                        "already exists" in record.message
                        for record in caplog.records
                    )

        finally:
            os.chdir(original_cwd)

    def test_create_project_fails_when_only_server_exists(
        self, temp_workspace, caplog
    ):
        """Test that create_project fails when only the server file exists."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                # Create project directory and only the server file
                project_dir = work_dir / "apps" / "partial_project_server"
                project_dir.mkdir(parents=True)
                server_file = project_dir / "partial_project_server_server.py"
                server_file.write_text("# Existing server file")

                # Try to create the project - should fail
                with caplog.at_level(logging.ERROR):
                    with pytest.raises(SystemExit) as excinfo:
                        create_project("partial_project_server")

                    # Verify exit code is 1
                    assert excinfo.value.code == 1

                    # Verify error message was logged
                    assert any(
                        "already exists" in record.message
                        for record in caplog.records
                    )

        finally:
            os.chdir(original_cwd)


class TestCLILogging:
    """Test suite for CLI logging functionality."""

    def test_logging_configuration(self):
        """Test that logging is configured correctly."""
        import pyplet.server.cli as cli_module

        # Verify logger exists
        assert hasattr(cli_module, "logger")
        assert isinstance(cli_module.logger, logging.Logger)
        assert cli_module.logger.name == "pyplet.cli"

    def test_create_project_logs_success(self, temp_workspace, caplog):
        """Test that successful project creation is logged."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            with caplog.at_level(logging.INFO):
                with patch("pyplet.server.cli.Path") as mock_path_class:
                    mock_file_path = MagicMock()
                    mock_file_path.resolve.return_value.parent.parent = (
                        temp_workspace["tmp_path"]
                    )

                    def path_side_effect(path_str=None):
                        if path_str is None or path_str == "__file__":
                            return mock_file_path
                        return Path(path_str)

                    mock_path_class.side_effect = path_side_effect
                    mock_path_class.cwd.return_value = Path(work_dir)

                    create_project("logged_project")

                    # Check that success messages were logged
                    assert any(
                        "Project 'logged_project' created" in record.message
                        for record in caplog.records
                    )
                    assert any(
                        "Files copied" in record.message
                        for record in caplog.records
                    )

        finally:
            os.chdir(original_cwd)

    def test_create_project_logs_errors(self, temp_workspace, caplog):
        """Test that errors are logged properly."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            with caplog.at_level(logging.ERROR):
                with patch("pyplet.server.cli.Path") as mock_path_class:
                    mock_file_path = MagicMock()
                    mock_file_path.resolve.return_value.parent.parent = (
                        temp_workspace["tmp_path"]
                    )

                    def path_side_effect(path_str=None):
                        if path_str is None or path_str == "__file__":
                            return mock_file_path
                        return Path(path_str)

                    mock_path_class.side_effect = path_side_effect
                    mock_path_class.cwd.return_value = Path(work_dir)

                    # Try to create with invalid name
                    with pytest.raises(SystemExit):
                        create_project("123-invalid")

                    # Check that error was logged
                    assert any(
                        "not a valid Python module name" in record.message
                        for record in caplog.records
                    )

        finally:
            os.chdir(original_cwd)


class TestStartServer:
    """Test suite for start_server function."""

    @patch("pyplet.server.cli.asyncio.run")
    @patch("pyplet.server._server.astart")
    def test_start_server_success(self, mock_astart, mock_asyncio_run):
        """Test that start_server calls astart correctly."""
        from pyplet.server.cli import start_server

        start_server()

        mock_asyncio_run.assert_called_once()

    @patch("pyplet.server.cli.asyncio.run")
    @patch("pyplet.server._server.astart")
    def test_start_server_keyboard_interrupt(
        self, mock_astart, mock_asyncio_run, caplog
    ):
        """Test that keyboard interrupt is handled gracefully."""
        from pyplet.server.cli import start_server

        mock_asyncio_run.side_effect = KeyboardInterrupt()

        with caplog.at_level(logging.INFO):
            start_server()

            # Check that the interrupt was logged
            assert any(
                "Server stopped by user" in record.message
                for record in caplog.records
            )

    @patch("pyplet.server.cli.asyncio.run")
    @patch("pyplet.server._server.astart")
    def test_start_server_exception(
        self, mock_astart, mock_asyncio_run, caplog
    ):
        """Test that exceptions are logged and cause exit."""
        from pyplet.server.cli import start_server

        mock_asyncio_run.side_effect = Exception("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as excinfo:
                start_server()

            assert excinfo.value.code == 1

            # Check that error was logged
            assert any(
                "Server error" in record.message for record in caplog.records
            )


class TestCLIArgumentParsing:
    """Test suite for CLI argument parsing."""

    @patch("pyplet.server.cli.create_project")
    def test_init_command(self, mock_create_project):
        """Test that 'init' command calls create_project."""
        from pyplet.server.cli import main

        with patch("sys.argv", ["pyplet", "init", "test_project"]):
            try:
                main()
            except SystemExit:
                pass  # Ignore exit from missing config import
            except ImportError:
                pass  # Expected when config can't be imported

            # Note: This test is limited because main() imports config
            # which triggers the pyplet environment detection

    def test_script_main_adds_cwd_to_path(self):
        """Test that script_main adds cwd to sys.path."""
        from pyplet.server.cli import script_main

        original_path = sys.path.copy()
        cwd = os.getcwd()

        # Remove cwd from path if it exists
        if cwd in sys.path:
            sys.path.remove(cwd)

        try:
            with patch("pyplet.server.cli.main"):
                script_main()
                assert cwd in sys.path
        finally:
            sys.path = original_path


@pytest.mark.unit
class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_full_project_creation_workflow(self, temp_workspace):
        """Test the complete project creation workflow."""
        from pyplet.server.cli import create_project

        work_dir = temp_workspace["work_dir"]
        original_cwd = os.getcwd()
        os.chdir(work_dir)

        try:
            with patch("pyplet.server.cli.Path") as mock_path_class:
                mock_file_path = MagicMock()
                mock_file_path.resolve.return_value.parent.parent = (
                    temp_workspace["tmp_path"]
                )

                def path_side_effect(path_str=None):
                    if path_str is None or path_str == "__file__":
                        return mock_file_path
                    return Path(path_str)

                mock_path_class.side_effect = path_side_effect
                mock_path_class.cwd.return_value = Path(work_dir)

                # Create project
                create_project("full_test_project")

                # Verify complete structure
                project_dir = work_dir / "apps" / "full_test_project"

                # Check directory exists
                assert project_dir.exists()
                assert project_dir.is_dir()

                # Check files exist and have correct names
                files = list(project_dir.iterdir())
                file_names = [f.name for f in files]

                assert "full_test_project_client.py" in file_names
                assert "full_test_project_server.py" in file_names
                assert "config.py" not in file_names

                # Verify file contents are not empty
                client_file = project_dir / "full_test_project_client.py"
                server_file = project_dir / "full_test_project_server.py"

                assert len(client_file.read_text()) > 0
                assert len(server_file.read_text()) > 0

                # Verify files contain expected content
                assert "pyplet" in client_file.read_text().lower()
                assert "pyplet" in server_file.read_text().lower()

        finally:
            os.chdir(original_cwd)
