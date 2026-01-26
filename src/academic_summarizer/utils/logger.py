"""Logging configuration for the academic summarizer application."""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO", log_file: Optional[Path] = None, verbose: bool = False
) -> logging.Logger:
    """
    Set up logging with both console and file handlers.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        verbose: If True, enables more detailed logging

    Returns:
        Configured logger instance
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    if verbose:
        numeric_level = logging.DEBUG

    # Create logger
    logger = logging.getLogger("academic_summarizer")
    logger.setLevel(numeric_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with Rich formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=verbose,
    )
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(
        "%(message)s",
        datefmt="[%X]",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (uses module name if not provided)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"academic_summarizer.{name}")
    return logging.getLogger("academic_summarizer")


def mask_api_key(api_key: str) -> str:
    """
    Mask API key for safe logging.

    Args:
        api_key: Full API key

    Returns:
        Masked API key (shows first 8 and last 4 characters)
    """
    if not api_key or len(api_key) < 12:
        return "****"
    return f"{api_key[:8]}...{api_key[-4:]}"
