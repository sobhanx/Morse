"""Shim — Contact model lives in morse.models."""

from morse.models import Contact, generate_telegram_link_token

__all__ = ["Contact", "generate_telegram_link_token"]
