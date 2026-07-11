from django.urls import path

from . import views

app_name = "inbox"

urlpatterns = [
    path(
        "conversations/<int:conversation_id>/send/",
        views.send_agent_message,
        name="send_message",
    ),
    path(
        "conversations/<int:conversation_id>/update/",
        views.update_conversation,
        name="update_conversation",
    ),
]
