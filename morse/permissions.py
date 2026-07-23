"""Website / widget-key resolution and dashboard access helpers."""

from urllib.parse import parse_qs

from django.http import JsonResponse

from morse.constants import DEMO_DOMAIN  # noqa: F401 — re-export for compatibility
from morse.models import Website


def get_widget_key_from_request(request):
    key = request.GET.get("key") or request.META.get("HTTP_X_WIDGET_KEY")
    if key:
        return key.strip()
    return None


def get_widget_key_from_scope(scope):
    query = scope.get("query_string", b"").decode()
    if not query:
        return None
    params = parse_qs(query)
    values = params.get("key", [])
    return values[0].strip() if values else None


def resolve_website_by_widget_key(key, *, require_active=True):
    if not key:
        return None
    try:
        website = Website.objects.get(public_widget_key=key)
    except Website.DoesNotExist:
        return None
    if require_active and not website.is_active:
        return None
    return website


def get_demo_website():
    """Return the public demo tenant used for marketing pages without a widget key."""
    from morse.demo import ensure_demo_website

    website = ensure_demo_website()
    if website:
        return website
    return Website.objects.filter(is_active=True).order_by("created_at").first()


def is_public_showcase_path(path):
    return path.startswith("/help/") or path.startswith("/widget/demo")


def user_can_access_website(user, website):
    if not user.is_authenticated or website is None:
        return False
    if user.is_superuser:
        return True
    if website.owner_id == user.id:
        return True
    return website.agents.filter(user_id=user.id).exists()


def get_accessible_websites(user):
    if not user.is_authenticated:
        return Website.objects.none()
    if user.is_superuser:
        return Website.objects.all()
    owned = Website.objects.filter(owner=user)
    member = Website.objects.filter(agents__user=user)
    return (owned | member).distinct()


ACTIVE_WEBSITE_SESSION_KEY = "active_website_id"


def get_active_website_id(request):
    return request.session.get(ACTIVE_WEBSITE_SESSION_KEY)


def set_active_website(request, website):
    request.session[ACTIVE_WEBSITE_SESSION_KEY] = str(website.id)


def resolve_dashboard_website(request):
    website_id = get_active_website_id(request)
    if not website_id:
        return None
    try:
        website = Website.objects.get(pk=website_id)
    except (Website.DoesNotExist, ValueError):
        return None
    if not user_can_access_website(request.user, website):
        return None
    return website


def website_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.website is None:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"error": "Website context required"}, status=403)
            from django.shortcuts import redirect

            return redirect("websites:list")
        return view_func(request, *args, **kwargs)

    return wrapper
