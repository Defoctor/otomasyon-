"""Application-specific exceptions with user-readable messages."""


class KidsShortsError(RuntimeError):
    """Base exception for expected application failures."""


class ConfigurationError(KidsShortsError):
    """Raised when application configuration is invalid."""


class StoryGenerationError(KidsShortsError):
    """Raised when a story provider cannot produce a valid story."""


class PersistenceError(KidsShortsError):
    """Raised when an episode cannot be saved consistently."""
