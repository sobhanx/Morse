"""Shim — Telegram services live in morse.services."""

from morse.services import send_telegram_message, send_telegram_notification

__all__ = ["send_telegram_message", "send_telegram_notification"]
