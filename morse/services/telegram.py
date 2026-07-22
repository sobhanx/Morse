"""Telegram Bot API notification provider."""

import logging
import re

import requests
from django.conf import settings

from .base import NotificationProvider

logger = logging.getLogger(__name__)

TELEGRAM_API_TIMEOUT = 10
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Telegram bot tokens appear in URL paths as /bot<token>/...
_BOT_PATH_RE = re.compile(r"/bot[^/\s]+/")


def _sanitize_telegram_error(message: str, bot_token: str = "") -> str:
    """Strip bot tokens / bot URL paths from error text before logging."""
    text = message or ""
    if bot_token:
        text = text.replace(bot_token, "[REDACTED]")
    text = _BOT_PATH_RE.sub("/bot[REDACTED]/", text)
    return text[:300]


class TelegramNotificationProvider(NotificationProvider):
    name = "telegram"

    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = (
            bot_token
            if bot_token is not None
            else getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        )
        self.chat_id = (
            chat_id if chat_id is not None else getattr(settings, "TELEGRAM_CHAT_ID", "")
        )

    def configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, message: str) -> bool:
        if not self.bot_token:
            logger.warning(
                "Telegram notification skipped: TELEGRAM_BOT_TOKEN must be set"
            )
            return False
        if not self.chat_id:
            logger.warning(
                "Telegram notification skipped: chat_id is required"
            )
            return False

        url = TELEGRAM_API_URL.format(token=self.bot_token)
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=TELEGRAM_API_TIMEOUT)
        except requests.RequestException as exc:
            logger.warning(
                "Telegram notification request failed: %s: %s",
                type(exc).__name__,
                _sanitize_telegram_error(str(exc), self.bot_token),
            )
            return False

        if response.status_code != 200:
            logger.warning(
                "Telegram notification failed: status=%s body=%s",
                response.status_code,
                _sanitize_telegram_error(response.text, self.bot_token),
            )
            return False

        try:
            data = response.json()
        except ValueError:
            logger.warning("Telegram notification failed: invalid JSON response")
            return False

        if not data.get("ok"):
            description = _sanitize_telegram_error(
                str(data.get("description", "unknown")),
                self.bot_token,
            )
            logger.warning(
                "Telegram notification rejected: description=%s",
                description,
            )
            return False

        return True


def send_telegram_notification(message: str) -> bool:
    """
    Send a plain-text Telegram message to the configured operator chat.

    Returns True on success, False if credentials are missing or delivery fails.
    Does not raise for configuration or network errors.
    """
    return TelegramNotificationProvider().send(message)


def send_telegram_message(chat_id, message: str) -> bool:
    """
    Send a plain-text Telegram message to an arbitrary chat_id.

    Used for visitor-facing replies (e.g. account-linking confirmation).
    Requires TELEGRAM_BOT_TOKEN only.
    """
    if chat_id is None or chat_id == "":
        logger.warning("Telegram message skipped: chat_id is required")
        return False
    return TelegramNotificationProvider(chat_id=str(chat_id)).send(message)


def _telegram_api_call(method: str, *, payload=None, http_method="post"):
    """
    Call a Telegram Bot API method.

    Returns (ok: bool, data: dict|None, error: str|None).
    Never includes the bot token in returned error strings.
    """
    bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
    if not bot_token:
        return False, None, "TELEGRAM_BOT_TOKEN is not set"

    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    try:
        if http_method.lower() == "get":
            response = requests.get(url, params=payload or {}, timeout=TELEGRAM_API_TIMEOUT)
        else:
            response = requests.post(url, json=payload or {}, timeout=TELEGRAM_API_TIMEOUT)
    except requests.RequestException as exc:
        return (
            False,
            None,
            f"{type(exc).__name__}: {_sanitize_telegram_error(str(exc), bot_token)}",
        )

    try:
        data = response.json()
    except ValueError:
        return (
            False,
            None,
            f"invalid JSON response (HTTP {response.status_code})",
        )

    if not isinstance(data, dict):
        return False, None, "unexpected response shape"

    if not data.get("ok"):
        description = _sanitize_telegram_error(
            str(data.get("description", "unknown")),
            bot_token,
        )
        return False, data, description

    return True, data, None


def set_telegram_webhook(url: str, *, secret_token: str = "") -> tuple[bool, str]:
    """
    Register the Morse Telegram webhook with Telegram's setWebhook API.

    Returns (success, message).
    """
    url = (url or "").strip()
    if not url:
        return False, "TELEGRAM_WEBHOOK_URL is not set"

    payload = {
        "url": url,
        "allowed_updates": ["message"],
        "drop_pending_updates": False,
    }
    secret = (secret_token or "").strip()
    if secret:
        payload["secret_token"] = secret

    ok, data, error = _telegram_api_call("setWebhook", payload=payload)
    if not ok:
        return False, error or "setWebhook failed"

    result = data.get("result") if isinstance(data, dict) else None
    description = ""
    if isinstance(data, dict):
        description = data.get("description") or ""
    if result is True or description:
        detail = description or "Webhook set successfully"
        return True, detail
    return True, "Webhook set successfully"


def get_telegram_webhook_info() -> tuple[bool, dict | None, str]:
    """
    Fetch the current webhook configuration via getWebhookInfo.

    Returns (success, result_dict_or_None, error_message).
    """
    ok, data, error = _telegram_api_call("getWebhookInfo", http_method="get")
    if not ok:
        return False, None, error or "getWebhookInfo failed"
    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, dict):
        return False, None, "getWebhookInfo returned no result object"
    return True, result, ""
