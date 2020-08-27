"""Exceptions used in PyDSS"""

class InvalidConfiguration(Exception):
    """Raised when a bad configuration is detected."""

class InvalidParameter(Exception):
    """Raised when bad user input is detected."""

class OpenDssConvergenceError(Exception):
    """Raised when OpenDSS fails to converge on a solution."""

