from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Article, Category


def _require_website(request):
    if not request.website:
        raise Http404("Invalid or missing widget key")
    return request.website


@require_GET
def help_center(request):
    website = _require_website(request)
    query = request.GET.get("q", "").strip()
    categories = Category.objects.prefetch_related("articles").all()
    articles = Article.objects.filter(is_published=True).select_related("category")

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
    website = _require_website(request)
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
