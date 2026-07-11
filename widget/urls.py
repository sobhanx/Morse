from django.urls import path

from . import views

app_name = "widget"

urlpatterns = [
    path("chat/", views.chat_widget, name="chat"),
    path("embed.js", views.embed_script, name="embed"),
    path("demo/", views.demo_page, name="demo"),
    path("demo/pricing/", views.demo_pricing, name="demo_pricing"),
    path("start/", views.start_conversation, name="start"),
    path("contact/", views.update_contact, name="update_contact"),
    path(
        "conversations/<int:conversation_id>/send/",
        views.send_message,
        name="send_message",
    ),
]
