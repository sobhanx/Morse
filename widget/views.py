import json

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from contacts.models import Contact
from inbox.models import Conversation, Message
from inbox.views import _broadcast_message
from websites.permissions import (
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
        raise Http404("Invalid or missing widget key")
    return website


def _session_key(website):
    return f"visitor_session_{website.id}"


def _get_or_create_contact(request, website):
    session_key = _session_key(website)
    session_id = request.session.get(session_key)
    contact = None
    if session_id:
        try:
            contact = Contact.objects.get(session_id=session_id, website=website)
        except (Contact.DoesNotExist, ValueError):
            contact = None
    if not contact:
        contact = Contact.objects.create(website=website)
        request.session[session_key] = str(contact.session_id)
    return contact


@xframe_options_exempt
@require_GET
def chat_widget(request):
    website = _require_website(request)
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
    widget_key = website.public_widget_key
    return render(
        request,
        "widget/chat.html",
        {
            "contact": contact,
            "conversation": conversation,
            "messages": messages,
            "website": website,
            "widget_key": widget_key,
        },
    )


@require_GET
def embed_script(request):
    website = _require_website(request)
    return render(
        request,
        "widget/embed.js",
        {"widget_key": website.public_widget_key},
        content_type="application/javascript",
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
        content="Thanks for reaching out! A support agent will be with you shortly.",
    )

    return JsonResponse(
        {
            "conversation_id": conversation.id,
            "contact_id": str(contact.session_id),
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
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    for field in ("name", "email", "phone", "company"):
        if field in data:
            setattr(contact, field, data[field])
    contact.save()
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def send_message(request, conversation_id):
    website = _require_website(request)
    try:
        conversation = Conversation.unscoped.get(
            pk=conversation_id, website=website
        )
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "Conversation not found"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    content = data.get("content", "").strip()
    if not content:
        return JsonResponse({"error": "Message cannot be empty"}, status=400)

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
            "message": {
                "id": message.id,
                "content": message.content,
                "sender_type": message.sender_type,
                "sender_name": message.sender_name,
                "created_at": message.created_at.isoformat(),
            },
        }
    )
