"""Tests for config module."""
from config import settings, DEVELOPMENT_MODE


class TestConfig:
    def test_settings_loaded(self):
        assert isinstance(settings, dict)
        assert settings["APP_NAME"] == "Kunj"
        assert "ENV" in settings

    def test_development_mode(self):
        assert DEVELOPMENT_MODE is True