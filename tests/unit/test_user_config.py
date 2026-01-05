"""
Tests for UserConfigManager - user configuration management with YAML persistence.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import shutil

from sogon.config.user_config import (
    UserConfigManager,
    CONFIGURABLE_KEYS,
    get_user_config_manager,
    reload_user_config,
)


class TestUserConfigManager:
    """Tests for UserConfigManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_config_dir):
        """Create a UserConfigManager with temporary directory."""
        return UserConfigManager(config_dir=temp_config_dir)

    def test_init_creates_empty_config(self, manager):
        """Test that a new manager starts with empty config."""
        assert manager.get_all() == {}

    def test_set_and_get_string_value(self, manager):
        """Test setting and getting a string value."""
        manager.set("output_base_dir", "/custom/path")
        assert manager.get("output_base_dir") == "/custom/path"

    def test_set_and_get_bool_value(self, manager):
        """Test setting and getting a boolean value."""
        manager.set("keep_temp_files", True)
        assert manager.get("keep_temp_files") is True

        manager.set("keep_temp_files", False)
        assert manager.get("keep_temp_files") is False

    def test_set_bool_from_string(self, manager):
        """Test setting boolean from string representations."""
        manager.set("keep_temp_files", "true")
        assert manager.get("keep_temp_files") is True

        manager.set("keep_temp_files", "false")
        assert manager.get("keep_temp_files") is False

        manager.set("keep_temp_files", "yes")
        assert manager.get("keep_temp_files") is True

        manager.set("keep_temp_files", "no")
        assert manager.get("keep_temp_files") is False

    def test_set_and_get_int_value(self, manager):
        """Test setting and getting an integer value."""
        manager.set("max_workers", 8)
        assert manager.get("max_workers") == 8

    def test_set_int_from_string(self, manager):
        """Test setting integer from string."""
        manager.set("max_workers", "6")
        assert manager.get("max_workers") == 6

    def test_get_unknown_key_raises_error(self, manager):
        """Test that getting unknown key raises KeyError."""
        with pytest.raises(KeyError, match="Unknown configuration key"):
            manager.get("unknown_key")

    def test_set_unknown_key_raises_error(self, manager):
        """Test that setting unknown key raises KeyError."""
        with pytest.raises(KeyError, match="Unknown configuration key"):
            manager.set("unknown_key", "value")

    def test_set_invalid_choice_raises_error(self, manager):
        """Test that setting invalid choice raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value"):
            manager.set("transcription_provider", "invalid_provider")

    def test_set_choice_case_insensitive(self, manager):
        """Test that choices are case-insensitive for strings."""
        manager.set("log_level", "debug")
        assert manager.get("log_level") == "DEBUG"

        manager.set("transcription_provider", "GROQ")
        assert manager.get("transcription_provider") == "groq"

    def test_set_int_below_min_raises_error(self, manager):
        """Test that setting int below minimum raises ValueError."""
        with pytest.raises(ValueError, match="must be >="):
            manager.set("max_workers", 0)

    def test_set_int_above_max_raises_error(self, manager):
        """Test that setting int above maximum raises ValueError."""
        with pytest.raises(ValueError, match="must be <="):
            manager.set("max_workers", 100)

    def test_reset_specific_key(self, manager):
        """Test resetting a specific key."""
        manager.set("output_base_dir", "/custom/path")
        assert manager.get("output_base_dir") == "/custom/path"

        manager.reset("output_base_dir")
        assert manager.get("output_base_dir") is None  # None means use default

    def test_reset_all(self, manager):
        """Test resetting all configuration."""
        manager.set("output_base_dir", "/custom/path")
        manager.set("log_level", "DEBUG")

        manager.reset()
        assert manager.get_all() == {}

    def test_reset_unknown_key_raises_error(self, manager):
        """Test that resetting unknown key raises KeyError."""
        with pytest.raises(KeyError, match="Unknown configuration key"):
            manager.reset("unknown_key")

    def test_get_all(self, manager):
        """Test getting all configured values."""
        manager.set("output_base_dir", "/path1")
        manager.set("log_level", "DEBUG")

        all_config = manager.get_all()
        assert all_config == {
            "output_base_dir": "/path1",
            "log_level": "DEBUG",
        }

    def test_get_effective_value_returns_user_config(self, manager):
        """Test get_effective_value returns user config when set."""
        manager.set("output_base_dir", "/custom")
        assert manager.get_effective_value("output_base_dir") == "/custom"

    def test_get_effective_value_returns_default_when_not_set(self, manager):
        """Test get_effective_value returns default when not set."""
        # output_base_dir default is "./result"
        assert manager.get_effective_value("output_base_dir") == "./result"

    def test_list_keys(self):
        """Test list_keys returns all configurable keys."""
        keys = UserConfigManager.list_keys()
        assert "output_base_dir" in keys
        assert "transcription_provider" in keys
        assert "log_level" in keys

    def test_persistence(self, temp_config_dir):
        """Test that config persists across manager instances."""
        # Create first manager and set values
        manager1 = UserConfigManager(config_dir=temp_config_dir)
        manager1.set("output_base_dir", "/persistent/path")
        manager1.set("log_level", "DEBUG")

        # Create second manager (should load from file)
        manager2 = UserConfigManager(config_dir=temp_config_dir)
        assert manager2.get("output_base_dir") == "/persistent/path"
        assert manager2.get("log_level") == "DEBUG"

    def test_config_file_created_on_set(self, manager, temp_config_dir):
        """Test that config file is created on first set."""
        config_path = temp_config_dir / "config.yaml"
        assert not config_path.exists()

        manager.set("log_level", "DEBUG")
        assert config_path.exists()

    def test_config_dir_created_if_not_exists(self, temp_config_dir):
        """Test that config directory is created if it doesn't exist."""
        nested_dir = temp_config_dir / "nested" / "config"
        manager = UserConfigManager(config_dir=nested_dir)
        manager.set("log_level", "DEBUG")

        assert nested_dir.exists()
        assert (nested_dir / "config.yaml").exists()


class TestConfigurableKeys:
    """Tests for CONFIGURABLE_KEYS definition."""

    def test_all_keys_have_required_fields(self):
        """Test that all configurable keys have required fields."""
        for key, info in CONFIGURABLE_KEYS.items():
            assert "description" in info, f"{key} missing description"
            assert "default" in info, f"{key} missing default"
            assert "type" in info, f"{key} missing type"

    def test_all_defaults_match_type(self):
        """Test that all defaults match their declared type."""
        for key, info in CONFIGURABLE_KEYS.items():
            default = info["default"]
            expected_type = info["type"]
            assert isinstance(default, expected_type), (
                f"{key} default {default} is not {expected_type.__name__}"
            )

    def test_choices_match_type(self):
        """Test that all choices match their declared type."""
        for key, info in CONFIGURABLE_KEYS.items():
            if "choices" in info:
                expected_type = info["type"]
                for choice in info["choices"]:
                    assert isinstance(choice, expected_type), (
                        f"{key} choice {choice} is not {expected_type.__name__}"
                    )

    def test_min_max_only_for_numeric(self):
        """Test that min/max are only defined for numeric types."""
        for key, info in CONFIGURABLE_KEYS.items():
            if "min" in info or "max" in info:
                assert info["type"] in (int, float), (
                    f"{key} has min/max but is not numeric type"
                )


class TestSingletonFunctions:
    """Tests for singleton accessor functions."""

    def test_get_user_config_manager_returns_same_instance(self):
        """Test that get_user_config_manager returns singleton."""
        # Note: This test modifies global state
        with patch.object(UserConfigManager, '__init__', return_value=None):
            manager1 = get_user_config_manager()
            manager2 = get_user_config_manager()
            assert manager1 is manager2

    def test_reload_user_config_creates_new_instance(self):
        """Test that reload_user_config creates new instance."""
        with patch.object(UserConfigManager, '__init__', return_value=None):
            manager1 = get_user_config_manager()
            manager2 = reload_user_config()
            # After reload, should be different instance
            assert manager1 is not manager2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_load_corrupted_yaml(self, temp_config_dir):
        """Test loading corrupted YAML file."""
        config_path = temp_config_dir / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("invalid: yaml: content: [")

        manager = UserConfigManager(config_dir=temp_config_dir)
        assert manager.get_all() == {}

    def test_load_empty_yaml(self, temp_config_dir):
        """Test loading empty YAML file."""
        config_path = temp_config_dir / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("")

        manager = UserConfigManager(config_dir=temp_config_dir)
        assert manager.get_all() == {}

    def test_invalid_bool_string_raises_error(self, temp_config_dir):
        """Test that invalid boolean string raises ValueError."""
        manager = UserConfigManager(config_dir=temp_config_dir)
        with pytest.raises(ValueError, match="Invalid boolean value"):
            manager.set("keep_temp_files", "invalid")

    def test_invalid_int_string_raises_error(self, temp_config_dir):
        """Test that invalid integer string raises ValueError."""
        manager = UserConfigManager(config_dir=temp_config_dir)
        with pytest.raises(ValueError, match="Cannot convert"):
            manager.set("max_workers", "not_a_number")
