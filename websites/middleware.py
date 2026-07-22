"""Shim — WebsiteMiddleware now lives in morse.middleware."""

from morse.middleware import WebsiteMiddleware  # noqa: F401

__all__ = ["WebsiteMiddleware"]
