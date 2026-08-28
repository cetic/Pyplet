import pytest

# Assuming this is your import path:
from pyplet.server.config import Param, PypletConfig


class MockConfig:
    """A dummy class to host our Param descriptors for testing."""

    # Standard param with automatic env_var (PORT) and casting (int)
    port = Param(default=8080, description="Server port", type_cast=int)

    # Standard param with string default
    host = Param(default="127.0.0.1", description="Server host")

    # Param with explicit env_var
    secret = Param(
        default="default_secret",
        description="Secret key",
        env_var="APP_SECRET",
    )

    # Param with a callable default (lazy evaluation)
    url = Param(
        default=lambda instance: f"http://{instance.host}:{instance.port}",
        description="Full URL",
    )


class TestParamDescriptor:
    @pytest.fixture
    def config(self):
        """Returns a fresh instance of MockConfig for each test."""
        return MockConfig()

    def test_set_name_and_class_access(self):
        """Test __set_name__ populates name/env_var and
        class access returns the Param."""
        # Accessing via the class should return the Param object itself
        assert isinstance(MockConfig.port, Param)

        # Verify __set_name__ populated the name correctly
        assert MockConfig.port.name == "port"
        assert MockConfig.secret.name == "secret"

        # Verify env_var logic (automatic vs explicit)
        assert MockConfig.port.env_var == "PORT"
        assert MockConfig.secret.env_var == "APP_SECRET"

    def test_default_values(self, config):
        """Test fallback to static default values."""
        assert config.port == 8080
        assert config.host == "127.0.0.1"

    def test_callable_default(self, config):
        """Test that callable defaults are executed and
        passed the instance."""
        assert config.url == "http://127.0.0.1:8080"

        # If we change host/port, the callable
        # should reflect it (if called again)
        # Note: In your current implementation,
        # it evaluates every time it's accessed
        # unless overridden by env or __set__.
        config.port = 9000
        assert config.url == "http://127.0.0.1:9000"

    def test_environment_variable_override(self, config, monkeypatch):
        """Test that environment variables override defaults and
        apply type casting."""
        # Use pytest's monkeypatch fixture to safely modify the environment
        monkeypatch.setenv("PORT", "3000")
        monkeypatch.setenv("APP_SECRET", "super_secret")

        # '3000' should be cast to int(3000)
        assert config.port == 3000
        assert config.secret == "super_secret"

    def test_instance_override_set(self, config):
        """Test __set__ saves to instance dict and applies type casting."""
        # Set directly (simulating CLI override)
        config.port = "4000"  # Passing a string, should be cast to int

        assert config.port == 4000
        assert config.__dict__["port"] == 4000

    def test_set_none(self, config):
        """Test that setting a Param to None works and bypasses casting."""
        config.port = None
        assert config.port is None
        assert config.__dict__["port"] is None

    def test_resolution_priority(self, config, monkeypatch):
        """Test the priority: Instance (__dict__) > Environment > Default."""
        # 1. Base default
        assert config.port == 8080

        # 2. Environment takes precedence over default
        monkeypatch.setenv("PORT", "5000")
        assert config.port == 5000

        # 3. Instance explicit set takes precedence over environment
        config.port = 6000
        assert config.port == 6000


class TestWsMaxMessageMbParam:
    """Story 18.17: the PYPLET_WS_MAX_MESSAGE_MB knob on the real config.

    Mirrors the ``port`` Param idiom above but on the concrete
    ``PypletConfig`` so the real env var name is exercised. The env override is
    verified on the Param here, not on the import-frozen ``_app_spec``.
    """

    @pytest.fixture
    def config(self):
        """A fresh PypletConfig instance for each test."""
        return PypletConfig()

    def test_default_is_40(self, config):
        """Default frame cap is 40 MB (carries a 25 MB base64'd upload)."""
        assert config.ws_max_message_mb == 40

    def test_env_var_name(self):
        """The Param binds the PYPLET_WS_MAX_MESSAGE_MB env variable."""
        assert (
            PypletConfig.ws_max_message_mb.env_var
            == "PYPLET_WS_MAX_MESSAGE_MB"
        )

    def test_env_override_casts_to_int(self, config, monkeypatch):
        """An env override wins over the default and is cast to int."""
        monkeypatch.setenv("PYPLET_WS_MAX_MESSAGE_MB", "64")
        assert config.ws_max_message_mb == 64
