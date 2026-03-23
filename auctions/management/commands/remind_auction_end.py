from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from auctions.models import Item, Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class Command(BaseCommand):
    help = 'Sends reminders for auctions ending within 1 hour'

    def handle(self, *args, **options):
        now = timezone.now()
        one_hour_later = now + timedelta(hours=1)
        
        # Find active items ending in the next hour
        items = Item.objects.filter(
            status='active',
            end_time__gt=now,
            end_time__lte=one_hour_later
        )

        channel_layer = get_channel_layer()

        for item in items:
            # 1. Notify the Seller
            seller_msg = f"Your auction for '{item.title}' is ending soon (at {item.end_time.strftime('%H:%M')})."
            self.send_notification(item.seller, seller_msg, item, channel_layer)

            # 2. Notify Watchers
            for watcher in item.watched_by.all():
                watcher_user = watcher.user
                watcher_msg = f"Reminder: Auction for '{item.title}' which you are watching ends in less than an hour!"
                self.send_notification(watcher_user, watcher_msg, item, channel_layer)

            # 3. Notify Bidders
            bidders = set(bid.user for bid in item.bids.all())
            for bidder in bidders:
                bidder_msg = f"Ending Soon: The auction for '{item.title}' is closing within an hour. Place your final bids!"
                self.send_notification(bidder, bidder_msg, item, channel_layer)

        self.stdout.write(self.style.SUCCESS(f"Successfully sent reminders for {items.count()} auctions."))

    def send_notification(self, user, message, item, channel_layer):
        # Create In-site Notification
        Notification.objects.create(
            user=user,
            message=message,
            link=f"/auctions/item/{item.id}/"
        )
        
        # Send via WebSocket
        async_to_sync(channel_layer.group_send)(
            f'user_notifications_{user.id}',
            {
                'type': 'send_notification',
                'message': message,
                'link': f"/auctions/item/{item.id}/"
            }
        )
        
        # Log Email/SMS Simulation
        self.stdout.write(f"NOTIFICATION SENT to {user.email}: {message}")
