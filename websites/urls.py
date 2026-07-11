from django.urls import path

from . import views

app_name = "websites"

urlpatterns = [
    path("", views.website_list, name="list"),
    path("create/", views.website_create, name="create"),
    path("<uuid:website_id>/switch/", views.website_switch, name="switch"),
    path("<uuid:website_id>/activate/", views.website_activate, name="activate"),
    path(
        "<uuid:website_id>/activate/toggle/",
        views.website_activate_toggle,
        name="activate_toggle",
    ),
    path(
        "<uuid:website_id>/deactivate/",
        views.website_deactivate,
        name="deactivate",
    ),
    path("settings/", views.website_settings, name="settings"),
    path("admin-panel/", views.admin_panel, name="admin_panel"),
]
