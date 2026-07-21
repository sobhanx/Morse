from django.contrib import admin

from .models import Contact


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
    # Never expose telegram_link_token on list or detail admin pages.
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
