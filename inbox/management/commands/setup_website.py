from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from websites.models import Website, WebsiteAgent

User = get_user_model()


class Command(BaseCommand):
    help = "Create or update a customer website and print its widget embed details"

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Display name for the website")
        parser.add_argument("--domain", required=True, help="Customer domain (e.g. example.com)")
        parser.add_argument(
            "--owner-phone",
            default=None,
            help="Phone of the website owner (defaults to first superuser)",
        )

    def handle(self, *args, **options):
        owner = None
        if options["owner_phone"]:
            owner = User.objects.filter(phone=options["owner_phone"]).first()
            if not owner:
                self.stderr.write(
                    self.style.ERROR(
                        f"No user found with phone {options['owner_phone']}. "
                        "Create the user first or omit --owner-phone to use a superuser."
                    )
                )
                return

        if not owner:
            owner = User.objects.filter(is_superuser=True).first()
        if not owner:
            self.stderr.write(
                self.style.ERROR("No owner user found. Create a superuser first.")
            )
            return

        domain = options["domain"].strip().lower()
        name = options["name"].strip()

        website, created = Website.objects.get_or_create(
            domain=domain,
            defaults={
                "name": name,
                "owner": owner,
            },
        )
        if not created:
            website.name = name
            website.owner = owner
            website.domain = domain

        website.is_active = True
        website.activated_at = website.activated_at or timezone.now()
        website.save()

        WebsiteAgent.objects.get_or_create(website=website, user=owner)

        base = getattr(settings, "PUBLIC_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
        embed_url = f"{base}/widget/embed.js?key={website.public_widget_key}"

        self.stdout.write(
            self.style.SUCCESS(
                f"Website: {website.name} ({'created' if created else 'updated'})"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Domain: {website.domain}"))
        self.stdout.write(self.style.SUCCESS(f"Active: {website.is_active}"))
        self.stdout.write(self.style.SUCCESS(f"Owner: {owner.phone}"))
        self.stdout.write(self.style.SUCCESS(f"Widget key: {website.public_widget_key}"))
        self.stdout.write("")
        self.stdout.write("Embed this script before </body> on the customer's site:")
        self.stdout.write(f'<script src="{embed_url}"></script>')
        self.stdout.write("")
        self.stdout.write(f"Widget demo: {base}/widget/demo/?key={website.public_widget_key}")
        self.stdout.write(f"Help center: {base}/help/?key={website.public_widget_key}")
