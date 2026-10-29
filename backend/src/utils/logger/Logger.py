"""Compatibility imports for the original logger module."""

from .logger import Logger, correlation_id, request_id

__all__ = ["Logger", "correlation_id", "request_id"]
