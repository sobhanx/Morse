"""Django admin for all Morse domain models (legacy app_labels preserved)."""

from django.contrib import admin
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html

from morse.models import (
    Article,
    Category,
    Contact,
    Conversation,
    Message,
    Website,
    WebsiteAgent,
)
from morse.usage import website_usage_queryset


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


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "email",
        "company",
        "telegram_username",
        "telegram_linked_at",
        "created_at",
    )
    list_filter = ("telegram_linked_at",)
    search_fields = (
        "name",
        "email",
        "company",
        "visitor_id",
        "telegram_username",
        "telegram_user_id",
    )
    exclude = ("telegram_link_token",)
    readonly_fields = (
        "session_id",
        "visitor_id",
        "telegram_chat_id",
        "telegram_user_id",
        "telegram_username",
        "telegram_linked_at",
        "created_at",
        "updated_at",
    )


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("contact", "status", "assigned_to", "is_unread", "updated_at")
    list_filter = ("status", "is_unread")
    search_fields = ("contact__name", "contact__email", "subject")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender_type", "content", "created_at")
    list_filter = ("sender_type",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "order")
    list_filter = ("website",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("website",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "website", "is_published", "views", "updated_at")
    list_filter = ("website", "category", "is_published")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("website", "category")


def website_usage_dashboard(request):
    websites = website_usage_queryset(Website.objects.all()).order_by(
        "-_conversation_count", "name"
    )

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
