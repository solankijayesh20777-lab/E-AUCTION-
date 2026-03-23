import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from .models import Item, Bid
from django.contrib.auth import get_user_model

User = get_user_model()

class BidConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.item_id = self.scope['url_route']['kwargs']['item_id']
        self.room_group_name = f'auction_{self.item_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        bid_amount = float(text_data_json['amount'])
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.send(text_data=json.dumps({
                'error': 'You must be logged in to bid.'
            }))
            return

        # Process bid via sync service
        result = await self.sync_process_bid(user, bid_amount)

        if result['status'] == 'success':
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'auction_message',
                    'amount': str(result['data']['amount']),
                    'user': result['data']['user'],
                    'end_time': result['data']['end_time']
                }
            )
        else:
            await self.send(text_data=json.dumps({
                'error': result['message']
            }))

    async def auction_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'amount': event['amount'],
            'user': event['user'],
            'end_time': event['end_time']
        }))

    @database_sync_to_async
    def sync_process_bid(self, user, amount):
        try:
            item = Item.objects.get(id=self.item_id)
            # Use the unified service
            return process_bid(user, item, amount)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user_id = self.scope["user"].id
            self.room_group_name = f'user_notifications_{self.user_id}'

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def send_notification(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message'],
            'link': event.get('link', '')
        }))
