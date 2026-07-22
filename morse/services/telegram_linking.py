"""Telegram deep-link account linking (/start <token>)."""

import logging
import re

from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from morse.models import Contact

from .telegram import send_telegram_message

logger = logging.getLogger(__name__)

_START_RE = re.compile(r"^/start(?:@\w+)?(?:\s+(.+))?$", re.IGNORECASE | re.DOTALL)


def parse_start_token(text: str):
    """
    Extract the deep-link payload from a /start command.

    Returns the token string, or None if this is not a /start with a payload.
    """
    if not text or not isinstance(text, str):
        return None
    match = _START_RE.match(text.strip())
    if not match:
        return None
    payload = (match.group(1) or "").strip()
    return payload or None


def link_contact_from_start_token(*, token, chat_id, user_id, username=""):
    """
    Link a Telegram user to the Contact identified by ``token``.

    On success the deep-link token is cleared (single-use). Returns
    ``(ok: bool, reply_text: str)``.
    """
    invalid = _(
        "This link is invalid or has expired. Please request a new linking link."
    )
    if not token or chat_id is None or user_id is None:
        return False, invalid

    try:
        with transaction.atomic():
            contact = (
                Contact.unscoped.select_for_update()
                .filter(telegram_link_token=token)
                .first()
            )
            if contact is None:
                return False, invalid

            contact.link_telegram_account(
                chat_id=chat_id,
                user_id=user_id,
                username=username or "",
            )
    except Contact.TelegramLinkError:
        return False, _(
            "This Telegram account is already linked to another contact and cannot "
            "be linked again."
        )
    except (IntegrityError, TypeError, ValueError):
        logger.warning(
            "Telegram link failed for user_id=%s",
            user_id,
        )
        return False, _(
            "We could not link your Telegram account right now. Please try again later."
        )

    return True, _(
        "Your Telegram account has been linked successfully. "
        "You can return to the chat — we will use this account for updates."
    )


def handle_telegram_update(update: dict) -> bool:
    """
    Process one Telegram Bot API update object.

    Handles /start <token> deep-link linking only. Returns True if a linking
    attempt was handled (success or failure reply sent), False if ignored.
    Never raises for malformed payloads.
    """
    if not isinstance(update, dict):
        return False

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return False

    text = message.get("text") or ""
    token = parse_start_token(text)
    if token is None:
        return False

    chat = message.get("chat")
    user = message.get("from")
    if not isinstance(chat, dict) or not isinstance(user, dict):
        return False

    chat_id = chat.get("id")
    user_id = user.get("id")
    username = user.get("username") or ""
    if not isinstance(username, str):
        username = ""

    if chat_id is None or user_id is None:
        return False

    try:
        _ok, reply = link_contact_from_start_token(
            token=token,
            chat_id=chat_id,
            user_id=user_id,
            username=username,
        )
    except Exception as exc:
        logger.warning(
            "Telegram link handler failed unexpectedly: %s",
            type(exc).__name__,
        )
        return False

    try:
        send_telegram_message(chat_id, str(reply))
    except Exception as exc:
        logger.warning(
            "Telegram link reply failed: %s",
            type(exc).__name__,
        )
    return True
