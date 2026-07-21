"""Telegram Bot API webhook endpoints."""

import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services.telegram_linking import handle_telegram_update

logger = logging.getLogger(__name__)


def _webhook_secret_ok(request) -> bool:
    """
    Validate Telegram's X-Telegram-Bot-Api-Secret-Token when configured.

    If TELEGRAM_WEBHOOK_SECRET is empty, the check is skipped (local/dev).
    Invalid or missing secrets are rejected with a constant-time compare.
    """
    expected = (getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or "").strip()
    if not expected:
        return True
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") or ""
    return hmac.compare_digest(provided, expected)


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """
    Receive Telegram Bot API updates (account linking via /start <token>).

    - POST only
    - Rejects invalid webhook secrets
    - Never crashes on malformed payloads

    Does not implement chat reply notifications yet.
    """
    if not _webhook_secret_ok(request):
        return HttpResponseForbidden("Forbidden")

    try:
        raw = request.body.decode("utf-8") if request.body else "{}"
        update = json.loads(raw or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Telegram webhook received invalid JSON")
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    if not isinstance(update, dict):
        return JsonResponse({"ok": False, "error": "invalid update"}, status=400)

    try:
        handle_telegram_update(update)
    except Exception as exc:
        # Acknowledge to avoid endless Telegram retries; do not leak details.
        logger.warning(
            "Telegram webhook handler failed: %s: %s",
            type(exc).__name__,
            str(exc)[:200],
        )

    return JsonResponse({"ok": True})
