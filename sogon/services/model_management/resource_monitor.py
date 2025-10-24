"""
ResourceMonitor: RAM/VRAM monitoring and threshold enforcement.

Monitors system resources and validates model loading requirements.
"""

import logging
from typing import Dict, Any

import psutil
import torch

from sogon.exceptions import ResourceExhaustedError

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    Monitors and validates system resource usage.

    Responsibilities:
    - Monitor RAM and VRAM usage
    - Enforce resource thresholds (FR-021: 90% limit)
    - Validate resources before model loading
    - Provide resource metrics and reporting

    Attributes:
        ram_threshold_percent: Maximum RAM usage percentage (default 90%)
        vram_threshold_percent: Maximum VRAM usage percentage (default 90%)
    """

    def __init__(
        self,
        ram_threshold_percent: float = 90.0,
        vram_threshold_percent: float = 90.0,
    ):
        """
        Initialize ResourceMonitor.

        Args:
            ram_threshold_percent: Max RAM usage % before error (FR-021)
            vram_threshold_percent: Max VRAM usage % before error (FR-021)
        """
        self.ram_threshold_percent = ram_threshold_percent
        self.vram_threshold_percent = vram_threshold_percent

    def get_system_ram_usage(self) -> Dict[str, float]:
        """
        Get current system RAM usage.

        Returns:
            Dictionary with RAM metrics:
            - total_gb: Total RAM in GB
            - used_gb: Used RAM in GB
            - available_gb: Available RAM in GB
            - percent: Usage percentage
        """
        memory = psutil.virtual_memory()

        return {
            "total_gb": memory.total / (1024**3),
            "used_gb": memory.used / (1024**3),
            "available_gb": memory.available / (1024**3),
            "percent": memory.percent,
        }

    def get_vram_usage(self, device: str) -> Dict[str, float]:
        """
        Get VRAM usage for GPU device.

        Args:
            device: Device name (cuda/mps/cpu)

        Returns:
            Dictionary with VRAM metrics (0 for CPU)
        """
        if device == "cpu":
            # CPU has no dedicated VRAM
            return {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "available_gb": 0.0,
                "percent": 0.0,
            }

        elif device == "cuda" and torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            total = props.total_memory
            allocated = torch.cuda.memory_allocated(0)
            used = allocated
            available = total - used
            percent = (used / total * 100) if total > 0 else 0.0

            return {
                "total_gb": total / (1024**3),
                "used_gb": used / (1024**3),
                "available_gb": available / (1024**3),
                "percent": percent,
            }

        elif device == "mps":
            # MPS uses unified memory (shared with system RAM)
            # Return system memory stats as approximation
            memory = psutil.virtual_memory()
            return {
                "total_gb": memory.total / (1024**3),
                "used_gb": memory.used / (1024**3),
                "available_gb": memory.available / (1024**3),
                "percent": memory.percent,
                "unified_memory": True,
            }

        else:
            return {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "available_gb": 0.0,
                "percent": 0.0,
            }

    def check_ram_threshold(self) -> None:
        """
        Check if RAM usage exceeds threshold.

        Raises:
            ResourceExhaustedError: When RAM usage >= threshold (FR-021)
        """
        ram_info = self.get_system_ram_usage()
        current_percent = ram_info["percent"]

        if current_percent >= self.ram_threshold_percent:
            raise ResourceExhaustedError(
                resource_type="RAM",
                required=self.ram_threshold_percent,
                available=current_percent,
                unit="%",
                suggestion="Close other applications or increase RAM threshold."
            )

        logger.debug(f"RAM usage OK: {current_percent:.1f}% of threshold")

    def check_vram_threshold(self, device: str) -> None:
        """
        Check if VRAM usage exceeds threshold.

        Args:
            device: Device to check (cuda/mps/cpu)

        Raises:
            ResourceExhaustedError: When VRAM usage >= threshold (FR-021)
        """
        if device == "cpu":
            return  # No VRAM to check

        vram_info = self.get_vram_usage(device)
        current_percent = vram_info["percent"]

        if current_percent >= self.vram_threshold_percent:
            raise ResourceExhaustedError(
                resource_type="VRAM",
                required=self.vram_threshold_percent,
                available=current_percent,
                unit="%",
                suggestion="Close GPU applications or use CPU device."
            )

        logger.debug(f"VRAM usage OK: {current_percent:.1f}% of threshold")

    def validate_resources_for_model(
        self,
        model_name: str,
        device: str,
        required_ram_gb: float,
        required_vram_gb: float,
    ) -> None:
        """
        Validate sufficient resources available for model.

        Args:
            model_name: Model name (for error messages)
            device: Target device
            required_ram_gb: Required RAM in GB
            required_vram_gb: Required VRAM in GB (0 for CPU)

        Raises:
            ResourceExhaustedError: When insufficient resources (FR-021)
        """
        # Check RAM
        ram_info = self.get_system_ram_usage()
        if ram_info["available_gb"] < required_ram_gb:
            raise ResourceExhaustedError(
                resource_type="RAM",
                required=required_ram_gb,
                available=ram_info["available_gb"],
                unit="GB",
                suggestion=f"Model '{model_name}' needs more RAM. Close other applications or try a smaller model (tiny, base, small)."
            )

        # Check VRAM (if GPU device)
        if device != "cpu" and required_vram_gb > 0:
            vram_info = self.get_vram_usage(device)
            if vram_info["available_gb"] < required_vram_gb:
                raise ResourceExhaustedError(
                    resource_type="VRAM",
                    required=required_vram_gb,
                    available=vram_info["available_gb"],
                    unit="GB",
                    suggestion=f"Model '{model_name}' needs more VRAM on {device}. Use smaller model or switch to CPU."
                )

        logger.info(
            f"Resource validation passed for {model_name}: "
            f"RAM {required_ram_gb:.1f}GB/{ram_info['available_gb']:.1f}GB, "
            f"VRAM {required_vram_gb:.1f}GB"
        )

    def get_resource_summary(self, device: str) -> Dict[str, Any]:
        """
        Get comprehensive resource summary.

        Args:
            device: Device to include in summary

        Returns:
            Dictionary with RAM, VRAM, and threshold status
        """
        ram_info = self.get_system_ram_usage()
        vram_info = self.get_vram_usage(device)

        return {
            "ram": ram_info,
            "vram": vram_info,
            "thresholds": {
                "ram_threshold_percent": self.ram_threshold_percent,
                "vram_threshold_percent": self.vram_threshold_percent,
                "ram_exceeded": ram_info["percent"] >= self.ram_threshold_percent,
                "vram_exceeded": vram_info["percent"] >= self.vram_threshold_percent,
            },
            "device": device,
        }

    def estimate_available_ram_gb(self) -> float:
        """
        Estimate RAM available for model loading.

        Accounts for:
        - Current usage
        - Safety margin (10% reserve to stay under threshold)

        Returns:
            Estimated available RAM in GB
        """
        ram_info = self.get_system_ram_usage()

        # Apply safety margin: 90% of available to stay under threshold
        available_with_margin = ram_info["available_gb"] * 0.9

        return available_with_margin

    def can_fit_model(
        self,
        device: str,
        required_ram_gb: float,
        required_vram_gb: float,
    ) -> bool:
        """
        Check if model can fit in available memory.

        Args:
            device: Target device
            required_ram_gb: Required RAM
            required_vram_gb: Required VRAM (0 for CPU)

        Returns:
            True if model fits, False otherwise
        """
        # Check RAM with safety margin
        available_ram = self.estimate_available_ram_gb()
        if required_ram_gb > available_ram:
            return False

        # Check VRAM (if GPU)
        if device != "cpu" and required_vram_gb > 0:
            vram_info = self.get_vram_usage(device)
            # Apply safety margin (90% of available)
            available_vram = vram_info["available_gb"] * 0.9
            if required_vram_gb > available_vram:
                return False

        return True
