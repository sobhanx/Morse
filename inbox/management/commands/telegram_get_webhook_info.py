from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inbox.services.telegram import get_telegram_webhook_info


class Command(BaseCommand):
    help = "Display Telegram's current webhook configuration (getWebhookInfo)"

    def handle(self, *args, **options):
        token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN is not set")

        ok, info, error = get_telegram_webhook_info()
        if not ok or info is None:
            raise CommandError(f"getWebhookInfo failed: {error}")

        expected_url = (getattr(settings, "TELEGRAM_WEBHOOK_URL", "") or "").strip()
        expected_secret = bool(
            (getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or "").strip()
        )

        url = info.get("url") or ""
        has_custom_certificate = bool(info.get("has_custom_certificate"))
        pending = info.get("pending_update_count", 0)
        max_connections = info.get("max_connections")
        ip_address = info.get("ip_address") or ""
        last_error_date = info.get("last_error_date")
        last_error_message = info.get("last_error_message") or ""
        last_sync = info.get("last_synchronization_error_date")
        allowed_updates = info.get("allowed_updates") or []

        self.stdout.write("Telegram webhook info")
        self.stdout.write("-" * 40)
        self.stdout.write(f"url: {url or '(not set)'}")
        if expected_url:
            if url.rstrip("/") == expected_url.rstrip("/"):
                self.stdout.write(self.style.SUCCESS("url matches TELEGRAM_WEBHOOK_URL"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"url does not match TELEGRAM_WEBHOOK_URL ({expected_url})"
                    )
                )
        self.stdout.write(f"has_custom_certificate: {has_custom_certificate}")
        self.stdout.write(f"pending_update_count: {pending}")
        if max_connections is not None:
            self.stdout.write(f"max_connections: {max_connections}")
        if ip_address:
            self.stdout.write(f"ip_address: {ip_address}")
        if allowed_updates:
            self.stdout.write(f"allowed_updates: {', '.join(map(str, allowed_updates))}")
        else:
            self.stdout.write("allowed_updates: (default / all)")

        # Telegram does not echo the secret back; only remind local config.
        if expected_secret:
            self.stdout.write(
                "local TELEGRAM_WEBHOOK_SECRET: configured "
                "(Telegram does not return the secret in getWebhookInfo)"
            )
        else:
            self.stdout.write(
                self.style.WARNING("local TELEGRAM_WEBHOOK_SECRET: not set")
            )

        if last_error_date or last_error_message:
            self.stdout.write(self.style.ERROR(f"last_error_date: {last_error_date}"))
            self.stdout.write(
                self.style.ERROR(f"last_error_message: {last_error_message}")
            )
        else:
            self.stdout.write(self.style.SUCCESS("last_error: none"))

        if last_sync:
            self.stdout.write(
                self.style.WARNING(f"last_synchronization_error_date: {last_sync}")
            )

        if url:
            self.stdout.write(self.style.SUCCESS("Webhook is registered with Telegram."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "No webhook URL is registered. Run: "
                    "python manage.py telegram_set_webhook"
                )
            )
