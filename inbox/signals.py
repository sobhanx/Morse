"""Inbox model signals."""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message
from .services.telegram import send_telegram_notification


def _format_visitor_telegram_alert(message: Message) -> str:
    conversation = message.conversation
    contact = conversation.contact
    website = message.website
    preview = (message.content or "").strip()
    if message.message_type == Message.MessageType.AUDIO:
        preview = preview or "Voice message"
    if len(preview) > 200:
        preview = preview[:197] + "..."

    site_label = website.name if website else "Unknown site"
    visitor_label = contact.display_name if contact else "Visitor"

    return (
        f"New visitor message on {site_label}\n"
        f"From: {visitor_label}\n"
        f"Conversation #{conversation.id}\n"
        f"{preview}"
    )


@receiver(post_save, sender=Message, dispatch_uid="morse_message_telegram_notify")
def notify_telegram_on_visitor_message(sender, instance, created, **kwargs):
    """Notify Telegram once for each newly created visitor message."""
    if not created:
        return
    if instance.sender_type != Message.SenderType.VISITOR:
        return

    # Build the payload now (create-time content); send only after commit.
    alert_text = _format_visitor_telegram_alert(instance)
    transaction.on_commit(lambda: send_telegram_notification(alert_text))
