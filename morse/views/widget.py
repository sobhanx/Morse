import json
import uuid

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from morse.models import Contact, Conversation, Message
from morse.views.inbox import _broadcast_message
from morse.permissions import (
    get_demo_website,
    get_widget_key_from_request,
    is_public_showcase_path,
    resolve_website_by_widget_key,
)


def _require_website(request):
    key = get_widget_key_from_request(request)
    website = resolve_website_by_widget_key(key) if key else None
    if website is None:
        website = request.website
    if website is None and is_public_showcase_path(request.path):
        website = get_demo_website()
    if website is None:
        raise Http404(_("Invalid or missing widget key"))
    return website


def _session_key(website):
    return f"visitor_session_{website.id}"


def _parse_visitor_uuid(raw):
    """Parse a client-supplied visitor UUID (maps to Contact.session_id)."""
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _get_visitor_id_from_request(request):
    """
    Resolve the persistent anonymous visitor id from the request.

    Accepted sources (first match wins):
    - Query string: ?visitor_id=<uuid>
    - Header: X-Visitor-Id
    - Cookie: morse_vid_<widget_key>
    - JSON body: { "visitor_id": "<uuid>" }
    - Multipart/form: visitor_id=<uuid>
    """
    raw = request.GET.get("visitor_id") or request.META.get("HTTP_X_VISITOR_ID")
    if raw:
        return _parse_visitor_uuid(raw)

    widget_key = get_widget_key_from_request(request)
    if widget_key:
        cookie_name = "morse_vid_" + "".join(
            ch if ch.isalnum() or ch in "-_" else "" for ch in widget_key
        )
        cookie_value = request.COOKIES.get(cookie_name)
        parsed = _parse_visitor_uuid(cookie_value)
        if parsed:
            return parsed

    if request.method == "POST":
        form_value = request.POST.get("visitor_id")
        if form_value:
            return _parse_visitor_uuid(form_value)

        content_type = (request.META.get("CONTENT_TYPE") or "").lower()
        if "application/json" in content_type and request.body:
            try:
                data = json.loads(request.body)
            except (json.JSONDecodeError, TypeError, ValueError):
                data = None
            if isinstance(data, dict) and data.get("visitor_id"):
                return _parse_visitor_uuid(data.get("visitor_id"))

    return None


def _get_or_create_contact(request, website, *, create=True):
    """
    Resolve the anonymous visitor Contact for this website.

    Priority:
    1. Persistent visitor_id from the client (localStorage UUID → Contact.session_id)
    2. Django session cookie fallback (legacy / same-tab continuity)
    3. Optionally create a new Contact (chat bootstrap only)
    """
    session_key = _session_key(website)
    contact = None

    client_id = _get_visitor_id_from_request(request)
    if client_id:
        try:
            contact = Contact.objects.get(session_id=client_id, website=website)
        except Contact.DoesNotExist:
            if create:
                # First request with a newly generated client UUID — create Contact
                # using that UUID as the stable identity.
                contact = Contact.objects.create(website=website, session_id=client_id)

    if not contact:
        session_id = request.session.get(session_key)
        if session_id:
            try:
                contact = Contact.objects.get(session_id=session_id, website=website)
            except (Contact.DoesNotExist, ValueError):
                contact = None

    if not contact and create:
        contact = Contact.objects.create(website=website)

    if contact:
        request.session[session_key] = str(contact.session_id)
    return contact


def _contact_owns_conversation(contact, conversation):
    return (
        contact is not None
        and conversation.contact_id == contact.id
        and conversation.website_id == contact.website_id
    )


@xframe_options_exempt
@require_GET
def chat_widget(request):
    website = _require_website(request)
    widget_key = website.public_widget_key

    # Require a client visitor_id before creating/loading a Contact, so the first
    # HTML response does not mint an orphan identity. The bootstrap page writes
    # localStorage and redirects with ?visitor_id=...
    if not _get_visitor_id_from_request(request):
        return render(
            request,
            "widget/chat_bootstrap.html",
            {"widget_key": widget_key},
        )

    contact = _get_or_create_contact(request, website)
    conversation = (
        Conversation.objects.filter(contact=contact, website=website)
        .order_by("-updated_at")
        .first()
    )
    if not conversation:
        conversation = Conversation.objects.create(
            contact=contact, website=website
        )
    messages = conversation.messages.all()
    telegram_deep_link = contact.get_telegram_deep_link()
    return render(
        request,
        "widget/chat.html",
        {
            "contact": contact,
            "conversation": conversation,
            "messages": messages,
            "website": website,
            "widget_key": widget_key,
            "telegram_deep_link": telegram_deep_link,
        },
    )


@require_GET
def embed_script(request):
    website = _require_website(request)
    return render(
        request,
        "widget/embed.js",
        {"widget_key": website.public_widget_key},
        content_type="application/javascript; charset=utf-8",
    )


@require_GET
def demo_page(request):
    website = _require_website(request)
    return render(request, "widget/demo.html", {"website": website})


@require_GET
def demo_pricing(request):
    website = _require_website(request)
    return render(request, "widget/demo_pricing.html", {"website": website})


@csrf_exempt
@require_POST
def start_conversation(request):
    website = _require_website(request)
    contact = _get_or_create_contact(request, website)
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    if data.get("name"):
        contact.name = data["name"]
    if data.get("email"):
        contact.email = data["email"]
    contact.save()

    conversation = Conversation.objects.create(
        contact=contact,
        website=website,
        subject=data.get("subject", ""),
    )

    greeting = Message.objects.create(
        conversation=conversation,
        website=website,
        sender_type=Message.SenderType.SYSTEM,
        content=_(
            "Thanks for reaching out! A support agent will be with you shortly."
        ),
    )

    return JsonResponse(
        {
            "conversation_id": conversation.id,
            "contact_id": str(contact.session_id),
            # Stable anonymous identity (UUID stored in localStorage as morse_visitor_id)
            "persistent_visitor_id": str(contact.session_id),
            # Short public display code shown in the widget footer / inbox
            "visitor_id": contact.visitor_id,
            "greeting": {
                "content": greeting.content,
                "sender_type": greeting.sender_type,
                "created_at": greeting.created_at.isoformat(),
            },
        }
    )


@csrf_exempt
@require_POST
def update_contact(request):
    website = _require_website(request)
    contact = _get_or_create_contact(request, website)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": _("Invalid JSON")}, status=400)

    for field in ("name", "email", "phone", "company"):
        if field in data:
            setattr(contact, field, data[field])
    contact.save()
    return JsonResponse({"ok": True, "persistent_visitor_id": str(contact.session_id)})


@csrf_exempt
@require_POST
def send_message(request, conversation_id):
    website = _require_website(request)
    contact = _get_or_create_contact(request, website, create=False)
    try:
        conversation = Conversation.unscoped.get(
            pk=conversation_id, website=website
        )
    except Conversation.DoesNotExist:
        return JsonResponse({"error": _("Conversation not found")}, status=404)

    if not contact or not _contact_owns_conversation(contact, conversation):
        return JsonResponse({"error": _("Conversation not found")}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": _("Invalid JSON")}, status=400)

    content = data.get("content", "").strip()
    if not content:
        return JsonResponse({"error": _("Message cannot be empty")}, status=400)

    message = Message.unscoped.create(
        conversation=conversation,
        website=website,
        sender_type=Message.SenderType.VISITOR,
        content=content,
    )
    conversation.is_unread = True
    conversation.status = Conversation.Status.OPEN
    conversation.save(update_fields=["is_unread", "status", "updated_at"])

    _broadcast_message(message)
    return JsonResponse(
        {
            "ok": True,
            "message": message.to_payload(),
        }
    )


@csrf_exempt
@require_POST
def send_voice_message(request, conversation_id):
    website = _require_website(request)
    contact = _get_or_create_contact(request, website, create=False)
    try:
        conversation = Conversation.unscoped.get(
            pk=conversation_id, website=website
        )
    except Conversation.DoesNotExist:
        return JsonResponse({"error": _("Conversation not found")}, status=404)

    if not contact or not _contact_owns_conversation(contact, conversation):
        return JsonResponse({"error": _("Conversation not found")}, status=404)

    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": _("Audio file is required")}, status=400)

    if audio_file.size > Message.MAX_VOICE_BYTES:
        return JsonResponse(
            {"error": _("Voice message is too large (max 5 MB)")},
            status=400,
        )

    content_type = (getattr(audio_file, "content_type", "") or "").split(";")[0].strip()
    # Some browsers omit or use generic types; allow empty/octet-stream with audio extension.
    name = (getattr(audio_file, "name", "") or "").lower()
    has_audio_ext = name.endswith(
        (".webm", ".ogg", ".mp3", ".mp4", ".m4a", ".wav", ".aac")
    )
    if content_type and content_type not in Message.ALLOWED_AUDIO_TYPES:
        if content_type not in ("application/octet-stream",) or not has_audio_ext:
            return JsonResponse(
                {"error": _("Unsupported audio format")},
                status=400,
            )

    try:
        duration = int(request.POST.get("duration_seconds") or 0)
    except (TypeError, ValueError):
        duration = 0
    if duration < 1:
        duration = 1
    if duration > Message.MAX_VOICE_SECONDS:
        return JsonResponse(
            {
                "error": _("Voice messages cannot exceed %(seconds)s seconds")
                % {"seconds": Message.MAX_VOICE_SECONDS}
            },
            status=400,
        )

    message = Message.unscoped.create(
        conversation=conversation,
        website=website,
        sender_type=Message.SenderType.VISITOR,
        message_type=Message.MessageType.AUDIO,
        content=_("Voice message"),
        audio=audio_file,
        duration_seconds=duration,
    )
    conversation.is_unread = True
    conversation.status = Conversation.Status.OPEN
    conversation.save(update_fields=["is_unread", "status", "updated_at"])

    _broadcast_message(message)
    return JsonResponse(
        {
            "ok": True,
            "message": message.to_payload(),
        }
    )
