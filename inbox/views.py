import json
import os

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from websites.models import WebsiteAgent
from websites.permissions import (
    get_widget_key_from_request,
    resolve_website_by_widget_key,
    user_can_access_website,
    website_required,
)

from .models import Conversation, Message

AUDIO_MIME_BY_EXT = {
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".mp4": "audio/mp4",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
}


def audio_content_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    return AUDIO_MIME_BY_EXT.get(ext, "application/octet-stream")


def _can_access_message_audio(request, message):
    if request.user.is_authenticated and user_can_access_website(
        request.user, message.website
    ):
        return True

    # Persistent anonymous visitor id (localStorage UUID → Contact.session_id)
    visitor_raw = request.GET.get("visitor_id") or request.META.get("HTTP_X_VISITOR_ID")
    if visitor_raw:
        try:
            if str(message.conversation.contact.session_id) == str(visitor_raw).strip():
                return True
        except Exception:
            pass

    key = get_widget_key_from_request(request)
    website = resolve_website_by_widget_key(key, require_active=False)
    if website and website.id == message.website_id:
        return True

    session_key = f"visitor_session_{message.website_id}"
    session_id = request.session.get(session_key)
    if session_id and str(message.conversation.contact.session_id) == str(session_id):
        return True

    return False


@require_GET
def serve_message_audio(request, message_id):
    message = get_object_or_404(
        Message.unscoped.select_related(
            "conversation",
            "conversation__contact",
            "website",
        ),
        pk=message_id,
    )
    if not message.audio or message.message_type != Message.MessageType.AUDIO:
        raise Http404

    if not _can_access_message_audio(request, message):
        raise Http404

    content_type = audio_content_type(message.audio.name)
    response = FileResponse(
        message.audio.open("rb"),
        content_type=content_type,
    )
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, max-age=3600"
    return response


def _broadcast_message(message):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    payload = {
        "type": "chat.message",
        "message": message.to_payload(),
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
    return JsonResponse({"ok": True, "message": message.to_payload()})


@login_required
@website_required
@require_GET
def conversation_messages(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    messages = conversation.messages.order_by("created_at")
    since = request.GET.get("since")
    if since:
        try:
            messages = messages.filter(id__gt=int(since))
        except (TypeError, ValueError):
            pass
    return JsonResponse(
        {"messages": [message.to_payload() for message in messages]}
    )


@login_required
@website_required
@require_GET
def conversations_feed(request):
    status_filter = request.GET.get("status", "all")
    search = request.GET.get("q", "").strip()
    conversations = Conversation.objects.select_related("contact", "assigned_to")
    if status_filter != "all":
        conversations = conversations.filter(status=status_filter)
    if search:
        from django.db.models import Q

        conversations = conversations.filter(
            Q(contact__name__icontains=search)
            | Q(contact__email__icontains=search)
            | Q(contact__visitor_id__icontains=search)
            | Q(subject__icontains=search)
        )
    payload = []
    for conversation in conversations[:100]:
        payload.append(
            {
                "id": conversation.id,
                "preview": str(conversation.preview),
                "is_unread": conversation.is_unread,
                "status": conversation.status,
                "updated_at": conversation.updated_at.isoformat(),
                "contact_name": conversation.contact.display_name,
                "visitor_id": conversation.contact.visitor_id,
            }
        )
    return JsonResponse({"conversations": payload})


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
