"""Module for error context and severity definitions.

Provides core error handling classes and enums used throughout the application
for standardized error management.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Levels of error severity."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ErrorContext:
    """Error context for detailed logging."""

    operation: str
    details: dict[str, Any]
    severity: ErrorSeverity
    recovery_action: str | None = None
