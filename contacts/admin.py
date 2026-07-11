from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("display_name", "email", "company", "created_at")
    search_fields = ("name", "email", "company")
    readonly_fields = ("session_id", "created_at", "updated_at")
