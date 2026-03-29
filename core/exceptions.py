"""Custom exceptions for crewai-dev-teams."""


class CrewAlreadyExistsError(Exception):
    """Raised when attempting to create a crew that already exists."""


class CrewNotFoundError(Exception):
    """Raised when a requested crew cannot be found."""


class MissingEnvVarError(Exception):
    """Raised when one or more required environment variables are absent."""


class GitNotFoundError(Exception):
    """Raised when the git binary is not found on the system."""


class GitOperationError(Exception):
    """Raised when a git command fails (non-zero exit, merge conflict, etc.)."""



class SlackUnavailableError(Exception):
    """Raised when the Slack API is unavailable after exhausting retries."""
