"""Shim — admin registrations live in morse.admin."""

from morse.admin import website_usage_dashboard  # noqa: F401
from morse.usage import website_usage_queryset  # noqa: F401

__all__ = ["website_usage_dashboard", "website_usage_queryset"]
