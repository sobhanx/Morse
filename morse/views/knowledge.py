from contextlib import contextmanager

from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from morse.permissions import (
    get_demo_website,
    get_widget_key_from_request,
    resolve_website_by_widget_key,
)
from morse.tenant import reset_current_website, set_current_website

from morse.models import Article, Category
from morse.localization import (
    filter_localized_articles,
    localize_article,
    localize_categories,
)


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
        raise Http404(_("Help center is not available yet"))

    query = request.GET.get("q", "").strip()
    with _website_context(website):
        published_articles = Prefetch(
            "articles",
            queryset=Article.unscoped.filter(is_published=True).order_by("-updated_at"),
        )
        if query:
            articles = filter_localized_articles(
                Article.objects.filter(is_published=True).select_related("category"),
                website,
                query,
            )
        else:
            articles = []

        categories = localize_categories(
            Category.objects.prefetch_related(published_articles).all(),
            website,
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
        raise Http404(_("Help center is not available yet"))

    with _website_context(website):
        article = get_object_or_404(
            Article, slug=slug, is_published=True, website=website
        )
        article = localize_article(article)
        article.views += 1
        article.save(update_fields=["views"])
        return render(
            request,
            "knowledge/article_detail.html",
            {
                "article": article,
                "website": website,
                "widget_key": website.public_widget_key,
            },
        )
