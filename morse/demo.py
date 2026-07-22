from django.contrib.auth import get_user_model
from django.utils.translation import gettext

from morse.demo_content import DEMO_KB
from morse.models import Article, Category, Website, WebsiteAgent
from morse.permissions import DEMO_DOMAIN

User = get_user_model()


def localized_website_name(website):
    if website is not None and website.domain == DEMO_DOMAIN:
        return gettext("Demo Website")
    return website.name if website else ""


def _seed_knowledge_base(website):
    for category_slug, translations in DEMO_KB.items():
        fa_data = translations["fa"]
        category, _ = Category.unscoped.update_or_create(
            website=website,
            slug=category_slug,
            defaults={
                "name": fa_data["name"],
                "description": fa_data["description"],
            },
        )
        for article_slug, article_data in fa_data["articles"].items():
            Article.unscoped.update_or_create(
                website=website,
                slug=article_slug,
                defaults={
                    "title": article_data["title"],
                    "content": article_data["content"],
                    "category": category,
                    "is_published": True,
                },
            )


def ensure_demo_website():
    """Create or repair the public demo tenant used by Help Center and Live Demo."""
    website = Website.objects.filter(domain=DEMO_DOMAIN).first()
    if website:
        changed = False
        if not website.is_active:
            website.is_active = True
            changed = True
        if website.name != "Demo Website":
            website.name = "Demo Website"
            changed = True
        if changed:
            website.save()
        _seed_knowledge_base(website)
        return website

    owner = User.objects.filter(is_superuser=True).order_by("id").first()
    if owner is None:
        owner = User.objects.order_by("id").first()
    if owner is None:
        return None

    website = Website.objects.create(
        domain=DEMO_DOMAIN,
        name="Demo Website",
        owner=owner,
        is_active=True,
    )
    WebsiteAgent.objects.get_or_create(website=website, user=owner)
    _seed_knowledge_base(website)
    return website
