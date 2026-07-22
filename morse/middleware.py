"""Resolve request.website from widget key or dashboard session."""

from asgiref.sync import iscoroutinefunction, sync_to_async
from django.utils.decorators import sync_and_async_middleware

from morse.permissions import (
    get_demo_website,
    get_widget_key_from_request,
    is_public_showcase_path,
    resolve_dashboard_website,
    resolve_website_by_widget_key,
)
from morse.tenant import reset_current_website, set_current_website

WIDGET_PREFIXES = ("/widget/", "/help/")
DASHBOARD_PREFIXES = ("/inbox", "/contacts", "/analytics", "/websites")


def _is_dashboard_path(path):
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in DASHBOARD_PREFIXES
    )


def _resolve_website(request):
    path = request.path

    if path.startswith(WIDGET_PREFIXES):
        key = get_widget_key_from_request(request)
        website = resolve_website_by_widget_key(key)
        if website is None and is_public_showcase_path(path):
            website = get_demo_website()
        return website

    if request.user.is_authenticated and _is_dashboard_path(path):
        return resolve_dashboard_website(request)

    return None


@sync_and_async_middleware
def WebsiteMiddleware(get_response):
    if iscoroutinefunction(get_response):

        async def middleware(request):
            website = await sync_to_async(_resolve_website, thread_sensitive=True)(
                request
            )
            request.website = website
            token = set_current_website(website) if website else None
            try:
                return await get_response(request)
            finally:
                if token is not None:
                    reset_current_website(token)

    else:

        def middleware(request):
            website = _resolve_website(request)
            request.website = website
            token = set_current_website(website) if website else None
            try:
                return get_response(request)
            finally:
                if token is not None:
                    reset_current_website(token)

    return middleware
