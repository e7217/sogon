"""
Contract tests for LocalModelConfiguration Pydantic schema.

Validates that LocalModelConfiguration enforces all validation rules
from the contract specification.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

# Import will be available after Task 7 implementation
# from sogon.models.local_config import LocalModelConfiguration
from tests.fixtures.configs import (
    ALL_VALID_CONFIGS,
    ALL_INVALID_CONFIGS,
    VALID_CONFIG_CPU_BASE,
    VALID_CONFIG_CUDA_MEDIUM,
    create_env_vars_for_config,
)


@pytest.mark.skip("Task 7: LocalModelConfiguration not implemented yet")
class TestLocalModelConfigurationValidation:
    """Test LocalModelConfiguration Pydantic validation rules."""

    @pytest.mark.parametrize("config_dict", ALL_VALID_CONFIGS)
    def test_valid_configs(self, config_dict):
        """All valid model/device/compute_type combinations should pass validation."""
        # from sogon.models.local_config import LocalModelConfiguration
        #
        # # Should not raise ValidationError
        # config = LocalModelConfiguration(**config_dict)
        #
        # # Verify all fields set correctly
        # assert config.model_name == config_dict["model_name"]
        # assert config.device == config_dict["device"]
        # assert config.compute_type == config_dict["compute_type"]
        pass

    def test_invalid_model_name(self):
        """Invalid model_name should raise ValueError with clear message."""
        # from sogon.models.local_config import LocalModelConfiguration
        #
        # invalid_config = {
        #     **VALID_CONFIG_CPU_BASE,
        #     "model_name": "invalid-model"
        # }
        #
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**invalid_config)
        #
        # error_msg = str(exc_info.value)
        # assert "Invalid model_name" in error_msg
        # assert "invalid-model" in error_msg
        # # Should list valid models
        # assert "tiny" in error_msg or "base" in error_msg
        pass

    def test_invalid_device(self):
        """Invalid device should raise ValueError with valid devices list."""
        # from sogon.models.local_config import LocalModelConfiguration
        #
        # invalid_config = {
        #     **VALID_CONFIG_CPU_BASE,
        #     "device": "tpu"
        # }
        #
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**invalid_config)
        #
        # error_msg = str(exc_info.value)
        # assert "Invalid device" in error_msg or "tpu" in error_msg
        # # Should list valid devices
        # assert "cpu" in error_msg or "cuda" in error_msg
        pass

    @pytest.mark.parametrize("invalid_config,expected_error", [
        ("INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_CPU_FLOAT16", "Invalid compute_type"),
        ("INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_MPS_INT8", "Invalid compute_type"),
    ])
    def test_compute_type_device_mismatch(self, invalid_config, expected_error):
        """
        Compute type must match device capabilities.

        - CPU: int8, int16 only
        - CUDA: int8, float16, float32
        - MPS: float16, float32
        """
        # from sogon.models.local_config import LocalModelConfiguration
        # from tests.fixtures.configs import (
        #     INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_CPU_FLOAT16,
        #     INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_MPS_INT8,
        # )
        #
        # config_map = {
        #     "INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_CPU_FLOAT16": INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_CPU_FLOAT16,
        #     "INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_MPS_INT8": INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_MPS_INT8,
        # }
        #
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**config_map[invalid_config])
        #
        # error_msg = str(exc_info.value)
        # assert expected_error in error_msg
        # # Should explain device-compute_type compatibility
        # assert "device" in error_msg.lower()
        pass

    def test_resource_estimates(self):
        """
        Verify resource estimation methods return correct values.

        - get_model_size_estimate_gb() matches documented model sizes
        - get_min_ram_gb() meets minimum requirements
        - get_min_vram_gb() returns 0 for CPU, >0 for GPU
        """
        # from sogon.models.local_config import LocalModelConfiguration
        #
        # # Test tiny model size
        # config_tiny = LocalModelConfiguration(**{
        #     **VALID_CONFIG_CPU_BASE,
        #     "model_name": "tiny"
        # })
        # assert config_tiny.get_model_size_estimate_gb() == 0.075  # 75MB
        # assert config_tiny.get_min_ram_gb() == 1.0
        # assert config_tiny.get_min_vram_gb() == 0.0  # CPU device
        #
        # # Test large-v3 model size
        # config_large = LocalModelConfiguration(**{
        #     **VALID_CONFIG_CUDA_MEDIUM,
        #     "model_name": "large-v3"
        # })
        # assert config_large.get_model_size_estimate_gb() == 2.9  # 2.9GB
        # assert config_large.get_min_ram_gb() == 8.0
        # assert config_large.get_min_vram_gb() == 8.0  # GPU device
        #
        # # Test medium model
        # config_medium = LocalModelConfiguration(**VALID_CONFIG_CUDA_MEDIUM)
        # assert config_medium.get_model_size_estimate_gb() == 1.5  # 1.5GB
        # assert config_medium.get_min_ram_gb() == 4.0
        # assert config_medium.get_min_vram_gb() == 4.0
        pass

    def test_environment_variable_parsing(self):
        """Verify config can be created from environment variables."""
        # from sogon.models.local_config import LocalModelConfiguration
        # import os
        #
        # # Set environment variables
        # env_vars = create_env_vars_for_config(VALID_CONFIG_CPU_BASE)
        #
        # with patch.dict(os.environ, env_vars):
        #     # Parse config from environment
        #     # (This would require an additional factory method)
        #     # config = LocalModelConfiguration.from_env()
        #
        #     # For now, manually parse
        #     config = LocalModelConfiguration(
        #         model_name=os.getenv("SOGON_LOCAL_MODEL_NAME", "base"),
        #         device=os.getenv("SOGON_LOCAL_DEVICE", "cpu"),
        #         compute_type=os.getenv("SOGON_LOCAL_COMPUTE_TYPE", "int8"),
        #     )
        #
        #     assert config.model_name == VALID_CONFIG_CPU_BASE["model_name"]
        #     assert config.device == VALID_CONFIG_CPU_BASE["device"]
        #     assert config.compute_type == VALID_CONFIG_CPU_BASE["compute_type"]
        pass

    def test_cli_flag_parsing(self):
        """Verify config can be created from CLI arguments."""
        # from sogon.models.local_config import LocalModelConfiguration
        #
        # # Simulate CLI args
        # cli_args = {
        #     "local_model": "large",
        #     "device": "cuda",
        #     "compute_type": "float16",
        #     "beam_size": 10,
        # }
        #
        # # Create config from CLI args
        # config = LocalModelConfiguration(
        #     model_name=cli_args["local_model"],
        #     device=cli_args["device"],
        #     compute_type=cli_args["compute_type"],
        #     beam_size=cli_args["beam_size"],
        # )
        #
        # assert config.model_name == "large"
        # assert config.device == "cuda"
        # assert config.compute_type == "float16"
        # assert config.beam_size == 10
        pass


@pytest.mark.skip("Task 7: LocalModelConfiguration not implemented yet")
class TestLocalModelConfigurationValidationErrors:
    """Test validation error messages are actionable (FR-025)."""

    @pytest.mark.parametrize("invalid_config,expected_fragment", ALL_INVALID_CONFIGS)
    def test_invalid_configs_raise_with_helpful_messages(self, invalid_config, expected_fragment):
        """
        All invalid configs should raise ValidationError with actionable messages.

        Error messages must include:
        - What's wrong (e.g., "Invalid model_name 'xyz'")
        - What's acceptable (e.g., "Must be one of: tiny, base, small...")
        """
        # from sogon.models.local_config import LocalModelConfiguration
        #
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**invalid_config)
        #
        # error_msg = str(exc_info.value)
        # assert expected_fragment in error_msg
        pass

    def test_beam_size_validation(self):
        """Beam size must be between 1 and 10."""
        # from sogon.models.local_config import LocalModelConfiguration
        # from tests.fixtures.configs import (
        #     INVALID_CONFIG_BEAM_SIZE_TOO_LOW,
        #     INVALID_CONFIG_BEAM_SIZE_TOO_HIGH,
        # )
        #
        # # Test too low
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**INVALID_CONFIG_BEAM_SIZE_TOO_LOW)
        # assert "greater than or equal to 1" in str(exc_info.value)
        #
        # # Test too high
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**INVALID_CONFIG_BEAM_SIZE_TOO_HIGH)
        # assert "less than or equal to 10" in str(exc_info.value)
        pass

    def test_temperature_validation(self):
        """Temperature must be between 0.0 and 1.0."""
        # from sogon.models.local_config import LocalModelConfiguration
        # from tests.fixtures.configs import (
        #     INVALID_CONFIG_TEMPERATURE_TOO_LOW,
        #     INVALID_CONFIG_TEMPERATURE_TOO_HIGH,
        # )
        #
        # # Test too low
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**INVALID_CONFIG_TEMPERATURE_TOO_LOW)
        # assert "greater than or equal to 0" in str(exc_info.value)
        #
        # # Test too high
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**INVALID_CONFIG_TEMPERATURE_TOO_HIGH)
        # assert "less than or equal to 1" in str(exc_info.value)
        pass

    def test_language_code_validation(self):
        """Language code must be 2 characters (ISO 639-1)."""
        # from sogon.models.local_config import LocalModelConfiguration
        # from tests.fixtures.configs import INVALID_CONFIG_LANGUAGE_WRONG_LENGTH
        #
        # with pytest.raises(ValidationError) as exc_info:
        #     LocalModelConfiguration(**INVALID_CONFIG_LANGUAGE_WRONG_LENGTH)
        #
        # error_msg = str(exc_info.value)
        # assert "2 characters" in error_msg
        # assert "ISO 639-1" in error_msg or "iso" in error_msg.lower()
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
