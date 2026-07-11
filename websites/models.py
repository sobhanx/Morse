import secrets
import uuid

from django.conf import settings
from django.db import models

from websites.tenant import TenantModel


def _generate_public_key():
    return secrets.token_urlsafe(24)


def _generate_private_key():
    return secrets.token_urlsafe(48)


class Website(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_websites",
    )
    is_active = models.BooleanField(
        default=False,
        help_text="When active, the chat widget accepts visitor messages.",
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    public_widget_key = models.CharField(
        max_length=64, unique=True, default=_generate_public_key, editable=False
    )
    private_api_key = models.CharField(
        max_length=96, unique=True, default=_generate_private_key, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class WebsiteAgent(TenantModel):
    """Links support agents to a website (tenant)."""

    website = models.ForeignKey(
        Website,
        on_delete=models.CASCADE,
        related_name="agents",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="website_memberships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("website", "user")]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} @ {self.website.name}"
