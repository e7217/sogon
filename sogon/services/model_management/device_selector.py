"""
DeviceSelector: Device detection and compatibility validation.

Handles CPU/CUDA/MPS device detection and compute type validation.
"""

import logging
from typing import List, Dict, Any

import torch

from sogon.exceptions import DeviceNotAvailableError, ResourceExhaustedError

logger = logging.getLogger(__name__)


class DeviceSelector:
    """
    Manages device detection and compatibility validation.

    Responsibilities:
    - Detect available devices (CPU, CUDA, MPS)
    - Validate device-compute_type compatibility
    - Auto-select optimal device
    - Check device requirements

    Supported Devices:
    - CPU: Always available, int8/int16 compute types
    - CUDA: NVIDIA GPUs, int8/float16/float32 compute types
    - MPS: Apple Silicon, float16/float32 compute types
    """

    # Device-compute type compatibility matrix (FR-008)
    DEVICE_COMPUTE_TYPES = {
        "cpu": {"int8", "int16"},
        "cuda": {"int8", "float16", "float32"},
        "mps": {"float16", "float32"},
    }

    def __init__(self):
        """Initialize DeviceSelector."""
        pass

    def get_available_devices(self) -> List[str]:
        """
        Get list of available devices on this system.

        Returns:
            List of device names (e.g., ["cpu", "cuda"])

        Note:
            CPU is always available as fallback (FR-006)
        """
        devices = ["cpu"]  # CPU always available

        # Check CUDA availability
        if torch.cuda.is_available():
            devices.append("cuda")
            logger.info("CUDA device detected")

        # Check MPS availability (Apple Silicon, torch >= 2.0)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            devices.append("mps")
            logger.info("MPS device detected (Apple Silicon)")

        return devices

    def validate_device_compute_type(self, device: str, compute_type: str) -> None:
        """
        Validate device-compute_type compatibility.

        Args:
            device: Device name (cpu/cuda/mps)
            compute_type: Compute precision (int8/float16/float32)

        Raises:
            DeviceNotAvailableError: When combination invalid

        Examples:
            >>> selector = DeviceSelector()
            >>> selector.validate_device_compute_type("cpu", "int8")  # OK
            >>> selector.validate_device_compute_type("cpu", "float16")  # Raises
        """
        valid_types = self.DEVICE_COMPUTE_TYPES.get(device, set())

        if compute_type not in valid_types:
            valid_str = ", ".join(sorted(valid_types))
            raise DeviceNotAvailableError(
                device=f"{device} with {compute_type}",
                available_devices=[f"{device} with {t}" for t in sorted(valid_types)]
            )

        logger.debug(f"Validated device-compute_type: {device}-{compute_type}")

    def auto_select_device(self) -> str:
        """
        Automatically select optimal device.

        Selection priority (FR-006, FR-010):
        1. CUDA (if available) - Best performance
        2. MPS (if available) - Apple Silicon acceleration
        3. CPU (fallback) - Always available

        Returns:
            Selected device name
        """
        available = self.get_available_devices()

        # Prefer GPU acceleration
        if "cuda" in available:
            logger.info("Auto-selected CUDA device")
            return "cuda"

        if "mps" in available:
            logger.info("Auto-selected MPS device (Apple Silicon)")
            return "mps"

        logger.info("Auto-selected CPU device (no GPU available)")
        return "cpu"

    def auto_select_compute_type(self, device: str) -> str:
        """
        Auto-select optimal compute type for device.

        Selection strategy:
        - CUDA: float16 (balance of speed/quality)
        - MPS: float16 (best supported precision)
        - CPU: int8 (speed priority)

        Args:
            device: Target device

        Returns:
            Optimal compute type for device
        """
        if device == "cuda":
            return "float16"
        elif device == "mps":
            return "float16"
        else:  # cpu
            return "int8"

    def is_device_available(self, device: str) -> bool:
        """
        Check if specific device is available.

        Args:
            device: Device name to check

        Returns:
            True if device available, False otherwise
        """
        available = self.get_available_devices()
        return device in available

    def raise_if_unavailable(self, device: str) -> None:
        """
        Raise error if device unavailable, with helpful message.

        Args:
            device: Device to check

        Raises:
            DeviceNotAvailableError: When device unavailable (FR-025)
        """
        if not self.is_device_available(device):
            available = self.get_available_devices()
            raise DeviceNotAvailableError(device=device, available_devices=available)

    def get_device_info(self, device: str) -> Dict[str, Any]:
        """
        Get device metadata and properties.

        Args:
            device: Device name

        Returns:
            Dictionary with device information

        Example:
            >>> selector.get_device_info("cuda")
            {
                "device_type": "cuda",
                "name": "NVIDIA GeForce RTX 3090",
                "memory_gb": 24.0,
                "compute_capability": (8, 6),
            }
        """
        info = {"device_type": device}

        if device == "cuda" and torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            info.update({
                "name": props.name,
                "memory_gb": props.total_memory / (1024**3),
                "compute_capability": (props.major, props.minor),
            })

        elif device == "mps":
            # MPS uses unified memory (shared with system RAM)
            import psutil
            mem = psutil.virtual_memory()
            info.update({
                "name": "Apple Silicon (MPS)",
                "memory_gb": mem.total / (1024**3),
                "unified_memory": True,
            })

        elif device == "cpu":
            import psutil
            info.update({
                "name": "CPU",
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
            })

        return info

    def _get_device_memory_gb(self, device: str) -> float:
        """
        Get available memory for device in GB.

        Args:
            device: Device name

        Returns:
            Available memory in GB
        """
        if device == "cuda" and torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            total_memory = props.total_memory / (1024**3)
            allocated = torch.cuda.memory_allocated(0) / (1024**3)
            return total_memory - allocated

        elif device == "mps":
            # MPS uses system RAM
            import psutil
            mem = psutil.virtual_memory()
            return mem.available / (1024**3)

        else:  # cpu
            import psutil
            mem = psutil.virtual_memory()
            return mem.available / (1024**3)

    def check_model_fits(self, device: str, model_size_gb: float) -> None:
        """
        Verify model fits in device memory.

        Args:
            device: Target device
            model_size_gb: Model size in GB

        Raises:
            ResourceExhaustedError: When insufficient memory
        """
        available_gb = self._get_device_memory_gb(device)

        if model_size_gb > available_gb:
            raise ResourceExhaustedError(
                resource_type="VRAM" if device in ["cuda", "mps"] else "RAM",
                required=model_size_gb,
                available=available_gb,
                unit="GB",
                suggestion=f"Try a smaller model or free up memory on {device}."
            )

    def recommend_device_for_model(self, model_size_gb: float) -> str:
        """
        Recommend optimal device based on model requirements.

        Args:
            model_size_gb: Model size in GB

        Returns:
            Recommended device name

        Strategy:
        1. Check each device's available memory
        2. Prefer GPU if model fits
        3. Fallback to CPU (can use swap)
        """
        available_devices = self.get_available_devices()

        # Check each device's capacity
        for device in ["cuda", "mps", "cpu"]:
            if device not in available_devices:
                continue

            available_memory = self._get_device_memory_gb(device)

            if available_memory >= model_size_gb:
                logger.info(
                    f"Recommending {device}: {available_memory:.1f}GB available "
                    f"for {model_size_gb:.1f}GB model"
                )
                return device

        # If no device has enough memory, recommend CPU (can use swap)
        logger.warning(
            f"No device has {model_size_gb:.1f}GB available, "
            f"recommending CPU with swap"
        )
        return "cpu"
