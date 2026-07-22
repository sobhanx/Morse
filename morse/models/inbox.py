from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from morse.models.contacts import Contact
from morse.tenant import TenantModel


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
        app_label = "inbox"
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
        if not msg:
            return _("No messages yet")
        if msg.message_type == Message.MessageType.AUDIO:
            return msg.content or _("Voice message")
        return (msg.content or "")[:80]


class Message(TenantModel):
    class SenderType(models.TextChoices):
        VISITOR = "visitor", _("Visitor")
        AGENT = "agent", _("Agent")
        SYSTEM = "system", _("System")

    class MessageType(models.TextChoices):
        TEXT = "text", _("Text")
        AUDIO = "audio", _("Audio")

    MAX_VOICE_SECONDS = 60
    MAX_VOICE_BYTES = 5 * 1024 * 1024
    ALLOWED_AUDIO_TYPES = (
        "audio/webm",
        "audio/ogg",
        "audio/mp4",
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/aac",
    )

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
    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    content = models.TextField(blank=True)
    audio = models.FileField(
        upload_to="chat_audio/%Y/%m/",
        blank=True,
        null=True,
    )
    duration_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "inbox"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if self.conversation_id and not self.website_id:
            self.website_id = self.conversation.website_id
        if self.message_type == self.MessageType.AUDIO and not self.content:
            self.content = str(_("Voice message"))
        super().save(*args, **kwargs)

    def __str__(self):
        if self.message_type == self.MessageType.AUDIO:
            return f"{self.sender_type}: [voice]"
        return f"{self.sender_type}: {(self.content or '')[:50]}"

    @property
    def sender_name(self):
        if self.sender_type == Message.SenderType.AGENT and self.agent:
            return self.agent.get_full_name() or self.agent.username
        if self.sender_type == Message.SenderType.VISITOR:
            return self.conversation.contact.display_name
        return _("System")

    @property
    def audio_url(self):
        if self.audio:
            return reverse("inbox:message_audio", args=[self.id])
        return None

    @property
    def audio_mime_type(self):
        if not self.audio:
            return None
        from inbox.views import audio_content_type

        return audio_content_type(self.audio.name)

    def to_payload(self):
        return {
            "id": self.id,
            "content": self.content,
            "message_type": self.message_type,
            "audio_url": self.audio_url,
            "audio_mime_type": self.audio_mime_type,
            "duration_seconds": self.duration_seconds,
            "sender_type": self.sender_type,
            "sender_name": self.sender_name,
            "created_at": self.created_at.isoformat(),
        }
