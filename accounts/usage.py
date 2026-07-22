from django.db.models import Count, Max, Q

from inbox.models import Conversation, Message


def user_usage_queryset(queryset=None):
    from accounts.models import User

    qs = queryset if queryset is not None else User.objects.all()
    return qs.annotate(
        _owned_website_count=Count("owned_websites", distinct=True),
        _active_owned_count=Count(
            "owned_websites",
            filter=Q(owned_websites__is_active=True),
            distinct=True,
        ),
        _member_website_count=Count("website_memberships", distinct=True),
        _owned_visitors=Count("owned_websites__contacts", distinct=True),
        _owned_conversations=Count("owned_websites__conversations", distinct=True),
        _owned_messages=Count("owned_websites__conversations__messages", distinct=True),
        _owned_unread=Count(
            "owned_websites__conversations",
            filter=Q(owned_websites__conversations__is_unread=True),
            distinct=True,
        ),
        _assigned_conversations=Count("assigned_conversations", distinct=True),
        _assigned_open=Count(
            "assigned_conversations",
            filter=Q(assigned_conversations__status=Conversation.Status.OPEN),
            distinct=True,
        ),
        _agent_messages=Count(
            "messages",
            filter=Q(messages__sender_type=Message.SenderType.AGENT),
            distinct=True,
        ),
        _sms_sent=Count("smslog", distinct=True),
        _last_owned_activity=Max("owned_websites__conversations__updated_at"),
        _last_agent_activity=Max("messages__created_at"),
    )


def get_user_owned_website_stats(user):
    from morse.models import Website
    from morse.usage import website_usage_queryset

    return website_usage_queryset(Website.objects.filter(owner=user)).order_by(
        "-_conversation_count"
    )


def get_user_agent_website_stats(user):
    from morse.models import Website
    from morse.usage import website_usage_queryset

    return website_usage_queryset(
        Website.objects.filter(agents__user=user).exclude(owner=user)
    ).order_by("-_conversation_count")


def get_user_assigned_conversations(user, limit=20):
    return (
        Conversation.unscoped.filter(assigned_to=user)
        .select_related("contact", "website")
        .order_by("-updated_at")[:limit]
    )
