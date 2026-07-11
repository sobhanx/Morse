import secrets
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from websites.tenant import TenantModel


def _generate_visitor_id():
    return secrets.token_hex(4).upper()


class Contact(TenantModel):
    visitor_id = models.CharField(max_length=16, editable=False, blank=True, default="")
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
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
