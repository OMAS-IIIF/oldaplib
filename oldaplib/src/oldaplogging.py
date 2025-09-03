# Module-level logger (default fallback)
"""A utility module for managing a global logger instance.

This module provides functionality to set and retrieve a global logger that
can be used across the application. By default, it initializes with a
null handler to avoid logging output when no external logger is specified.
"""
import logging

_logger = logging.getLogger("oldaplib")
_logger.addHandler(logging.NullHandler())

def set_logger(external_logger: logging.Logger):
    """
    Injects an external logger to be used by the system. This method allows
    passing a pre-configured logger instance, such as Flask's `app.logger`,
    to integrate and synchronize logging behaviors with external applications
    or frameworks.

    :param external_logger: The external logger instance to be used.
    :type external_logger: logging.Logger
    :return: None
    """
    global _logger
    _logger = external_logger

def get_logger() -> logging.Logger:
    """
    Retrieves the main application logger.

    This function returns a logging.Logger instance that is used for logging
    messages throughout the application.

    :return: The main logger instance used by the application.
    :rtype: logging.Logger
    """
    return _logger