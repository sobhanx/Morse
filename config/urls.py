from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

import config.admin_dashboards  # noqa: F401 — register admin usage dashboards
from config.views import set_language_view

urlpatterns = [
    path("i18n/setlang/", set_language_view, name="set_language"),
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("inbox/", include("inbox.urls")),
    path("widget/", include("widget.urls")),
    path("help/", include("knowledge.urls")),
    path("websites/", include("websites.urls")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
