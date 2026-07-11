from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import check_for_language
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.i18n import LANGUAGE_QUERY_PARAMETER


def _safe_next_url(request):
    next_url = request.POST.get("next", request.GET.get("next"))
    if (
        next_url or request.accepts("text/html")
    ) and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = request.META.get("HTTP_REFERER")
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/"
    return next_url or "/"


def _language_response(lang_code, next_url):
    response = HttpResponseRedirect(next_url)
    if lang_code and check_for_language(lang_code):
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang_code,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )
    return response


@require_http_methods(["GET", "POST"])
@csrf_protect
def set_language_view(request):
    """Switch UI language. GET avoids CSRF issues for the language selector."""
    next_url = _safe_next_url(request)
    if request.method == "GET":
        return _language_response(
            request.GET.get(LANGUAGE_QUERY_PARAMETER), next_url
        )
    return _language_response(
        request.POST.get(LANGUAGE_QUERY_PARAMETER), next_url
    )
