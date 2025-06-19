"""
Job processing related exceptions
"""

from typing import Optional

from .base import SogonError, SogonTimeoutError, SogonValidationError


class JobError(SogonError):
    """Base exception for job-related errors"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        job_status: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="JOB_ERROR", **kwargs)
        if job_id:
            self.add_context("job_id", job_id)
        if job_status:
            self.add_context("job_status", job_status)


class JobNotFoundError(JobError):
    """Error when job cannot be found"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_NOT_FOUND",
            **kwargs
        )


class JobCancelledError(JobError):
    """Error when job has been cancelled"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        cancelled_at: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_CANCELLED",
            **kwargs
        )
        if cancelled_at:
            self.add_context("cancelled_at", cancelled_at)


class JobTimeoutError(JobError, SogonTimeoutError):
    """Error when job processing times out"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_TIMEOUT",
            operation="job_processing",
            **kwargs
        )


class JobValidationError(JobError, SogonValidationError):
    """Error when job configuration or input is invalid"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        validation_field: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_VALIDATION_ERROR",
            field_name=validation_field,
            **kwargs
        )


class JobAlreadyExistsError(JobError):
    """Error when trying to create a job that already exists"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        existing_job_status: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_ALREADY_EXISTS",
            **kwargs
        )
        if existing_job_status:
            self.add_context("existing_job_status", existing_job_status)


class JobStateError(JobError):
    """Error when job is in an invalid state for the requested operation"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        current_state: Optional[str] = None,
        required_state: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_STATE_ERROR",
            **kwargs
        )
        if current_state:
            self.add_context("current_state", current_state)
        if required_state:
            self.add_context("required_state", required_state)
        if operation:
            self.add_context("operation", operation)


class JobResourceError(JobError):
    """Error when job encounters resource limitations"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_limit: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_RESOURCE_ERROR",
            **kwargs
        )
        if resource_type:
            self.add_context("resource_type", resource_type)
        if resource_limit:
            self.add_context("resource_limit", resource_limit)


class JobConcurrencyError(JobError):
    """Error when job concurrency limits are exceeded"""
    
    def __init__(
        self,
        message: str,
        max_concurrent_jobs: Optional[int] = None,
        current_job_count: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, error_code="JOB_CONCURRENCY_ERROR", **kwargs)
        if max_concurrent_jobs is not None:
            self.add_context("max_concurrent_jobs", max_concurrent_jobs)
        if current_job_count is not None:
            self.add_context("current_job_count", current_job_count)


class JobPersistenceError(JobError):
    """Error when job data cannot be saved or loaded"""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        operation: Optional[str] = None,
        storage_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            job_id=job_id,
            error_code="JOB_PERSISTENCE_ERROR",
            **kwargs
        )
        if operation:
            self.add_context("operation", operation)
        if storage_type:
            self.add_context("storage_type", storage_type)