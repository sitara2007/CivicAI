"""Audit logging services for CivicOS.

Provides centralized logging functionality for tracking application events.
"""

import logging


class AuditLogger:
    """Audit logger for tracking application events."""

    def __init__(self, name: str):
        """Initialize logger with the given name."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Create formatter and handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(handler)

    def info(self, message: str) -> None:
        """Log an informational message."""
        self.logger.info(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.logger.error(message)
