from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from contacts.models import Contact
from websites.tenant import TenantModel


class Conversation(TenantModel):
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        PENDING = "pending", _("Pending")
        RESOLVED = "resolved", _("Resolved")

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="conversations"
    )
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversations",
    )
    is_unread = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        if self.contact_id and not self.website_id:
            self.website_id = self.contact.website_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contact.display_name} — {self.get_status_display()}"

    @property
    def last_message(self):
        return self.messages.order_by("-created_at").first()

    @property
    def preview(self):
        msg = self.last_message
        if msg:
            return msg.content[:80]
        return _("No messages yet")


class Message(TenantModel):
    class SenderType(models.TextChoices):
        VISITOR = "visitor", _("Visitor")
        AGENT = "agent", _("Agent")
        SYSTEM = "system", _("System")

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender_type = models.CharField(max_length=20, choices=SenderType.choices)
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if self.conversation_id and not self.website_id:
            self.website_id = self.conversation.website_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender_type}: {self.content[:50]}"

    @property
    def sender_name(self):
        if self.sender_type == Message.SenderType.AGENT and self.agent:
            return self.agent.get_full_name() or self.agent.username
        if self.sender_type == Message.SenderType.VISITOR:
            return self.conversation.contact.display_name
        return _("System")
