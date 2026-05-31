"""Exceptions raised by the pact-ax-client SDK."""


class PactAXError(Exception):
    """Base exception for all pact-ax-client errors."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(PactAXError):
    """Resource not found (404)."""


class ConflictError(PactAXError):
    """Resource already exists (409)."""


class ValidationError(PactAXError):
    """Request validation failed (422)."""


class ServerError(PactAXError):
    """Unexpected server error (5xx)."""


class ConnectionError(PactAXError):
    """Could not connect to the pact-ax server."""
