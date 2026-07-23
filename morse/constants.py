"""Shared constants for the Morse business app."""

from django.conf import settings

DEMO_DOMAIN = getattr(settings, "DEMO_WEBSITE_DOMAIN", "demo.example.com")
