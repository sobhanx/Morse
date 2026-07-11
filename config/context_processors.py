from django.conf import settings


def branding(request):
    return {"product_name": getattr(settings, "PRODUCT_NAME", "Morse")}
