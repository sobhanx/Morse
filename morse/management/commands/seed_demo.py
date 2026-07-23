import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from morse.constants import DEMO_DOMAIN
from morse.models import Article, Category, Contact, Conversation, Message, Website, WebsiteAgent

User = get_user_model()

DEMO_ADMIN_PHONE = os.getenv("DEMO_ADMIN_PHONE", "09000000000")
DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "changeme-demo")


class Command(BaseCommand):
    help = "Seed demo data for Morse multi-tenant MVP"

    def handle(self, *args, **options):
        agent, created = User.objects.get_or_create(
            phone=DEMO_ADMIN_PHONE,
            defaults={
                "username": DEMO_ADMIN_PHONE,
                "email": "agent@example.com",
                "first_name": "Support",
                "last_name": "Agent",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        agent.set_password(DEMO_ADMIN_PASSWORD)
        agent.is_staff = True
        agent.is_superuser = True
        agent.save()
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created admin user ({DEMO_ADMIN_PHONE} / {DEMO_ADMIN_PASSWORD})"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Admin user ready ({DEMO_ADMIN_PHONE} / {DEMO_ADMIN_PASSWORD})"
                )
            )

        website, _ = Website.objects.get_or_create(
            domain=DEMO_DOMAIN,
            defaults={
                "name": "Demo Website",
                "owner": agent,
                "is_active": True,
            },
        )
        if website.name != "Demo Website":
            website.name = "Demo Website"
        if website.owner_id != agent.id:
            website.owner = agent
        if not website.is_active:
            website.is_active = True
        website.save()

        WebsiteAgent.objects.get_or_create(website=website, user=agent)

        categories_data = [
            ("Getting Started", "Learn the basics of our platform", [
                ("How do I create an account?", "Sign up on our homepage with your email address. You'll receive a confirmation link within minutes."),
                ("How do I reset my password?", "Click 'Forgot password' on the login page. Enter your email and follow the reset link we send you."),
            ]),
            ("Billing", "Payment and subscription questions", [
                ("What payment methods do you accept?", "We accept all major credit cards, PayPal, and bank transfers for annual plans."),
                ("How do I cancel my subscription?", "Go to Settings > Billing > Cancel subscription. Your access continues until the end of the billing period."),
            ]),
            ("Technical Support", "Troubleshooting and integrations", [
                ("How do I embed the chat widget?", "Copy the embed script from your dashboard and paste it before the closing </body> tag on your website."),
                ("Is there an API available?", "Yes! Visit our developer documentation for REST API endpoints and WebSocket integration guides."),
            ]),
        ]

        for cat_name, cat_desc, articles in categories_data:
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

        self.stdout.write(self.style.SUCCESS("Created knowledge base articles"))

        if not Contact.unscoped.filter(website=website, email="demo@visitor.com").exists():
            contact = Contact.unscoped.create(
                website=website,
                name="Demo Visitor",
                email="demo@visitor.com",
                company="Acme Inc",
            )
            conversation = Conversation.unscoped.create(
                website=website,
                contact=contact,
                subject="Question about pricing",
                status=Conversation.Status.OPEN,
            )
            Message.unscoped.create(
                website=website,
                conversation=conversation,
                sender_type=Message.SenderType.VISITOR,
                content="Hi! I'd like to know more about your enterprise pricing plans.",
            )
            Message.unscoped.create(
                website=website,
                conversation=conversation,
                sender_type=Message.SenderType.AGENT,
                agent=agent,
                content="Hello! Thanks for reaching out. Our enterprise plan starts at $99/month per seat. Would you like a detailed breakdown?",
            )
            self.stdout.write(self.style.SUCCESS("Created demo conversation"))

        self.stdout.write(self.style.SUCCESS(f"Demo website widget key: {website.public_widget_key}"))
        self.stdout.write(self.style.SUCCESS(
            f"Widget demo: /widget/demo/?key={website.public_widget_key}"
        ))
        self.stdout.write(self.style.SUCCESS("Seed data complete!"))
