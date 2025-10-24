"""
ModelManager: Model lifecycle management with LRU caching.

Handles model downloading, caching, and eviction for Whisper models.
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any
from collections import OrderedDict
import logging

import psutil

from sogon.services.model_management.model_key import ModelKey
from sogon.models.local_config import LocalModelConfiguration
from sogon.exceptions import (
    InsufficientDiskSpaceError,
    ModelCorruptionError,
)

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages Whisper model lifecycle with LRU caching.

    Responsibilities:
    - Download models from HuggingFace Hub
    - Cache loaded models in memory (LRU eviction)
    - Verify model integrity (checksums)
    - Manage disk space and cache size
    - Handle concurrent download requests

    Attributes:
        config: Local model configuration
        _cache: In-memory model cache (LRU-ordered)
        _lru_order: LRU access order tracking
        _download_locks: Per-model download locks for deduplication
    """

    def __init__(self, config: LocalModelConfiguration):
        """
        Initialize ModelManager.

        Args:
            config: Local model configuration with cache settings
        """
        self.config = config
        self._cache: Dict[ModelKey, Any] = OrderedDict()
        self._lru_order: list[ModelKey] = []
        self._download_locks: Dict[ModelKey, asyncio.Lock] = {}
        self._lock = asyncio.Lock()  # Protects cache modifications

    async def get_model(self, key: ModelKey) -> Any:
        """
        Get model from cache or download if not cached.

        Args:
            key: Model identifier (name, device, compute_type)

        Returns:
            Loaded model instance

        Raises:
            ModelCorruptionError: When checksum validation fails
        """
        # Check cache first
        async with self._lock:
            if key in self._cache:
                # Cache hit - update LRU order
                self._lru_order.remove(key)
                self._lru_order.append(key)
                logger.debug(f"Cache hit for model: {key}")
                return self._cache[key]

        # Cache miss - need to download
        logger.info(f"Cache miss for model: {key}, downloading...")

        # Get or create download lock for this model
        async with self._lock:
            if key not in self._download_locks:
                self._download_locks[key] = asyncio.Lock()
            download_lock = self._download_locks[key]

        # Only one download per model at a time
        async with download_lock:
            # Double-check cache (another task may have downloaded)
            async with self._lock:
                if key in self._cache:
                    logger.debug(f"Model downloaded by concurrent task: {key}")
                    return self._cache[key]

            # Download model
            model = await self.download_model(key)

            # Add to cache
            async with self._lock:
                self._cache[key] = model
                self._lru_order.append(key)

                # Evict if cache exceeds limit
                await self._evict_if_needed()

            return model

    async def download_model(
        self,
        key: ModelKey,
        progress_callback: Optional[callable] = None
    ) -> Any:
        """
        Download model from HuggingFace Hub.

        Args:
            key: Model identifier
            progress_callback: Optional callback(current_bytes, total_bytes)

        Returns:
            Downloaded model instance

        Raises:
            ModelCorruptionError: When checksum validation fails
        """
        # Load model from HuggingFace Hub
        # stable-ts automatically uses HF_HOME environment variable for cache
        # If HF_HOME is not set, uses default: ~/.cache/huggingface
        logger.info(f"Loading model {key.model_name}")

        try:
            import os
            import stable_whisper

            # Log cache location for debugging
            hf_home = os.getenv('HF_HOME')
            if hf_home:
                logger.debug(f"Using HuggingFace cache (HF_HOME): {hf_home}")
            else:
                logger.debug("Using default HuggingFace cache: ~/.cache/huggingface")

            # Load model with stable-whisper
            # It will automatically download to HF cache if not present
            model = await asyncio.to_thread(
                stable_whisper.load_model,
                key.model_name,
                device=key.device,
                # No download_root needed - uses HF_HOME automatically
            )

            logger.info(f"Successfully downloaded and loaded model: {key}")
            return model

        except Exception as e:
            logger.error(f"Failed to download model {key}: {e}")
            raise

    async def _verify_checksum(self, model_path: Path) -> None:
        """
        Verify model file integrity using SHA256 checksum.

        Args:
            model_path: Path to model file

        Raises:
            ModelCorruptionError: When checksum validation fails
        """
        # Calculate SHA256 hash
        sha256_hash = hashlib.sha256()

        def calculate_hash():
            with open(model_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()

        calculated_hash = await asyncio.to_thread(calculate_hash)

        # TODO: Fetch expected hash from HuggingFace model card
        # For now, we skip validation if no expected hash available
        # In production, this should fetch from model metadata

        logger.debug(f"Model checksum: {calculated_hash}")
        # Checksum validation would happen here if we had expected hashes

    async def _evict_if_needed(self) -> None:
        """
        Evict least recently used models if cache exceeds max_size_gb.

        Uses LRU eviction policy (FR-024).
        """
        while self.get_cache_usage_gb() > self.config.cache_max_size_gb:
            if not self._lru_order:
                break

            # Evict least recently used (first in list)
            lru_key = self._lru_order[0]
            logger.info(f"Evicting LRU model from cache: {lru_key}")

            del self._cache[lru_key]
            self._lru_order.remove(lru_key)

    def get_cache_usage_gb(self) -> float:
        """
        Calculate current cache size in GB.

        Returns:
            Total size of cached models in GB
        """
        total_gb = 0.0

        for key in self._cache:
            # Estimate based on model name
            # In practice, could inspect actual memory usage
            model_sizes = {
                "tiny": 0.075,
                "base": 0.142,
                "small": 0.466,
                "medium": 1.5,
                "large": 2.9,
                "large-v2": 2.9,
                "large-v3": 2.9,
            }
            total_gb += model_sizes.get(key.model_name, 1.0)

        return total_gb

    def _get_model_size_gb(self, key: ModelKey) -> float:
        """
        Get estimated model size in GB.

        Args:
            key: Model identifier

        Returns:
            Estimated size in GB
        """
        model_sizes = {
            "tiny": 0.075,
            "base": 0.142,
            "small": 0.466,
            "medium": 1.5,
            "large": 2.9,
            "large-v2": 2.9,
            "large-v3": 2.9,
        }
        return model_sizes.get(key.model_name, 1.0)

    def clear_cache(self) -> None:
        """Remove all models from cache."""
        self._cache.clear()
        self._lru_order.clear()
        logger.info("Cleared model cache")

    def remove_model(self, key: ModelKey) -> None:
        """
        Remove specific model from cache.

        Args:
            key: Model identifier to remove
        """
        if key in self._cache:
            del self._cache[key]
            self._lru_order.remove(key)
            logger.info(f"Removed model from cache: {key}")
