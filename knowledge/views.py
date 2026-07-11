from contextlib import contextmanager

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from websites.permissions import (
    get_demo_website,
    get_widget_key_from_request,
    resolve_website_by_widget_key,
)
from websites.tenant import reset_current_website, set_current_website

from .models import Article, Category


def _resolve_website(request):
    key = get_widget_key_from_request(request)
    website = resolve_website_by_widget_key(key) if key else None
    if website is None:
        website = request.website or get_demo_website()
    return website


@contextmanager
def _website_context(website):
    token = set_current_website(website)
    try:
        yield
    finally:
        reset_current_website(token)


@require_GET
def help_center(request):
    website = _resolve_website(request)
    if website is None:
        raise Http404("Help center is not available yet")

    query = request.GET.get("q", "").strip()
    with _website_context(website):
        categories = Category.objects.prefetch_related("articles").all()
        articles = Article.objects.filter(is_published=True).select_related(
            "category"
        )

        if query:
            articles = articles.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            )

        return render(
            request,
            "knowledge/help_center.html",
            {
                "categories": categories,
                "articles": articles,
                "query": query,
                "website": website,
                "widget_key": website.public_widget_key,
            },
        )


@require_GET
def article_detail(request, slug):
    website = _resolve_website(request)
    if website is None:
        raise Http404("Help center is not available yet")

    with _website_context(website):
        article = get_object_or_404(
            Article, slug=slug, is_published=True, website=website
        )
        article.views += 1
        article.save(update_fields=["views"])
        return render(
            request,
            "knowledge/article_detail.html",
            {
                "article": article,
                "widget_key": website.public_widget_key,
            },
        )
