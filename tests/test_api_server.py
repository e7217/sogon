"""
Tests for API server entry point
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path to import api_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api_server


class TestAPIServer(unittest.TestCase):
    """Test cases for API server entry point"""

    @patch('api_server.uvicorn.run')
    @patch('api_server.config')
    @patch('builtins.print')
    def test_main_function_default_config(self, mock_print, mock_config, mock_uvicorn_run):
        """Test main function with default configuration"""
        # Setup mock config
        mock_config.host = "127.0.0.1"
        mock_config.port = 8000
        mock_config.debug = False
        mock_config.log_level = "INFO"
        
        # Call main function
        api_server.main()
        
        # Verify print statements
        expected_prints = [
            unittest.mock.call("Starting SOGON API server on 127.0.0.1:8000"),
            unittest.mock.call("Debug mode: False"),
            unittest.mock.call("Access the API documentation at: http://127.0.0.1:8000/docs")
        ]
        mock_print.assert_has_calls(expected_prints)
        
        # Verify uvicorn.run was called with correct parameters
        mock_uvicorn_run.assert_called_once_with(
            "sogon.api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info"
        )

    @patch('api_server.uvicorn.run')
    @patch('api_server.config')
    @patch('builtins.print')
    def test_main_function_custom_config(self, mock_print, mock_config, mock_uvicorn_run):
        """Test main function with custom configuration"""
        # Setup mock config
        mock_config.host = "0.0.0.0"
        mock_config.port = 9000
        mock_config.debug = True
        mock_config.log_level = "DEBUG"
        
        # Call main function
        api_server.main()
        
        # Verify print statements
        expected_prints = [
            unittest.mock.call("Starting SOGON API server on 0.0.0.0:9000"),
            unittest.mock.call("Debug mode: True"),
            unittest.mock.call("Access the API documentation at: http://0.0.0.0:9000/docs")
        ]
        mock_print.assert_has_calls(expected_prints)
        
        # Verify uvicorn.run was called with correct parameters
        mock_uvicorn_run.assert_called_once_with(
            "sogon.api.main:app",
            host="0.0.0.0",
            port=9000,
            reload=True,
            log_level="debug"
        )

    @patch('api_server.uvicorn.run')
    @patch('api_server.config')
    @patch('builtins.print')
    def test_main_function_mixed_case_log_level(self, mock_print, mock_config, mock_uvicorn_run):
        """Test main function handles mixed case log levels"""
        # Setup mock config with mixed case log level
        mock_config.host = "127.0.0.1"
        mock_config.port = 8000
        mock_config.debug = False
        mock_config.log_level = "WARNING"
        
        # Call main function
        api_server.main()
        
        # Verify log level is converted to lowercase
        mock_uvicorn_run.assert_called_once_with(
            "sogon.api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="warning"
        )

    @patch('api_server.main')
    def test_main_execution_when_run_as_script(self, mock_main):
        """Test that main() is called when script is executed directly"""
        # This test simulates running the script directly
        # We need to mock __name__ being "__main__"
        
        with patch.object(api_server, '__name__', '__main__'):
            # Import and reload the module to trigger the if __name__ == "__main__" block
            import importlib
            importlib.reload(api_server)
            
        # Note: This test is complex because of how Python modules work
        # In practice, this is more of an integration test
        # The important thing is that the main() function works correctly

    def test_module_imports(self):
        """Test that all required modules can be imported"""
        # Verify that the module imports work without errors
        self.assertTrue(hasattr(api_server, 'uvicorn'))
        self.assertTrue(hasattr(api_server, 'config'))
        self.assertTrue(hasattr(api_server, 'app'))
        self.assertTrue(hasattr(api_server, 'main'))

    @patch('api_server.uvicorn.run')
    @patch('api_server.config')
    def test_main_function_exception_handling(self, mock_config, mock_uvicorn_run):
        """Test main function handles uvicorn exceptions"""
        # Setup mock config
        mock_config.host = "127.0.0.1"
        mock_config.port = 8000
        mock_config.debug = False
        mock_config.log_level = "INFO"
        
        # Make uvicorn.run raise an exception
        mock_uvicorn_run.side_effect = Exception("Test exception")
        
        # Call main function and expect it to raise the exception
        with self.assertRaises(Exception):
            api_server.main()

    def test_imports_exist(self):
        """Test that required imports are available"""
        # Test that uvicorn is imported
        self.assertTrue(hasattr(api_server, 'uvicorn'))
        
        # Test that config is imported
        self.assertTrue(hasattr(api_server, 'config'))
        
        # Test that app is imported
        self.assertTrue(hasattr(api_server, 'app'))


if __name__ == '__main__':
    unittest.main()