"""Simple tests to verify test infrastructure."""

import os
import pytest
from unittest.mock import patch


class TestBasicFunctionality:
    """Test basic functionality without async."""

    def test_imports_work(self):
        """Test that main module can be imported."""
        import main
        assert hasattr(main, 'BOT_TOKEN')
        assert hasattr(main, 'PORT')
        assert hasattr(main, 'logger')

    def test_environment_configuration(self):
        """Test environment variable configuration."""
        with patch.dict(os.environ, {"BOT_TOKEN": "test_token", "PORT": "8080"}):
            # Reload main to pick up new environment
            import importlib
            import main
            importlib.reload(main)
            assert main.BOT_TOKEN == "test_token"
            assert main.PORT == 8080

    def test_health_handler_exists(self):
        """Test that HealthHandler class exists."""
        from main import HealthHandler
        assert HealthHandler is not None

    def test_utility_functions_exist(self):
        """Test that utility functions are defined."""
        from main import start_http_server
        assert callable(start_http_server)


class TestConstants:
    """Test constant definitions."""

    def test_default_port(self):
        """Test default port setting."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import main
            importlib.reload(main)
            assert main.PORT == 8080

    def test_admin_users_parsing(self):
        """Test admin users parsing."""
        test_users = "123,456,789"
        with patch.dict(os.environ, {"ADMIN_USERS": test_users}):
            import importlib
            import main
            importlib.reload(main)
            assert "123" in main.ADMIN_USERS
            assert "456" in main.ADMIN_USERS
            assert "789" in main.ADMIN_USERS


class TestTypeChecking:
    """Test that the code passes basic type checking."""

    def test_module_has_type_annotations(self):
        """Test that main functions have type annotations."""
        import inspect
        from main import get_real_channel_stats, init_telethon
        
        sig1 = inspect.signature(get_real_channel_stats)
        sig2 = inspect.signature(init_telethon)
        
        # Should have return type annotations
        assert sig1.return_annotation != inspect.Signature.empty
        assert sig2.return_annotation != inspect.Signature.empty