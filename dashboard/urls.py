from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("inbox/", views.inbox, name="inbox"),
    path("contacts/", views.contacts_list, name="contacts"),
    path("contacts/<int:contact_id>/", views.contact_detail, name="contact_detail"),
    path(
        "contacts/<int:contact_id>/notes/",
        views.update_contact_notes,
        name="update_contact_notes",
    ),
    path("analytics/", views.analytics, name="analytics"),
]
