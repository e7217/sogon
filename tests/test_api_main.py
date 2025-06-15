"""
Tests for API main module
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from sogon.api.main import app, HealthResponse


class TestAPIMain(unittest.TestCase):
    """Test cases for API main functionality"""

    def setUp(self):
        """Set up test client"""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test root endpoint returns correct response"""
        response = self.client.get("/")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "SOGON API Server")
        self.assertEqual(data["docs"], "/docs")

    def test_health_endpoint_success(self):
        """Test health endpoint returns healthy status"""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
        self.assertIn("config", data)
        
        # Check values
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        
        # Validate timestamp format
        datetime.fromisoformat(data["timestamp"])
        
        # Check config structure
        config = data["config"]
        expected_config_keys = [
            "host", "port", "debug", "base_output_dir",
            "enable_correction", "use_ai_correction"
        ]
        for key in expected_config_keys:
            self.assertIn(key, config)

    @patch('sogon.api.main.config')
    def test_health_endpoint_with_custom_config(self, mock_config):
        """Test health endpoint with custom configuration values"""
        # Setup mock config
        mock_config.host = "192.168.1.100"
        mock_config.port = 9000
        mock_config.debug = True
        mock_config.base_output_dir = "/custom/output"
        mock_config.enable_correction = False
        mock_config.use_ai_correction = False
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        config = data["config"]
        self.assertEqual(config["host"], "192.168.1.100")
        self.assertEqual(config["port"], 9000)
        self.assertEqual(config["debug"], True)
        self.assertEqual(config["base_output_dir"], "/custom/output")
        self.assertEqual(config["enable_correction"], False)
        self.assertEqual(config["use_ai_correction"], False)

    @patch('sogon.api.main.datetime')
    def test_health_endpoint_exception_handling(self, mock_datetime):
        """Test health endpoint handles exceptions properly"""
        # Make datetime.now() raise an exception
        mock_datetime.now.side_effect = Exception("Test exception")
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data["detail"], "Health check failed")

    def test_health_response_model(self):
        """Test HealthResponse model validation"""
        # Test valid data
        valid_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "config": {"test": "value"}
        }
        
        health_response = HealthResponse(**valid_data)
        self.assertEqual(health_response.status, "healthy")
        self.assertEqual(health_response.version, "1.0.0")
        self.assertIsInstance(health_response.config, dict)

    def test_app_metadata(self):
        """Test FastAPI app metadata"""
        self.assertEqual(app.title, "SOGON API")
        self.assertIn("Subtitle generator API", app.description)
        self.assertEqual(app.version, "1.0.0")

    @patch('sogon.api.main.logger')
    def test_health_endpoint_logging(self, mock_logger):
        """Test that health endpoint logs correctly"""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        mock_logger.info.assert_called_with("Health check requested")

    @patch('sogon.api.main.logger')
    @patch('sogon.api.main.datetime')
    def test_health_endpoint_error_logging(self, mock_datetime, mock_logger):
        """Test that health endpoint logs errors correctly"""
        mock_datetime.now.side_effect = Exception("Test exception")
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 500)
        mock_logger.error.assert_called()

    def test_openapi_docs_accessible(self):
        """Test that OpenAPI documentation is accessible"""
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)

    def test_openapi_json_accessible(self):
        """Test that OpenAPI JSON schema is accessible"""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        
        # Verify it's valid JSON
        data = response.json()
        self.assertIn("openapi", data)
        self.assertIn("info", data)
        self.assertEqual(data["info"]["title"], "SOGON API")

    def test_general_exception_handler(self):
        """Test general exception handler"""
        # This is tricky to test directly, but we can verify the handler exists
        # by checking app exception handlers
        self.assertIn(Exception, app.exception_handlers)


if __name__ == '__main__':
    unittest.main()