from django.contrib.auth import get_user_model

from knowledge.models import Article, Category
from websites.models import Website, WebsiteAgent

from .permissions import DEMO_DOMAIN

User = get_user_model()

KNOWLEDGE_BASE = [
    (
        "Getting Started",
        "Learn the basics of our platform",
        [
            (
                "How do I create an account?",
                "Sign up on our homepage with your email address. "
                "You'll receive a confirmation link within minutes.",
            ),
            (
                "How do I reset my password?",
                "Click 'Forgot password' on the login page. Enter your email "
                "and follow the reset link we send you.",
            ),
        ],
    ),
    (
        "Billing",
        "Payment and subscription questions",
        [
            (
                "What payment methods do you accept?",
                "We accept all major credit cards, PayPal, and bank transfers "
                "for annual plans.",
            ),
            (
                "How do I cancel my subscription?",
                "Go to Settings > Billing > Cancel subscription. Your access "
                "continues until the end of the billing period.",
            ),
        ],
    ),
    (
        "Technical Support",
        "Troubleshooting and integrations",
        [
            (
                "How do I embed the chat widget?",
                "Copy the embed script from your dashboard and paste it before "
                "the closing </body> tag on your website.",
            ),
            (
                "Is there an API available?",
                "Yes! Visit our developer documentation for REST API endpoints "
                "and WebSocket integration guides.",
            ),
        ],
    ),
]


def _seed_knowledge_base(website):
    for cat_name, cat_desc, articles in KNOWLEDGE_BASE:
        category, _ = Category.unscoped.get_or_create(
            website=website,
            name=cat_name,
            defaults={"description": cat_desc},
        )
        for title, content in articles:
            Article.unscoped.get_or_create(
                website=website,
                title=title,
                category=category,
                defaults={"content": content},
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
        if not Article.unscoped.filter(website=website).exists():
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
