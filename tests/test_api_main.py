"""
Tests for API main module
"""

import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock, mock_open
from fastapi.testclient import TestClient
from datetime import datetime
from pathlib import Path
import io

from sogon.api.main import app, HealthResponse, TranscribeRequest, TranscribeResponse, JobStatusResponse, jobs


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


class TestTranscriptionAPI(unittest.TestCase):
    """Test cases for transcription API endpoints"""

    def setUp(self):
        """Set up test client and clear jobs"""
        self.client = TestClient(app)
        jobs.clear()  # Clear jobs between tests

    def tearDown(self):
        """Clean up after tests"""
        jobs.clear()

    def test_transcribe_url_success(self):
        """Test successful URL transcription request"""
        response = self.client.post(
            "/api/v1/transcribe/url",
            json={
                "url": "https://www.youtube.com/watch?v=test",
                "enable_correction": True,
                "use_ai_correction": True,
                "subtitle_format": "txt"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["message"], "Transcription job created successfully")
        
        # Verify job was created (status might change due to background task)
        job_id = data["job_id"]
        self.assertIn(job_id, jobs)
        self.assertEqual(jobs[job_id]["input_type"], "url")
        self.assertIn(jobs[job_id]["status"], ["pending", "processing", "completed", "failed"])

    def test_transcribe_url_with_keep_audio_option(self):
        """Test URL transcription with keep_audio option"""
        response = self.client.post(
            "/api/v1/transcribe/url",
            json={
                "url": "https://www.youtube.com/watch?v=test",
                "enable_correction": True,
                "use_ai_correction": True,
                "subtitle_format": "txt",
                "keep_audio": True
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["message"], "Transcription job created successfully")

    def test_transcribe_url_invalid_url(self):
        """Test URL transcription with invalid URL"""
        response = self.client.post(
            "/api/v1/transcribe/url",
            json={
                "url": "not-a-valid-url",
                "enable_correction": True,
                "use_ai_correction": True,
                "subtitle_format": "txt"
            }
        )

        self.assertEqual(response.status_code, 422)  # Validation error

    @patch('sogon.api.main.config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sogon.api.main.Path')
    def test_transcribe_upload_success(self, mock_path, mock_file, mock_config):
        """Test successful file upload transcription"""
        mock_config.base_output_dir = "/test/output"
        mock_path_instance = MagicMock()
        mock_path_instance.mkdir = MagicMock()
        mock_path.return_value = mock_path_instance
        
        # Create test file content
        test_file_content = b"test audio file content"
        
        response = self.client.post(
            "/api/v1/transcribe/upload",
            files={"file": ("test.mp3", io.BytesIO(test_file_content), "audio/mpeg")},
            data={
                "enable_correction": "true",
                "use_ai_correction": "true",
                "subtitle_format": "txt"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["message"], "File uploaded and transcription job created successfully")

    @patch('sogon.api.main.config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sogon.api.main.Path')
    def test_transcribe_upload_with_keep_audio(self, mock_path, mock_file, mock_config):
        """Test file upload transcription with keep_audio option"""
        mock_config.base_output_dir = "/test/output"
        mock_path_instance = MagicMock()
        mock_path_instance.mkdir = MagicMock()
        mock_path.return_value = mock_path_instance
        
        # Create test file content
        test_file_content = b"test audio file content"
        
        response = self.client.post(
            "/api/v1/transcribe/upload",
            files={"file": ("test.mp3", io.BytesIO(test_file_content), "audio/mpeg")},
            data={
                "enable_correction": "true",
                "use_ai_correction": "true", 
                "subtitle_format": "txt",
                "keep_audio": "true"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["message"], "File uploaded and transcription job created successfully")

    def test_transcribe_upload_no_file(self):
        """Test file upload without file"""
        response = self.client.post(
            "/api/v1/transcribe/upload",
            data={
                "enable_correction": "true",
                "use_ai_correction": "true",
                "subtitle_format": "txt"
            }
        )

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_get_job_status_success(self):
        """Test getting job status for existing job"""
        # Create a test job
        job_id = "test-job-123"
        jobs[job_id] = {
            "status": "processing",
            "progress": 50,
            "input_type": "url",
            "input_value": "https://test.com"
        }

        response = self.client.get(f"/api/v1/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["job_id"], job_id)
        self.assertEqual(data["status"], "processing")
        self.assertEqual(data["progress"], 50)

    def test_get_job_status_not_found(self):
        """Test getting job status for non-existent job"""
        response = self.client.get("/api/v1/jobs/non-existent-job")

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["detail"], "Job not found")

    @patch('sogon.api.main.FileResponse')
    @patch('sogon.api.main.Path')
    def test_download_result_success(self, mock_path, mock_file_response):
        """Test downloading result file for completed job"""
        # Create a completed job
        job_id = "completed-job-123"
        jobs[job_id] = {
            "status": "completed",
            "result": {
                "original_files": ["/path/to/result.txt", "/path/to/metadata.json"],
                "corrected_files": ["/path/to/corrected.txt", "/path/to/corrected_metadata.json"],
                "output_directory": "/output/dir"
            }
        }

        # Mock file existence
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.name = "result.txt"
        mock_path.return_value = mock_path_instance
        
        # Mock FileResponse
        mock_file_response.return_value = MagicMock()

        response = self.client.get(f"/api/v1/jobs/{job_id}/download?file_type=original")

        # The endpoint should call FileResponse
        mock_file_response.assert_called_once()

    def test_download_result_job_not_found(self):
        """Test downloading result for non-existent job"""
        response = self.client.get("/api/v1/jobs/non-existent/download")

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["detail"], "Job not found")

    def test_download_result_job_not_completed(self):
        """Test downloading result for incomplete job"""
        job_id = "processing-job-123"
        jobs[job_id] = {
            "status": "processing",
            "progress": 50
        }

        response = self.client.get(f"/api/v1/jobs/{job_id}/download")

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["detail"], "Job not completed yet")

    def test_delete_job_success(self):
        """Test deleting existing job"""
        job_id = "test-job-to-delete"
        jobs[job_id] = {
            "status": "completed",
            "input_type": "url",
            "input_value": "https://test.com"
        }

        response = self.client.delete(f"/api/v1/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Job deleted successfully")
        
        # Verify job was deleted
        self.assertNotIn(job_id, jobs)

    def test_delete_job_not_found(self):
        """Test deleting non-existent job"""
        response = self.client.delete("/api/v1/jobs/non-existent")

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["detail"], "Job not found")

    @patch('sogon.api.main.Path')
    def test_delete_job_with_file_cleanup(self, mock_path):
        """Test deleting job with uploaded file cleanup"""
        job_id = "test-job-with-file"
        jobs[job_id] = {
            "status": "completed",
            "input_type": "file",
            "input_value": "/uploads/test-file.mp3"
        }

        # Mock file operations
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.unlink = MagicMock()
        mock_path.return_value = mock_path_instance

        response = self.client.delete(f"/api/v1/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        mock_path_instance.unlink.assert_called_once()

    def test_update_job_safely_success(self):
        """Test safe job update when job exists"""
        from sogon.api.main import update_job_safely
        
        # Create a job
        job_id = "test-job-safe-update"
        jobs[job_id] = {
            "status": "pending",
            "progress": 0
        }
        
        # Test successful update
        result = update_job_safely(job_id, {"status": "processing", "progress": 50})
        self.assertTrue(result)
        self.assertEqual(jobs[job_id]["status"], "processing")
        self.assertEqual(jobs[job_id]["progress"], 50)

    def test_update_job_safely_job_not_found(self):
        """Test safe job update when job doesn't exist"""
        from sogon.api.main import update_job_safely
        
        # Test update on non-existent job
        result = update_job_safely("non-existent-job", {"status": "processing"})
        self.assertFalse(result)

    def test_update_job_safely_race_condition(self):
        """Test safe job update during race condition"""
        from sogon.api.main import update_job_safely
        
        # Create a job
        job_id = "test-job-race"
        jobs[job_id] = {
            "status": "pending",
            "progress": 0
        }
        
        # Simulate deletion of job after existence check
        del jobs[job_id]
        
        # This should handle the missing job gracefully
        result = update_job_safely(job_id, {"status": "processing"})
        self.assertFalse(result)


class TestRequestResponseModels(unittest.TestCase):
    """Test cases for request/response models"""

    def test_transcribe_request_model(self):
        """Test TranscribeRequest model validation"""
        valid_data = {
            "url": "https://www.youtube.com/watch?v=test",
            "enable_correction": True,
            "use_ai_correction": False,
            "subtitle_format": "srt"
        }
        
        request = TranscribeRequest(**valid_data)
        self.assertEqual(str(request.url), "https://www.youtube.com/watch?v=test")
        self.assertTrue(request.enable_correction)
        self.assertFalse(request.use_ai_correction)
        self.assertEqual(request.subtitle_format, "srt")

    def test_transcribe_request_defaults(self):
        """Test TranscribeRequest model with default values"""
        minimal_data = {
            "url": "https://example.com/video"
        }
        
        request = TranscribeRequest(**minimal_data)
        self.assertTrue(request.enable_correction)  # Default
        self.assertTrue(request.use_ai_correction)  # Default
        self.assertEqual(request.subtitle_format, "txt")  # Default
        self.assertFalse(request.keep_audio)  # Default

    def test_transcribe_request_with_keep_audio(self):
        """Test TranscribeRequest model with keep_audio option"""
        data = {
            "url": "https://www.youtube.com/watch?v=test",
            "enable_correction": True,
            "use_ai_correction": False,
            "subtitle_format": "srt",
            "keep_audio": True
        }
        
        request = TranscribeRequest(**data)
        self.assertEqual(str(request.url), "https://www.youtube.com/watch?v=test")
        self.assertTrue(request.enable_correction)
        self.assertFalse(request.use_ai_correction)
        self.assertEqual(request.subtitle_format, "srt")
        self.assertTrue(request.keep_audio)

    def test_transcribe_response_model(self):
        """Test TranscribeResponse model"""
        data = {
            "job_id": "test-123",
            "status": "pending",
            "message": "Job created"
        }
        
        response = TranscribeResponse(**data)
        self.assertEqual(response.job_id, "test-123")
        self.assertEqual(response.status, "pending")
        self.assertEqual(response.message, "Job created")

    def test_job_status_response_model(self):
        """Test JobStatusResponse model"""
        data = {
            "job_id": "test-456",
            "status": "completed",
            "progress": 100,
            "result": {"files": ["test.txt"]},
            "error": None
        }
        
        response = JobStatusResponse(**data)
        self.assertEqual(response.job_id, "test-456")
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.progress, 100)
        self.assertEqual(response.result, {"files": ["test.txt"]})
        self.assertIsNone(response.error)


if __name__ == '__main__':
    unittest.main()