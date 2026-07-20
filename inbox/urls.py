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
        "conversations/<int:conversation_id>/messages/",
        views.conversation_messages,
        name="conversation_messages",
    ),
    path(
        "conversations/feed/",
        views.conversations_feed,
        name="conversations_feed",
    ),
    path(
        "conversations/<int:conversation_id>/update/",
        views.update_conversation,
        name="update_conversation",
    ),
    path(
        "messages/<int:message_id>/audio/",
        views.serve_message_audio,
        name="message_audio",
    ),
]
