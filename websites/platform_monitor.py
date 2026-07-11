from django.db.models import Count, Prefetch, Q

from accounts.models import User
from accounts.usage import user_usage_queryset
from inbox.models import Conversation, Message
from websites.admin import website_usage_queryset
from websites.models import Website


def get_platform_totals():
    websites = Website.objects.all()
    conversations = Conversation.unscoped.all()
    customers = User.objects.filter(owned_websites__isnull=False).distinct()
    return {
        "customers": customers.count(),
        "websites": websites.count(),
        "active_websites": websites.filter(is_active=True).count(),
        "conversations": conversations.count(),
        "open_conversations": conversations.filter(status=Conversation.Status.OPEN).count(),
        "unread_conversations": conversations.filter(is_unread=True).count(),
        "messages": Message.unscoped.count(),
    }


def get_platform_customers(search=""):
    owners = (
        user_usage_queryset(User.objects.filter(owned_websites__isnull=False))
        .distinct()
        .order_by("-date_joined")
    )
    if search:
        owners = owners.filter(
            Q(phone__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(owned_websites__name__icontains=search)
        ).distinct()
    return owners


def get_platform_websites(search=""):
    websites = website_usage_queryset(Website.objects.all()).select_related("owner")
    if search:
        websites = websites.filter(
            Q(name__icontains=search)
            | Q(domain__icontains=search)
            | Q(owner__phone__icontains=search)
            | Q(owner__username__icontains=search)
            | Q(public_widget_key__icontains=search)
        )
    return websites.order_by("-created_at")


def get_platform_conversations(search="", status="", website_id=""):
    last_message = Message.unscoped.order_by("-created_at")
    qs = (
        Conversation.unscoped.select_related(
            "contact",
            "website",
            "website__owner",
            "assigned_to",
        )
        .prefetch_related(Prefetch("messages", queryset=last_message[:1], to_attr="_latest_messages"))
        .order_by("-updated_at")
    )

    if status and status != "all":
        qs = qs.filter(status=status)
    if website_id:
        qs = qs.filter(website_id=website_id)
    if search:
        qs = qs.filter(
            Q(contact__name__icontains=search)
            | Q(contact__email__icontains=search)
            | Q(contact__visitor_id__icontains=search)
            | Q(subject__icontains=search)
            | Q(website__name__icontains=search)
            | Q(website__owner__phone__icontains=search)
            | Q(messages__content__icontains=search)
        ).distinct()

    return qs[:200]


def build_customer_rows(customers):
    rows = []
    for customer in customers:
        rows.append(
            {
                "user": customer,
                "owned_websites": customer._owned_website_count,
                "active_sites": customer._active_owned_count,
                "visitors": customer._owned_visitors,
                "conversations": customer._owned_conversations,
                "unread": customer._owned_unread,
                "agent_replies": customer._agent_messages,
                "last_activity": customer._last_owned_activity,
            }
        )
    return rows


def build_website_rows(websites):
    rows = []
    for website in websites:
        rows.append(
            {
                "website": website,
                "visitors": website._contact_count,
                "conversations": website._conversation_count,
                "messages": website._message_count,
                "unread": website._unread_count,
            }
        )
    return rows
