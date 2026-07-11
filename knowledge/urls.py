from django.urls import path

from . import views

app_name = "knowledge"

urlpatterns = [
    path("", views.help_center, name="help_center"),
    path("article/<slug:slug>/", views.article_detail, name="article"),
]
