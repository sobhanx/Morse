from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import SmsLog, User, VerifyCode
from .usage import (
    get_user_agent_website_stats,
    get_user_assigned_conversations,
    get_user_owned_website_stats,
    user_usage_queryset,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "phone",
        "display_name",
        "owned_websites_display",
        "owned_usage_display",
        "agent_activity_display",
        "last_activity_display",
        "is_active",
        "last_login",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "valid_phone", "date_joined")
    search_fields = ("phone", "email", "first_name", "last_name", "username")
    ordering = ("-date_joined",)
    readonly_fields = ("usage_summary", "last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "username")}),
        ("Phone", {"fields": ("valid_phone",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Usage", {"fields": ("usage_summary",)}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "password1", "password2"),
            },
        ),
    )

    def get_queryset(self, request):
        return user_usage_queryset(super().get_queryset(request))

    @admin.display(description="Name")
    def display_name(self, obj):
        return obj.get_full_name() or "—"

    @admin.display(description="Owned sites", ordering="_owned_website_count")
    def owned_websites_display(self, obj):
        return format_html(
            '{} <span style="color:#666">({} active)</span>',
            obj._owned_website_count,
            obj._active_owned_count,
        )

    @admin.display(description="Platform usage (owned)", ordering="_owned_conversations")
    def owned_usage_display(self, obj):
        return format_html(
            '{} visitors · {} chats · {} msgs',
            obj._owned_visitors,
            obj._owned_conversations,
            obj._owned_messages,
        )

    @admin.display(description="Agent activity", ordering="_agent_messages")
    def agent_activity_display(self, obj):
        return format_html(
            '{} assigned · {} replies · {} sites',
            obj._assigned_conversations,
            obj._agent_messages,
            obj._member_website_count,
        )

    @admin.display(description="Last activity", ordering="_last_owned_activity")
    def last_activity_display(self, obj):
        latest = obj._last_owned_activity or obj._last_agent_activity
        if not latest:
            return "—"
        return timezone.localtime(latest).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Usage summary")
    def usage_summary(self, obj):
        if not obj.pk:
            return "Save the user first to see usage stats."

        users = user_usage_queryset(User.objects.filter(pk=obj.pk))
        user = users.first()
        owned_sites = get_user_owned_website_stats(obj)
        agent_sites = get_user_agent_website_stats(obj)
        assigned = get_user_assigned_conversations(obj, limit=10)

        owned_rows = "".join(
            format_html(
                "<tr>"
                "<td style='padding:4px 8px'><a href='{}'>{}</a></td>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "</tr>",
                f"/admin/websites/website/{site.pk}/change/",
                site.name,
                site._contact_count,
                site._conversation_count,
                site._message_count,
                "Active" if site.is_active else "Inactive",
            )
            for site in owned_sites
        ) or "<tr><td colspan='5' style='padding:4px 8px'>No owned websites.</td></tr>"

        agent_rows = "".join(
            format_html(
                "<tr>"
                "<td style='padding:4px 8px'><a href='{}'>{}</a></td>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "</tr>",
                f"/admin/websites/website/{site.pk}/change/",
                site.name,
                site._conversation_count,
                site._message_count,
                site.owner.get_full_name() or site.owner.phone,
            )
            for site in agent_sites
        ) or "<tr><td colspan='4' style='padding:4px 8px'>Not an agent on other websites.</td></tr>"

        assigned_rows = "".join(
            format_html(
                "<tr>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "<td style='padding:4px 8px'>{}</td>"
                "</tr>",
                conv.contact.display_name,
                conv.website.name,
                conv.get_status_display(),
                timezone.localtime(conv.updated_at).strftime("%Y-%m-%d %H:%M"),
            )
            for conv in assigned
        ) or "<tr><td colspan='4' style='padding:4px 8px'>No assigned conversations.</td></tr>"

        return format_html(
            "<div style='line-height:1.6'>"
            "<p><strong>Owned websites:</strong> {} total ({} active) · "
            "<strong>Visitors:</strong> {} · <strong>Conversations:</strong> {} "
            "({} unread) · <strong>Messages:</strong> {}</p>"
            "<p><strong>As agent:</strong> {} website memberships · "
            "<strong>Assigned chats:</strong> {} ({} open) · "
            "<strong>Replies sent:</strong> {} · <strong>SMS logs:</strong> {}</p>"
            "<h4 style='margin:16px 0 8px'>Owned websites breakdown</h4>"
            "<table style='border-collapse:collapse;width:100%;max-width:720px'>"
            "<thead><tr>"
            "<th align='left' style='padding:4px 8px'>Website</th>"
            "<th align='left' style='padding:4px 8px'>Visitors</th>"
            "<th align='left' style='padding:4px 8px'>Chats</th>"
            "<th align='left' style='padding:4px 8px'>Messages</th>"
            "<th align='left' style='padding:4px 8px'>Status</th>"
            "</tr></thead><tbody>{}</tbody></table>"
            "<h4 style='margin:16px 0 8px'>Agent on other websites</h4>"
            "<table style='border-collapse:collapse;width:100%;max-width:720px'>"
            "<thead><tr>"
            "<th align='left' style='padding:4px 8px'>Website</th>"
            "<th align='left' style='padding:4px 8px'>Chats</th>"
            "<th align='left' style='padding:4px 8px'>Messages</th>"
            "<th align='left' style='padding:4px 8px'>Owner</th>"
            "</tr></thead><tbody>{}</tbody></table>"
            "<h4 style='margin:16px 0 8px'>Recent assigned conversations</h4>"
            "<table style='border-collapse:collapse;width:100%;max-width:720px'>"
            "<thead><tr>"
            "<th align='left' style='padding:4px 8px'>Visitor</th>"
            "<th align='left' style='padding:4px 8px'>Website</th>"
            "<th align='left' style='padding:4px 8px'>Status</th>"
            "<th align='left' style='padding:4px 8px'>Updated</th>"
            "</tr></thead><tbody>{}</tbody></table>"
            "</div>",
            user._owned_website_count,
            user._active_owned_count,
            user._owned_visitors,
            user._owned_conversations,
            user._owned_unread,
            user._owned_messages,
            user._member_website_count,
            user._assigned_conversations,
            user._assigned_open,
            user._agent_messages,
            user._sms_sent,
            mark_safe(owned_rows),
            mark_safe(agent_rows),
            mark_safe(assigned_rows),
        )


@admin.register(VerifyCode)
class VerifyCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "code", "status", "attempts", "created_at")
    list_filter = ("subject", "status")
    search_fields = ("user__phone", "code")


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ("phone", "user", "subject", "is_sent", "status_code", "created_at")
    list_filter = ("subject", "is_sent")
    search_fields = ("phone", "user__phone")


def user_usage_dashboard(request):
    users = user_usage_queryset(User.objects.all()).order_by("-_owned_conversations", "-_agent_messages")

    usage_rows = []
    for user in users:
        usage_rows.append(
            {
                "user": user,
                "owned_websites": user._owned_website_count,
                "active_sites": user._active_owned_count,
                "visitors": user._owned_visitors,
                "conversations": user._owned_conversations,
                "unread": user._owned_unread,
                "messages": user._owned_messages,
                "agent_sites": user._member_website_count,
                "assigned": user._assigned_conversations,
                "replies": user._agent_messages,
                "last_activity": user._last_owned_activity or user._last_agent_activity,
            }
        )

    totals = {
        "users": users.count(),
        "active_users": users.filter(is_active=True).count(),
        "owned_websites": sum(row["owned_websites"] for row in usage_rows),
        "visitors": sum(row["visitors"] for row in usage_rows),
        "conversations": sum(row["conversations"] for row in usage_rows),
        "messages": sum(row["messages"] for row in usage_rows),
        "agent_replies": sum(row["replies"] for row in usage_rows),
    }

    context = {
        **admin.site.each_context(request),
        "title": "User usage",
        "usage_rows": usage_rows,
        "totals": totals,
        "opts": User._meta,
    }
    return TemplateResponse(request, "admin/accounts/user_usage_dashboard.html", context)
