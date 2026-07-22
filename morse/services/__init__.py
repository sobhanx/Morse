"""Outbound notification providers (Telegram, and future Slack/WhatsApp/Email)."""

from .telegram import send_telegram_message, send_telegram_notification

__all__ = ["send_telegram_notification", "send_telegram_message"]
