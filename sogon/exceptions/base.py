"""
Base exception classes for SOGON
"""

from typing import Optional, Dict, Any


class SogonError(Exception):
    """
    Base exception for all SOGON-related errors
    
    Provides consistent error handling with optional error codes,
    context information, and chaining support.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize SogonError
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for programmatic handling
            context: Additional context information
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
        
        # Chain the original exception if provided
        if cause:
            self.__cause__ = cause
    
    def add_context(self, key: str, value: Any) -> 'SogonError':
        """
        Add context information to the error
        
        Args:
            key: Context key
            value: Context value
            
        Returns:
            SogonError: Self for method chaining
        """
        self.context[key] = value
        return self
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get context value
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Any: Context value or default
        """
        return self.context.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for serialization
        
        Returns:
            Dict[str, Any]: Error dictionary
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        """String representation of the error"""
        parts = [self.message]
        
        if self.error_code:
            parts.append(f"(code: {self.error_code})")
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"[{context_str}]")
        
        if self.cause:
            parts.append(f"caused by: {self.cause}")
        
        return " ".join(parts)
    
    def __repr__(self) -> str:
        """Detailed representation of the error"""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"context={self.context}, "
            f"cause={repr(self.cause)}"
            f")"
        )


class SogonConfigurationError(SogonError):
    """
    Configuration-related errors
    
    Raised when there are issues with application configuration,
    missing environment variables, invalid settings, etc.
    """
    
    def __init__(
        self,
        message: str,
        setting_name: Optional[str] = None,
        setting_value: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize configuration error
        
        Args:
            message: Error message
            setting_name: Name of the problematic setting
            setting_value: Value of the problematic setting
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        
        if setting_name:
            self.add_context("setting_name", setting_name)
        if setting_value:
            self.add_context("setting_value", setting_value)


class SogonValidationError(SogonError):
    """
    Input validation errors
    
    Raised when user input or data doesn't meet validation requirements.
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize validation error
        
        Args:
            message: Error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            validation_rule: Description of the validation rule
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        
        if field_name:
            self.add_context("field_name", field_name)
        if field_value is not None:
            self.add_context("field_value", field_value)
        if validation_rule:
            self.add_context("validation_rule", validation_rule)


class SogonRetryableError(SogonError):
    """
    Base class for errors that might succeed if retried
    
    These errors indicate temporary failures that could potentially
    succeed if the operation is attempted again.
    """
    
    def __init__(
        self,
        message: str,
        retry_after_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize retryable error
        
        Args:
            message: Error message
            retry_after_seconds: Suggested delay before retry
            max_retries: Maximum number of retries recommended
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        
        if retry_after_seconds is not None:
            self.add_context("retry_after_seconds", retry_after_seconds)
        if max_retries is not None:
            self.add_context("max_retries", max_retries)
    
    @property
    def is_retryable(self) -> bool:
        """Check if this error is retryable"""
        return True
    
    @property
    def retry_after_seconds(self) -> Optional[float]:
        """Get suggested retry delay"""
        return self.get_context("retry_after_seconds")
    
    @property
    def max_retries(self) -> Optional[int]:
        """Get maximum recommended retries"""
        return self.get_context("max_retries")


class SogonResourceError(SogonError):
    """
    Resource-related errors
    
    Raised when there are issues with system resources like
    disk space, memory, file permissions, etc.
    """
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize resource error
        
        Args:
            message: Error message
            resource_type: Type of resource (file, memory, disk, etc.)
            resource_name: Name or identifier of the resource
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, error_code="RESOURCE_ERROR", **kwargs)
        
        if resource_type:
            self.add_context("resource_type", resource_type)
        if resource_name:
            self.add_context("resource_name", resource_name)


class SogonTimeoutError(SogonRetryableError):
    """
    Timeout-related errors
    
    Raised when operations exceed their time limits.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize timeout error
        
        Args:
            message: Error message
            timeout_seconds: The timeout value that was exceeded
            operation: Description of the operation that timed out
            **kwargs: Additional arguments for base class
        """
        super().__init__(
            message, 
            error_code="TIMEOUT_ERROR",
            retry_after_seconds=timeout_seconds * 2 if timeout_seconds else None,
            **kwargs
        )
        
        if timeout_seconds is not None:
            self.add_context("timeout_seconds", timeout_seconds)
        if operation:
            self.add_context("operation", operation)