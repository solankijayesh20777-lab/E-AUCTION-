from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Bid, Notification, Item
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=Bid)
def handle_new_bid(sender, instance, created, **kwargs):
    if created:
        item = instance.item
        channel_layer = get_channel_layer()

        # 1. Notify the Seller
        seller_msg = f"New bid of ${instance.amount} on your item: {item.title}"
        Notification.objects.create(
            user=item.seller,
            message=seller_msg,
            link=f"/auctions/item/{item.id}/"
        )
        
        async_to_sync(channel_layer.group_send)(
            f'user_notifications_{item.seller.id}',
            {
                'type': 'send_notification',
                'message': seller_msg,
                'link': f"/auctions/item/{item.id}/"
            }
        )

        # 2. Notify the previous bidder (Outbid alert)
        previous_bid = Bid.objects.filter(item=item).exclude(id=instance.id).order_by('-amount').first()
        if previous_bid and previous_bid.user != instance.user:
            outbid_msg = f"You have been outbid on {item.title}! New bid: ${instance.amount}"
            Notification.objects.create(
                user=previous_bid.user,
                message=outbid_msg,
                link=f"/auctions/item/{item.id}/"
            )
            
            async_to_sync(channel_layer.group_send)(
                f'user_notifications_{previous_bid.user.id}',
                {
                    'type': 'send_notification',
                    'message': outbid_msg,
                    'link': f"/auctions/item/{item.id}/"
                }
            )
            
            # console logs for development
            print(f"--- EMAIL/SMS SIMULATION ---")
            print(f"To: {previous_bid.user.email} - {outbid_msg}")
            print(f"----------------------------")
