from django.contrib import admin
from django.db.models import Count, Max, Q
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.utils import timezone

from inbox.models import Conversation
from .models import Website, WebsiteAgent


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


class WebsiteAgentInline(admin.TabularInline):
    model = WebsiteAgent
    extra = 0


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "domain",
        "owner_link",
        "status_badge",
        "visitors_display",
        "conversations_display",
        "messages_display",
        "agents_display",
        "articles_display",
        "unread_display",
        "last_activity_display",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "domain", "public_widget_key", "owner__phone", "owner__username")
    readonly_fields = (
        "id",
        "public_widget_key",
        "private_api_key",
        "created_at",
        "activated_at",
        "usage_summary",
    )
    inlines = [WebsiteAgentInline]
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("name", "domain", "owner", "is_active", "activated_at")}),
        ("Usage", {"fields": ("usage_summary",)}),
        (
            "API keys",
            {
                "fields": ("id", "public_widget_key", "private_api_key", "created_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return website_usage_queryset(super().get_queryset(request))

    @admin.display(description="Owner", ordering="owner__phone")
    def owner_link(self, obj):
        owner = obj.owner
        label = owner.get_full_name() or owner.phone or owner.username
        return format_html('<a href="{}">{}</a>', f"/admin/accounts/user/{owner.pk}/change/", label)

    @admin.display(description="Status", ordering="is_active")
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#0a7a3e;font-weight:600">Active</span>')
        return format_html('<span style="color:#9a6700;font-weight:600">Inactive</span>')

    @admin.display(description="Visitors", ordering="_contact_count")
    def visitors_display(self, obj):
        return obj._contact_count

    @admin.display(description="Conversations", ordering="_conversation_count")
    def conversations_display(self, obj):
        return format_html(
            '{} <span style="color:#666">({} open / {} resolved)</span>',
            obj._conversation_count,
            obj._open_count,
            obj._resolved_count,
        )

    @admin.display(description="Messages", ordering="_message_count")
    def messages_display(self, obj):
        return obj._message_count

    @admin.display(description="Agents", ordering="_agent_count")
    def agents_display(self, obj):
        return obj._agent_count

    @admin.display(description="KB articles", ordering="_article_count")
    def articles_display(self, obj):
        return format_html(
            '{} <span style="color:#666">({} categories)</span>',
            obj._article_count,
            obj._category_count,
        )

    @admin.display(description="Unread", ordering="_unread_count")
    def unread_display(self, obj):
        if obj._unread_count:
            return format_html('<strong style="color:#c62828">{}</strong>', obj._unread_count)
        return "0"

    @admin.display(description="Last activity", ordering="_last_activity")
    def last_activity_display(self, obj):
        if not obj._last_activity:
            return "—"
        return timezone.localtime(obj._last_activity).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Usage summary")
    def usage_summary(self, obj):
        if not obj.pk:
            return "Save the website first to see usage stats."

        websites = website_usage_queryset(Website.objects.filter(pk=obj.pk))
        site = websites.first()
        return format_html(
            "<table style='border-collapse:collapse'>"
            "<tr><td style='padding:4px 16px 4px 0'><strong>Visitors</strong></td><td>{}</td></tr>"
            "<tr><td style='padding:4px 16px 4px 0'><strong>Conversations</strong></td><td>{} total "
            "({} open, {} resolved, {} unread)</td></tr>"
            "<tr><td style='padding:4px 16px 4px 0'><strong>Messages</strong></td><td>{}</td></tr>"
            "<tr><td style='padding:4px 16px 4px 0'><strong>Agents</strong></td><td>{}</td></tr>"
            "<tr><td style='padding:4px 16px 4px 0'><strong>Knowledge base</strong></td><td>{} articles "
            "in {} categories</td></tr>"
            "<tr><td style='padding:4px 16px 4px 0'><strong>Last activity</strong></td><td>{}</td></tr>"
            "</table>",
            site._contact_count,
            site._conversation_count,
            site._open_count,
            site._resolved_count,
            site._unread_count,
            site._message_count,
            site._agent_count,
            site._article_count,
            site._category_count,
            timezone.localtime(site._last_activity).strftime("%Y-%m-%d %H:%M")
            if site._last_activity
            else "—",
        )


@admin.register(WebsiteAgent)
class WebsiteAgentAdmin(admin.ModelAdmin):
    list_display = ("website", "user", "created_at")
    list_filter = ("website",)
    search_fields = ("website__name", "user__phone", "user__username")


def website_usage_dashboard(request):
    websites = website_usage_queryset(Website.objects.all()).order_by("-_conversation_count", "name")

    usage_rows = []
    for website in websites:
        usage_rows.append(
            {
                "website": website,
                "visitors": website._contact_count,
                "conversations": website._conversation_count,
                "open_count": website._open_count,
                "resolved_count": website._resolved_count,
                "unread": website._unread_count,
                "messages": website._message_count,
                "agents": website._agent_count,
                "articles": website._article_count,
                "last_activity": website._last_activity,
            }
        )

    totals = {
        "websites": websites.count(),
        "active_websites": websites.filter(is_active=True).count(),
        "contacts": sum(row["visitors"] for row in usage_rows),
        "conversations": sum(row["conversations"] for row in usage_rows),
        "messages": sum(row["messages"] for row in usage_rows),
        "agents": sum(row["agents"] for row in usage_rows),
        "articles": sum(row["articles"] for row in usage_rows),
        "unread": sum(row["unread"] for row in usage_rows),
    }

    context = {
        **admin.site.each_context(request),
        "title": "Website usage",
        "usage_rows": usage_rows,
        "totals": totals,
        "opts": Website._meta,
    }
    return TemplateResponse(request, "admin/websites/usage_dashboard.html", context)
