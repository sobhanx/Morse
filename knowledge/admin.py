from django.contrib import admin

from .models import Article, Category


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
