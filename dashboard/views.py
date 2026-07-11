from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from contacts.models import Contact
from inbox.models import Conversation, Message
from websites.models import WebsiteAgent
from websites.permissions import (
    get_accessible_websites,
    get_demo_website,
    set_active_website,
    website_required,
)

User = get_user_model()


def _ensure_active_website(request):
    if request.website:
        return None
    websites = get_accessible_websites(request.user)
    if websites.count() == 1:
        set_active_website(request, websites.first())
        return redirect(request.get_full_path())
    return redirect("websites:list")


@login_required
def inbox(request):
    redirect_response = _ensure_active_website(request)
    if redirect_response:
        return redirect_response
    if not request.website:
        return redirect("websites:list")

    status_filter = request.GET.get("status", "all")
    search = request.GET.get("q", "").strip()

    conversations = Conversation.objects.select_related(
        "contact", "assigned_to"
    ).prefetch_related("messages")

    if status_filter != "all":
        conversations = conversations.filter(status=status_filter)
    if search:
        conversations = conversations.filter(
            Q(contact__name__icontains=search)
            | Q(contact__email__icontains=search)
            | Q(contact__visitor_id__icontains=search)
            | Q(subject__icontains=search)
        )

    stats = {
        "total": conversations.count(),
        "open": conversations.filter(status=Conversation.Status.OPEN).count(),
        "pending": conversations.filter(status=Conversation.Status.PENDING).count(),
        "unread": conversations.filter(is_unread=True).count(),
    }

    active_id = request.GET.get("conversation")
    active_conversation = None
    messages = []
    if active_id:
        active_conversation = get_object_or_404(Conversation, pk=active_id)
        active_conversation.is_unread = False
        active_conversation.save(update_fields=["is_unread"])
        messages = active_conversation.messages.select_related("agent")
    elif conversations.exists():
        active_conversation = conversations.first()
        active_conversation.is_unread = False
        active_conversation.save(update_fields=["is_unread"])
        messages = active_conversation.messages.select_related("agent")

    agent_ids = WebsiteAgent.objects.filter(
        website=request.website
    ).values_list("user_id", flat=True)
    agents = User.objects.filter(id__in=agent_ids)

    return render(
        request,
        "dashboard/inbox.html",
        {
            "conversations": conversations,
            "active_conversation": active_conversation,
            "messages": messages,
            "stats": stats,
            "status_filter": status_filter,
            "search": search,
            "agents": agents,
        },
    )


@login_required
@website_required
def contacts_list(request):
    search = request.GET.get("q", "").strip()
    contacts = Contact.objects.annotate(conversation_count=Count("conversations"))
    if search:
        contacts = contacts.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(company__icontains=search)
            | Q(visitor_id__icontains=search)
        )
    return render(
        request,
        "dashboard/contacts.html",
        {"contacts": contacts, "search": search},
    )


@login_required
@website_required
def contact_detail(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    conversations = contact.conversations.prefetch_related("messages")
    return render(
        request,
        "dashboard/contact_detail.html",
        {"contact": contact, "conversations": conversations},
    )


@login_required
@website_required
@require_POST
def update_contact_notes(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    contact.notes = request.POST.get("notes", "")
    contact.save(update_fields=["notes", "updated_at"])
    return redirect("dashboard:contact_detail", contact_id=contact.pk)


@login_required
@website_required
def analytics(request):
    total_conversations = Conversation.objects.count()
    total_messages = Message.objects.count()
    total_contacts = Contact.objects.count()
    resolved = Conversation.objects.filter(
        status=Conversation.Status.RESOLVED
    ).count()

    resolution_rate = (
        round(resolved / total_conversations * 100, 1) if total_conversations else 0
    )

    recent_conversations = Conversation.objects.select_related("contact").order_by(
        "-created_at"
    )[:10]

    return render(
        request,
        "dashboard/analytics.html",
        {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_contacts": total_contacts,
            "resolved": resolved,
            "resolution_rate": resolution_rate,
            "recent_conversations": recent_conversations,
        },
    )


@require_GET
def landing(request):
    if request.user.is_authenticated:
        websites = get_accessible_websites(request.user)
        if not websites.exists():
            return redirect("websites:list")
        active_id = request.session.get("active_website_id")
        website = None
        if active_id:
            website = websites.filter(pk=active_id).first()
        if not website:
            website = websites.first()
            set_active_website(request, website)
        if website.owner_id == request.user.id and not website.is_active:
            return redirect("websites:activate", website_id=website.id)
        return redirect("dashboard:inbox")
    return render(
        request,
        "dashboard/landing.html",
        {"demo_website": get_demo_website()},
    )
