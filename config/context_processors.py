from django.conf import settings
from django.utils.translation import gettext_lazy as _


def branding(request):
    product_name = getattr(settings, "PRODUCT_NAME", "Morse")
    return {
        "product_name": product_name,
        "brand_name": _("Morse"),
    }
