import importlib
import sys
from unittest.mock import MagicMock, patch

import pyplet


class TestEnvironmentInitialization:
    def test_client_environment_fallback(self):
        # 1. Clean up cached attributes
        if hasattr(pyplet, "server"):
            delattr(pyplet, "server")
        if hasattr(pyplet, "client"):  # Good practice to clean this up too!
            delattr(pyplet, "client")

        # 2. Block the server modules
        patched_modules = {
            name: None
            for name in list(sys.modules.keys())
            if name.startswith("pyplet.server")
        }
        patched_modules["pyplet.server"] = None

        # 3. Inject the fake browser modules
        mock_js = MagicMock()
        mock_pyscript = MagicMock()  # Often needed alongside 'js'

        patched_modules["js"] = mock_js
        patched_modules["pyscript"] = mock_pyscript

        # 4. Apply the roadblocks AND the fake modules
        with patch.dict("sys.modules", patched_modules):
            # Reload to trigger the fallback
            importlib.reload(pyplet)

            # Verify the fallback worked
            assert pyplet.is_server is False
            assert pyplet.is_client is True

        # 5. Clean up: reload normally so the rest of your test suite survives
        importlib.reload(pyplet)
