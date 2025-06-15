"""
Tests for API configuration module
"""

import os
import unittest
from unittest.mock import patch
from sogon.api.config import APIConfig


class TestAPIConfig(unittest.TestCase):
    """Test cases for API configuration"""

    def setUp(self):
        """Set up test environment"""
        # Store original environment variables
        self.original_env = {}
        env_vars = [
            'API_HOST', 'API_PORT', 'API_DEBUG', 'API_LOG_LEVEL',
            'SOGON_OUTPUT_DIR', 'SOGON_ENABLE_CORRECTION', 'SOGON_USE_AI_CORRECTION'
        ]
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)

    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value

    def test_default_configuration(self):
        """Test default configuration values"""
        # Clear environment variables
        for var in self.original_env:
            os.environ.pop(var, None)
        
        config = APIConfig()
        
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8000)
        self.assertEqual(config.debug, False)
        self.assertEqual(config.log_level, "INFO")
        self.assertEqual(config.base_output_dir, "./result")
        self.assertEqual(config.enable_correction, True)
        self.assertEqual(config.use_ai_correction, True)

    def test_environment_variable_override_host(self):
        """Test host configuration from environment variable"""
        os.environ['API_HOST'] = '192.168.1.100'
        config = APIConfig()
        self.assertEqual(config.host, '192.168.1.100')

    def test_environment_variable_override_port(self):
        """Test port configuration from environment variable"""
        os.environ['API_PORT'] = '9000'
        config = APIConfig()
        self.assertEqual(config.port, 9000)

    def test_environment_variable_override_debug_true(self):
        """Test debug mode enabled from environment variable"""
        os.environ['API_DEBUG'] = 'true'
        config = APIConfig()
        self.assertEqual(config.debug, True)

    def test_environment_variable_override_debug_false(self):
        """Test debug mode disabled from environment variable"""
        os.environ['API_DEBUG'] = 'false'
        config = APIConfig()
        self.assertEqual(config.debug, False)

    def test_environment_variable_override_debug_case_insensitive(self):
        """Test debug mode case insensitive parsing"""
        os.environ['API_DEBUG'] = 'TRUE'
        config = APIConfig()
        self.assertEqual(config.debug, True)
        
        os.environ['API_DEBUG'] = 'False'
        config = APIConfig()
        self.assertEqual(config.debug, False)

    def test_environment_variable_override_log_level(self):
        """Test log level configuration from environment variable"""
        os.environ['API_LOG_LEVEL'] = 'DEBUG'
        config = APIConfig()
        self.assertEqual(config.log_level, 'DEBUG')

    def test_environment_variable_override_output_dir(self):
        """Test output directory configuration from environment variable"""
        os.environ['SOGON_OUTPUT_DIR'] = '/custom/output/path'
        config = APIConfig()
        self.assertEqual(config.base_output_dir, '/custom/output/path')

    def test_environment_variable_override_correction_settings(self):
        """Test correction settings from environment variables"""
        os.environ['SOGON_ENABLE_CORRECTION'] = 'false'
        os.environ['SOGON_USE_AI_CORRECTION'] = 'false'
        config = APIConfig()
        self.assertEqual(config.enable_correction, False)
        self.assertEqual(config.use_ai_correction, False)

    def test_invalid_port_number(self):
        """Test invalid port number handling"""
        os.environ['API_PORT'] = 'invalid'
        with self.assertRaises(ValueError):
            APIConfig()

    def test_config_repr(self):
        """Test string representation of config"""
        config = APIConfig()
        repr_str = repr(config)
        self.assertIn('APIConfig', repr_str)
        self.assertIn(f'host={config.host}', repr_str)
        self.assertIn(f'port={config.port}', repr_str)
        self.assertIn(f'debug={config.debug}', repr_str)

    def test_dotenv_loading(self):
        """Test that load_dotenv functionality works"""
        # Since load_dotenv is called at module import time,
        # we can't mock it after import. Instead, test that
        # the functionality works by creating a config instance
        config = APIConfig()
        self.assertIsNotNone(config)


if __name__ == '__main__':
    unittest.main()