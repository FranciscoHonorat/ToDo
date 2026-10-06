class InvalidTitleError(ValueError):
    """Raised when a task title is invalid (e.g., empty or only spaces)."""

class TaskNotFoundError(ValueError):
    """Raised when a task is not found."""
