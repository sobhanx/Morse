"""Shared queryset helpers for website usage stats (admin + platform monitor)."""

from django.db.models import Count, Max, Q

from morse.models import Conversation, Website


def website_usage_queryset(queryset=None):
    qs = queryset if queryset is not None else Website.objects.all()
    return qs.annotate(
        _contact_count=Count("contacts", distinct=True),
        _conversation_count=Count("conversations", distinct=True),
        _message_count=Count("conversations__messages", distinct=True),
        _agent_count=Count("agents", distinct=True),
        _article_count=Count("articles", distinct=True),
        _category_count=Count("categorys", distinct=True),
        _unread_count=Count(
            "conversations",
            filter=Q(conversations__is_unread=True),
            distinct=True,
        ),
        _open_count=Count(
            "conversations",
            filter=Q(conversations__status=Conversation.Status.OPEN),
            distinct=True,
        ),
        _resolved_count=Count(
            "conversations",
            filter=Q(conversations__status=Conversation.Status.RESOLVED),
            distinct=True,
        ),
        _last_activity=Max("conversations__updated_at"),
    ).select_related("owner")
