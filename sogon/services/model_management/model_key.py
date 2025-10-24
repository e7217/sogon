"""
ModelKey value object for model caching.

Immutable key used for identifying and caching loaded Whisper models.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelKey:
    """
    Immutable key for identifying cached Whisper models.

    A model is uniquely identified by the combination of:
    - model_name: The Whisper model size (tiny, base, small, etc.)
    - device: The compute device (cpu, cuda, mps)
    - compute_type: The numerical precision (int8, float16, float32)

    The same model with different devices or compute types are cached separately.

    Example:
        >>> key1 = ModelKey(model_name="base", device="cpu", compute_type="int8")
        >>> key2 = ModelKey(model_name="base", device="cuda", compute_type="float16")
        >>> key1 == key2
        False

        >>> # Can be used as dict key
        >>> cache = {key1: model1, key2: model2}
        >>> model = cache[key1]
    """

    model_name: str
    device: str
    compute_type: str

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"ModelKey(model={self.model_name}, device={self.device}, compute={self.compute_type})"

    def __str__(self) -> str:
        """Return user-friendly string representation."""
        return f"{self.model_name}-{self.device}-{self.compute_type}"
