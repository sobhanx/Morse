from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

import config.admin_dashboards  # noqa: F401 — register admin usage dashboards

urlpatterns = [
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
