"""
Django Channels WebSocket consumer for live support chat.
Staff members and the ticket owner can exchange messages in real-time.

Room group name: support_<ticket_id>
Messages: {"type": "chat", "username": "...", "body": "...", "is_staff": bool}
"""
import json

from django.contrib.auth.models import User

try:
    from channels.generic.websocket import AsyncWebsocketConsumer

    class SupportChatConsumer(AsyncWebsocketConsumer):

        async def connect(self):
            self.ticket_id = self.scope["url_route"]["kwargs"]["ticket_id"]
            self.room_group = f"support_{self.ticket_id}"
            user = self.scope.get("user")
            if not user or not user.is_authenticated:
                await self.close()
                return
            # Only staff and the ticket owner may connect
            from channels.db import database_sync_to_async
            from ananimeclip.support.models import SupportTicket
            @database_sync_to_async
            def get_ticket():
                try:
                    return SupportTicket.objects.get(pk=self.ticket_id)
                except SupportTicket.DoesNotExist:
                    return None
            ticket = await get_ticket()
            if ticket is None or (not user.is_staff and ticket.user_id != user.pk):
                await self.close()
                return
            await self.channel_layer.group_add(self.room_group, self.channel_name)
            await self.accept()

        async def disconnect(self, code):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

        async def receive(self, text_data=None, bytes_data=None):
            user = self.scope.get("user")
            try:
                data = json.loads(text_data or "{}")
                body = str(data.get("body", "")).strip()[:1000]
            except Exception:
                return
            if not body:
                return
            await self.channel_layer.group_send(self.room_group, {
                "type": "chat_message",
                "username": user.username if user else "?",
                "body": body,
                "is_staff": bool(user and user.is_staff),
            })

        async def chat_message(self, event):
            await self.send(text_data=json.dumps({
                "type": "chat",
                "username": event["username"],
                "body": event["body"],
                "is_staff": event["is_staff"],
            }))

except ImportError:
    # channels not installed — no-op
    pass
