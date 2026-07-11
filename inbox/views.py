import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from websites.models import WebsiteAgent
from websites.permissions import user_can_access_website, website_required

from .models import Conversation, Message


def _broadcast_message(message):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    payload = {
        "type": "chat.message",
        "message": {
            "id": message.id,
            "content": message.content,
            "sender_type": message.sender_type,
            "sender_name": message.sender_name,
            "created_at": message.created_at.isoformat(),
        },
    }
    async_to_sync(channel_layer.group_send)(
        f"conversation_{message.conversation_id}", payload
    )


@login_required
@website_required
@require_POST
def send_agent_message(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": _("Invalid JSON")}, status=400)

    content = data.get("content", "").strip()
    if not content:
        return JsonResponse({"error": _("Message cannot be empty")}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        website=request.website,
        sender_type=Message.SenderType.AGENT,
        agent=request.user,
        content=content,
    )
    conversation.status = Conversation.Status.OPEN
    conversation.is_unread = False
    conversation.save(update_fields=["status", "is_unread", "updated_at"])

    _broadcast_message(message)
    return JsonResponse({"ok": True, "message_id": message.id})


@login_required
@website_required
@require_POST
def update_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": _("Invalid JSON")}, status=400)

    if "status" in data and data["status"] in Conversation.Status.values:
        conversation.status = data["status"]
    if "assigned_to" in data:
        if data["assigned_to"] is None:
            conversation.assigned_to = None
        else:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            agent = get_object_or_404(User, pk=data["assigned_to"])
            if not WebsiteAgent.objects.filter(
                website=request.website, user=agent
            ).exists():
                return JsonResponse(
                    {"error": _("Agent not on this website")}, status=400
                )
            conversation.assigned_to = agent
    if data.get("mark_read"):
        conversation.is_unread = False

    conversation.save()
    return JsonResponse({"ok": True, "status": conversation.status})
