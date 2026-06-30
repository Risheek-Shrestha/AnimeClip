"""
Django Channels WebSocket consumer for Watch Party real-time sync.

Replaces the 3-second polling loop with a proper WebSocket group broadcast.
The JS client sends:
  {"type": "sync", "position": 12.4, "is_playing": true}   (host only)
  {"type": "heartbeat"}                                       (any member)

The consumer broadcasts to all group members:
  {"type": "state", "position": ..., "is_playing": ..., "host": "...", "members": [...]}

Room group name: watch_party_<room_code>
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

try:
    from channels.db import database_sync_to_async
    from channels.generic.websocket import AsyncWebsocketConsumer
    from django.utils import timezone

    from .models import WatchParty, WatchPartyMember

    class WatchPartyConsumer(AsyncWebsocketConsumer):
        async def connect(self):
            self.room_code = self.scope['url_route']['kwargs']['room_code']
            self.group_name = f'watch_party_{self.room_code}'
            user = self.scope.get('user')
            if not user or not user.is_authenticated:
                await self.close()
                return

            @database_sync_to_async
            def get_party():
                try:
                    return WatchParty.objects.get(room_code=self.room_code, is_active=True)
                except WatchParty.DoesNotExist:
                    return None

            party = await get_party()
            if party is None:
                await self.close()
                return

            @database_sync_to_async
            def join():
                WatchPartyMember.objects.get_or_create(party=party, user=user)

            await join()
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

        async def disconnect(self, code):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        async def receive(self, text_data=None, bytes_data=None):
            user = self.scope.get('user')
            try:
                data = json.loads(text_data or '{}')
            except Exception:
                return
            msg_type = data.get('type')

            if msg_type == 'sync':
                @database_sync_to_async
                def update_party():
                    try:
                        party = WatchParty.objects.get(
                            room_code=self.room_code, host=user, is_active=True
                        )
                        party.playback_position = float(data.get('position', party.playback_position))
                        party.is_playing = bool(data.get('is_playing', party.is_playing))
                        party.updated_at = timezone.now()
                        party.save(update_fields=['playback_position', 'is_playing', 'updated_at'])
                        members = list(
                            party.members.select_related('user').values_list('user__username', flat=True)
                        )
                        return party, members
                    except WatchParty.DoesNotExist:
                        return None, []

                party, members = await update_party()
                if party:
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            'type': 'party_state',
                            'position': party.playback_position,
                            'is_playing': party.is_playing,
                            'host': user.username,
                            'members': members,
                        },
                    )

            elif msg_type == 'heartbeat':
                pass  # connection keepalive; no broadcast needed

        async def party_state(self, event):
            await self.send(text_data=json.dumps({
                'type': 'state',
                'position': event['position'],
                'is_playing': event['is_playing'],
                'host': event['host'],
                'members': event['members'],
            }))

except ImportError:
    pass
