from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inbox.services.telegram import set_telegram_webhook


class Command(BaseCommand):
    help = (
        "Register Morse's Telegram webhook with Telegram's setWebhook API "
        "(uses TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=None,
            help="Override TELEGRAM_WEBHOOK_URL for this run",
        )
        parser.add_argument(
            "--secret",
            default=None,
            help="Override TELEGRAM_WEBHOOK_SECRET for this run",
        )

    def handle(self, *args, **options):
        token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN is not set")

        url = (options.get("url") or getattr(settings, "TELEGRAM_WEBHOOK_URL", "") or "").strip()
        if not url:
            raise CommandError(
                "TELEGRAM_WEBHOOK_URL is not set. Example: "
                "https://your-host/inbox/telegram/webhook/"
            )

        secret = options.get("secret")
        if secret is None:
            secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or ""
        secret = secret.strip()

        self.stdout.write(f"Setting Telegram webhook to: {url}")
        if secret:
            self.stdout.write("Secret token: configured (not printed)")
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Secret token: not set (TELEGRAM_WEBHOOK_SECRET empty)"
                )
            )

        ok, message = set_telegram_webhook(url, secret_token=secret)
        if not ok:
            raise CommandError(f"setWebhook failed: {message}")

        self.stdout.write(self.style.SUCCESS(f"setWebhook OK: {message}"))
        self.stdout.write(
            "Verify with: python manage.py telegram_get_webhook_info"
        )
