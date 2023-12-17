"""Exceptions used in PyDSS"""


class InvalidConfigurationError(Exception):
    """Raised when a bad configuration is detected."""


class InvalidParameterError(Exception):
    """Raised when bad user input is detected."""


class HelicsConvergenceError(Exception):
    """Raised when OpenDSS fails to converge on a solution."""


class PsseConvergenceError(Exception):
    """Raised when OpenDSS fails to converge on a solution."""
