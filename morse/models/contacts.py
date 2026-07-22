import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from morse.tenant import TenantModel


def _generate_visitor_id():
    return secrets.token_hex(4).upper()


def generate_telegram_link_token():
    """Return a unique, unguessable token for Telegram deep-link account linking."""
    return secrets.token_urlsafe(32)


class Contact(TenantModel):
    class TelegramLinkError(Exception):
        """Raised when a Telegram account cannot be linked to this contact."""

    visitor_id = models.CharField(max_length=16, editable=False, blank=True, default="")
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    telegram_link_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )
    telegram_chat_id = models.BigIntegerField(null=True, blank=True)
    telegram_user_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    telegram_username = models.CharField(max_length=255, blank=True, default="")
    telegram_linked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "contacts"
        ordering = ["-updated_at"]
        unique_together = [("website", "session_id"), ("website", "visitor_id")]

    def save(self, *args, **kwargs):
        if not self.visitor_id:
            for _ in range(10):
                candidate = _generate_visitor_id()
                exists = Contact.unscoped.filter(
                    website_id=self.website_id, visitor_id=candidate
                ).exists()
                if not exists:
                    self.visitor_id = candidate
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.name:
            return self.name
        if self.email:
            return self.email
        return _("Visitor %(visitor_id)s") % {"visitor_id": self.visitor_id}

    @property
    def initials(self):
        name = self.display_name
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return name[:2].upper()

    @property
    def is_telegram_linked(self):
        return self.telegram_user_id is not None and self.telegram_chat_id is not None

    def ensure_telegram_link_token(self):
        """Create and persist a deep-link token if this contact does not have one."""
        if self.telegram_link_token:
            return self.telegram_link_token
        for _ in range(10):
            candidate = generate_telegram_link_token()
            if not Contact.unscoped.filter(telegram_link_token=candidate).exists():
                self.telegram_link_token = candidate
                self.save(update_fields=["telegram_link_token", "updated_at"])
                return self.telegram_link_token
        raise RuntimeError("Unable to allocate a unique Telegram link token")

    def clear_telegram_link_token(self):
        """Invalidate any outstanding deep-link token (single-use linking)."""
        if self.telegram_link_token is None:
            return
        self.telegram_link_token = None
        self.save(update_fields=["telegram_link_token", "updated_at"])

    def get_telegram_deep_link(self):
        """
        Return https://t.me/<BOT_USERNAME>?start=<token> or empty string if
        TELEGRAM_BOT_USERNAME is not configured.
        """
        username = (getattr(settings, "TELEGRAM_BOT_USERNAME", "") or "").lstrip("@")
        if not username:
            return ""
        token = self.ensure_telegram_link_token()
        return f"https://t.me/{username}?start={token}"

    def link_telegram_account(self, *, chat_id, user_id, username=""):
        """
        Attach a Telegram user/chat to this contact and invalidate the deep-link
        token so the link cannot be reused.

        Raises Contact.TelegramLinkError if the Telegram account is already
        linked to a different contact.
        """
        if user_id is None or chat_id is None:
            raise self.TelegramLinkError("Telegram user_id and chat_id are required")

        conflict = (
            Contact.unscoped.filter(telegram_user_id=user_id)
            .exclude(pk=self.pk)
            .first()
        )
        if conflict is not None:
            raise self.TelegramLinkError(
                "This Telegram account is already linked to another contact"
            )

        self.telegram_chat_id = int(chat_id)
        self.telegram_user_id = int(user_id)
        self.telegram_username = (username or "").lstrip("@")[:255]
        self.telegram_linked_at = timezone.now()
        self.telegram_link_token = None
        self.save(
            update_fields=[
                "telegram_chat_id",
                "telegram_user_id",
                "telegram_username",
                "telegram_linked_at",
                "telegram_link_token",
                "updated_at",
            ]
        )
