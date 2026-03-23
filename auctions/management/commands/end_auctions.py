from django.core.management.base import BaseCommand
from django.utils import timezone
from auctions.models import Item, Notification

class Command(BaseCommand):
    help = 'Expires auctions that have reached their end time.'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_items = Item.objects.filter(
            status='active',
            end_time__lte=now
        )
        
        count = expired_items.count()
        for item in expired_items:
            # Check if there are any bids
            highest_bid = item.bids.order_by('-amount').first()
            if highest_bid:
                item.status = 'sold'
                # Notify winner
                Notification.objects.create(
                    user=highest_bid.user,
                    message=f"Congratulations! You won the auction for '{item.title}'!",
                    link=f"/auctions/item/{item.id}/"
                )
                # Notify seller
                Notification.objects.create(
                    user=item.seller,
                    message=f"Your item '{item.title}' has been sold for ${item.current_price}!",
                    link=f"/auctions/dashboard/"
                )
            else:
                item.status = 'ended'
                # Notify seller
                Notification.objects.create(
                    user=item.seller,
                    message=f"Your auction for '{item.title}' ended without any bids.",
                    link=f"/auctions/dashboard/"
                )
            item.save()
            
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} items.'))
