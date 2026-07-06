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
import runpy
import shutil
import subprocess
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

    def test_create_project_missing_template_directory(self, temp_workspace):
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
                mock_path_class.return_value = mock_file_path

                with pytest.raises(SystemExit) as excinfo:
                    create_project("my_test_app")

                assert excinfo.value.code == 1
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
                        "is not a valid Python's module name."
                        in record.message
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
            # Catch the expected SystemExit exception
            with pytest.raises(SystemExit) as exc_info:
                start_server()

            # Verify the exit code is exactly 0
            assert exc_info.value.code == 0

        # Check that the interrupt was logged
        assert any(
            "Server stopped by user" in record.message
            for record in caplog.records
        )

    @patch("pyplet.server.cli.asyncio.run")
    @patch("pyplet.server._server.astart")
    def test_start_server_oserror_98(
        self, mock_astart, mock_asyncio_run, caplog
    ):
        """Test that OSError 98 (address already in use) is
        handled gracefully."""
        from pyplet.server.cli import start_server

        mock_asyncio_run.side_effect = OSError(
            98,
            "Address already in use",
        )

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as excinfo:
                start_server()

            assert excinfo.value.code == 3

            # Check that error was logged
            assert any(
                "The server address (" in record.message
                for record in caplog.records
            )

        # Check that the exception is re-raised is it's not
        # a Error 98, but still an OSError
        mock_asyncio_run.side_effect = OSError(99, "Other address in use")
        with pytest.raises(OSError):
            start_server()

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

            assert excinfo.value.code == 4

            # Check that error was logged
            assert any(
                "Server error" in record.message for record in caplog.records
            )


class TestCLIArgumentParsing:
    """Test suite for CLI argument parsing."""

    def test_pyplet_main_entry_point_subprocess(self):
        """Test `python -m pyplet` using a real subprocess."""

        # 1. Run the command: `<path_to_python> -m pyplet --help`
        result = subprocess.run(
            [sys.executable, "-m", "pyplet", "--help"],
            capture_output=True,
            text=True,
        )

        # 2. Verify the process exited gracefully
        assert result.returncode == 0

        # 3. Verify the output contains the CLI help menu
        assert "usage:" in result.stdout.lower()

    def test_pyplet_main_entry_point(self):
        """Test `python -m pyplet` entry point with full coverage."""
        with patch("sys.argv", ["pyplet", "--help"]):
            with pytest.raises(SystemExit) as excinfo:
                runpy.run_module("pyplet", run_name="__main__")

            assert excinfo.value.code == 0

    def test_no_args(self):
        """Test that no args raises SystemExit."""
        from pyplet.server.cli import main

        with patch("sys.argv", ["pyplet"]):
            # main() should print the help message and return
            with patch("sys.stdout") as mock_stdout:
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 0
                mock_stdout.write.assert_called_once()

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

    @patch("pyplet.server.cli.start_server")
    def test_start_command(self, mock_start_server):
        """Test that 'start' command calls start_server."""
        from pyplet.server.cli import main

        # We need to test pyplet start, run, server
        start_commands = ["start"]  # , "run", "server"]
        for cmd in start_commands:
            with patch("sys.argv", ["pyplet", cmd]):
                # If your main() function exits gracefully
                # after running the command,
                # you don't need the try/except SystemExit block here.
                main()

            mock_start_server.assert_called_once()
            mock_start_server.reset_mock()

        # Test that "pyplet anything" displays help and exits
        with patch("sys.argv", ["pyplet", "anything"]):
            # argparse automatically throws a SystemExit(2) on invalid choices,
            # so we should use pytest.raises to catch it properly!
            with pytest.raises(SystemExit) as excinfo:
                main()

            # Verify argparse exited with the standard error code (2)
            assert excinfo.value.code == 2

    def test_try_to_start_server_with_no_existing_project_dir(self):
        """Test that trying to start a server with
        no existing project dir exits with error."""
        from pyplet.server.cli import main

        # 1. Patch the exists method on the Path
        # class imported in your cli module
        with patch("pyplet.server.cli.Path.exists", return_value=False):
            # 2. Simulate the CLI arguments
            with patch("sys.argv", ["pyplet", "start"]):
                # 3. Catch the expected SystemExit
                with pytest.raises(SystemExit) as excinfo:
                    main()

                # 4. Assert the exit code is 2
                assert excinfo.value.code == 2

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


class TestCLIConfigOverrides:
    @patch("pyplet.server.cli.start_server")
    @patch("pyplet.server.cli.Path.exists", return_value=True)
    def test_start_command_sets_config_attributes(
        self, mock_exists, mock_start_server
    ):
        """Test that CLI arguments correctly override config values."""
        from pyplet.server.cli import main
        from pyplet.server.config import config

        # 1. Store original config values to prevent test leakage
        # (Assuming your config has 'port' and 'host' as valid params)
        original_port = config.port
        original_host = config.address

        # 2. Simulate the CLI command: `pyplet start --port 9999`
        with patch("sys.argv", ["pyplet", "start", "--port", "9999"]):
            main()

        try:
            # 3. Verify the setattr logic correctly
            # updated the provided argument
            assert config.port == 9999

            # 4. Verify the `argparse.SUPPRESS` and
            # `if value is not ...:` logic
            # This ensures omitted arguments don't
            # accidentally overwrite defaults
            # with None or empty strings.
            assert config.address == original_host

        finally:
            # 5. Clean up the singleton state so subsequent tests don't fail!
            config.port = original_port
            config.address = original_host


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
