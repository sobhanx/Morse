from django.utils.translation import get_language

from morse.constants import DEMO_DOMAIN

from .demo_content import DEMO_KB
from morse.models import Article


def _language_code():
    return (get_language() or "fa")[:2]


def is_demo_knowledge_website(website):
    return website is not None and website.domain == DEMO_DOMAIN


def localize_category(category, language=None):
    if language is None:
        language = _language_code()
    data = DEMO_KB.get(category.slug, {}).get(language)
    if not data:
        return category
    category.name = data["name"]
    category.description = data["description"]
    return category


def localize_article(article, language=None):
    if language is None:
        language = _language_code()
    category_data = DEMO_KB.get(article.category.slug, {}).get(language, {})
    article_data = category_data.get("articles", {}).get(article.slug)
    if not article_data:
        return article
    article.title = article_data["title"]
    article.content = article_data["content"]
    return article


def localize_categories(categories, website, language=None):
    if not is_demo_knowledge_website(website):
        return list(categories)
    if language is None:
        language = _language_code()
    result = []
    for category in categories:
        cat = localize_category(category, language)
        # Use unscoped related articles so tenant context cannot empty the list.
        articles = []
        for article in Article.unscoped.filter(
            category_id=category.id, is_published=True
        ):
            articles.append(localize_article(article, language))
        cat._prefetched_objects_cache = {"articles": articles}
        result.append(cat)
    return result


def localize_articles(articles, website, language=None):
    if not is_demo_knowledge_website(website):
        return list(articles)
    if language is None:
        language = _language_code()
    return [localize_article(article, language) for article in articles]


def filter_localized_articles(articles, website, query, language=None):
    if not query:
        return localize_articles(articles, website, language)
    if language is None:
        language = _language_code()
    query_lower = query.lower()
    matches = []
    for article in articles:
        localized = localize_article(article, language)
        if (
            query_lower in localized.title.lower()
            or query_lower in localized.content.lower()
            or query_lower in article.title.lower()
            or query_lower in article.content.lower()
        ):
            matches.append(localized)
    return matches
