"""
Tests for CLI config subcommand.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from typer.testing import CliRunner

from sogon.cli import app
from sogon.config.user_config import UserConfigManager


runner = CliRunner()


class TestConfigGet:
    """Tests for 'sogon config get' command."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_manager(self, temp_config_dir):
        """Create a mock UserConfigManager."""
        manager = UserConfigManager(config_dir=temp_config_dir)
        return manager

    def test_config_get_all_shows_settings(self, mock_manager):
        """Test 'sogon config get' shows all settings."""
        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "get"])

        assert result.exit_code == 0
        assert "output_base_dir" in result.stdout
        assert "Use --verbose" in result.stdout

    def test_config_get_specific_key(self, mock_manager):
        """Test 'sogon config get <key>' shows specific value."""
        mock_manager.set("log_level", "DEBUG")

        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "get", "log_level"])

        assert result.exit_code == 0
        assert "log_level=DEBUG" in result.stdout

    def test_config_get_default_value(self, mock_manager):
        """Test 'sogon config get <key>' shows default when not set."""
        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "get", "output_base_dir"])

        assert result.exit_code == 0
        assert "output_base_dir=./result" in result.stdout
        assert "(default)" in result.stdout

    def test_config_get_unknown_key_error(self, mock_manager):
        """Test 'sogon config get <unknown>' returns error."""
        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "get", "unknown_key"])

        assert result.exit_code == 1
        # Error messages go to stderr, use output which combines both
        assert "Error:" in result.output
        assert "unknown_key" in result.output
        assert "Available keys:" in result.output


class TestConfigSet:
    """Tests for 'sogon config set' command."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_manager(self, temp_config_dir):
        """Create a mock UserConfigManager."""
        manager = UserConfigManager(config_dir=temp_config_dir)
        return manager

    def test_config_set_valid_value(self, mock_manager):
        """Test 'sogon config set <key> <value>' sets value."""
        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "set", "log_level", "DEBUG"])

        assert result.exit_code == 0
        assert "Set log_level=DEBUG" in result.stdout
        assert mock_manager.get("log_level") == "DEBUG"

    def test_config_set_invalid_choice(self, mock_manager):
        """Test 'sogon config set' with invalid choice returns error."""
        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "set", "log_level", "INVALID"])

        assert result.exit_code == 1
        # Error messages go to stderr, use output which combines both
        assert "Error:" in result.output

    def test_config_set_unknown_key_error(self, mock_manager):
        """Test 'sogon config set <unknown>' returns error."""
        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "set", "unknown_key", "value"])

        assert result.exit_code == 1
        # Error messages go to stderr, use output which combines both
        assert "Error:" in result.output


class TestConfigReset:
    """Tests for 'sogon config reset' command."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_manager(self, temp_config_dir):
        """Create a mock UserConfigManager."""
        manager = UserConfigManager(config_dir=temp_config_dir)
        return manager

    def test_config_reset_specific_key(self, mock_manager):
        """Test 'sogon config reset <key>' resets specific key."""
        mock_manager.set("log_level", "DEBUG")

        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "reset", "log_level"])

        assert result.exit_code == 0
        assert "Reset log_level to default" in result.stdout
        assert mock_manager.get("log_level") is None

    def test_config_reset_all_with_force(self, mock_manager):
        """Test 'sogon config reset --force' resets all."""
        mock_manager.set("log_level", "DEBUG")
        mock_manager.set("output_base_dir", "/custom")

        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "reset", "--force"])

        assert result.exit_code == 0
        assert "All configuration reset" in result.stdout
        assert mock_manager.get_all() == {}

    def test_config_reset_all_cancelled(self, mock_manager):
        """Test 'sogon config reset' cancelled by user."""
        mock_manager.set("log_level", "DEBUG")

        with patch("sogon.config.user_config.get_user_config_manager", return_value=mock_manager):
            result = runner.invoke(app, ["config", "reset"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        # Value should still be set
        assert mock_manager.get("log_level") == "DEBUG"


class TestConfigList:
    """Tests for 'sogon config list' command."""

    def test_config_list_shows_all_keys(self):
        """Test 'sogon config list' shows all available keys."""
        result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        assert "Available Configuration Keys:" in result.stdout
        assert "output_base_dir" in result.stdout
        assert "Description:" in result.stdout
        assert "Default:" in result.stdout


class TestConfigPath:
    """Tests for 'sogon config path' command."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_config_path_shows_location(self, temp_config_dir):
        """Test 'sogon config path' shows config location."""
        manager = UserConfigManager(config_dir=temp_config_dir)

        with patch("sogon.config.user_config.get_user_config_manager", return_value=manager):
            result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert "Config directory:" in result.stdout
        assert "Config file:" in result.stdout


class TestConfigHelp:
    """Tests for config command help."""

    def test_config_help(self):
        """Test 'sogon config --help' shows help."""
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "Manage user configuration" in result.stdout

    def test_config_get_help(self):
        """Test 'sogon config get --help' shows help."""
        result = runner.invoke(app, ["config", "get", "--help"])

        assert result.exit_code == 0
        assert "Get a configuration value" in result.stdout

    def test_config_set_help(self):
        """Test 'sogon config set --help' shows help."""
        result = runner.invoke(app, ["config", "set", "--help"])

        assert result.exit_code == 0
        assert "Set a configuration value" in result.stdout
