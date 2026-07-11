from django.contrib import admin

from .models import Conversation, Message


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
