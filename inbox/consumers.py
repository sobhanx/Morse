import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from websites.permissions import (
    get_widget_key_from_scope,
    resolve_website_by_widget_key,
    user_can_access_website,
)

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"conversation_{self.conversation_id}"
        self.widget_key = get_widget_key_from_scope(self.scope)

        if not await self.can_connect():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type", "message")

        if message_type == "message":
            content = data.get("content", "").strip()
            if not content:
                return

            user = self.scope.get("user")
            if user and user.is_authenticated:
                message = await self.save_agent_message(content, user)
            else:
                message = await self.save_visitor_message(content)

            if not message:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": {
                        "id": message["id"],
                        "content": message["content"],
                        "sender_type": message["sender_type"],
                        "sender_name": message["sender_name"],
                        "created_at": message["created_at"],
                    },
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def can_connect(self):
        try:
            conversation = Conversation.unscoped.select_related("website").get(
                pk=self.conversation_id
            )
        except Conversation.DoesNotExist:
            return False

        user = self.scope.get("user")
        if user and user.is_authenticated:
            return user_can_access_website(user, conversation.website)

        website = resolve_website_by_widget_key(self.widget_key)
        return website is not None and website.id == conversation.website_id

    @database_sync_to_async
    def save_visitor_message(self, content):
        try:
            conversation = Conversation.unscoped.get(pk=self.conversation_id)
        except Conversation.DoesNotExist:
            return None

        website = resolve_website_by_widget_key(self.widget_key)
        if not website or website.id != conversation.website_id:
            return None

        message = Message.unscoped.create(
            conversation=conversation,
            website=conversation.website,
            sender_type=Message.SenderType.VISITOR,
            content=content,
        )
        conversation.is_unread = True
        conversation.status = Conversation.Status.OPEN
        conversation.save(update_fields=["is_unread", "status", "updated_at"])
        return {
            "id": message.id,
            "content": message.content,
            "sender_type": message.sender_type,
            "sender_name": message.sender_name,
            "created_at": message.created_at.isoformat(),
        }

    @database_sync_to_async
    def save_agent_message(self, content, user):
        try:
            conversation = Conversation.unscoped.select_related("website").get(
                pk=self.conversation_id
            )
        except Conversation.DoesNotExist:
            return None

        if not user_can_access_website(user, conversation.website):
            return None

        message = Message.unscoped.create(
            conversation=conversation,
            website=conversation.website,
            sender_type=Message.SenderType.AGENT,
            agent=user,
            content=content,
        )
        conversation.is_unread = False
        conversation.save(update_fields=["is_unread", "updated_at"])
        return {
            "id": message.id,
            "content": message.content,
            "sender_type": message.sender_type,
            "sender_name": message.sender_name,
            "created_at": message.created_at.isoformat(),
        }
