from django.utils import timezone
from django.db import transaction
from .models import Bid, Notification
from datetime import timedelta

def process_bid(user, item, amount, is_auto=False, max_auto_amount=None):
    """
    Unified bidding logic handling validations, bid creation, 
    auto-bid engine, and notifications.
    Returns: {'status': 'success/error', 'message': '...', 'data': {...}}
    """
    now = timezone.now()
    
    # 1. Validations
    if item.status != 'active' or now > item.end_time:
        return {'status': 'error', 'message': 'Auction has ended.'}
    
    if user == item.seller:
        return {'status': 'error', 'message': 'Sellers cannot bid on their own items.'}
    
    if float(amount) <= float(item.current_price):
        return {'status': 'error', 'message': f'Bid must be higher than ${item.current_price}'}

    with transaction.atomic():
        # 2. Identify previous highest bidder (to notify them later)
        previous_highest_bid = item.bids.order_by('-amount').first()
        previous_user = previous_highest_bid.user if previous_highest_bid else None

        # 3. Create the New Bid
        new_bid = Bid.objects.create(
            item=item,
            user=user,
            amount=amount,
            is_auto_bid=is_auto,
            max_auto_amount=max_auto_amount
        )
        item.current_price = amount

        # 4. Auto-extend Logic (if within 60s)
        time_left = item.end_time - now
        if time_left < timedelta(seconds=60):
            item.end_time = now + timedelta(seconds=60)
        
        item.save()

        # 5. Notify Seller
        Notification.objects.create(
            user=item.seller,
            message=f"New bid of ${amount} on your item '{item.title}'.",
            link=f"/auctions/item/{item.id}/"
        )

        # 6. Notify Previous Bidder they've been outbid
        if previous_user and previous_user != user:
            Notification.objects.create(
                user=previous_user,
                message=f"You have been outbid on '{item.title}'. New bid: ${amount}",
                link=f"/auctions/item/{item.id}/"
            )

        # 7. Check for competing Auto-bids
        # Trigger any OTHER auto-bids that might outbid this new person
        other_auto_bids = Bid.objects.filter(
            item=item, 
            is_auto_bid=True
        ).exclude(user=user).order_by('-max_auto_amount')

        if other_auto_bids.exists():
            top_auto = other_auto_bids.first()
            increment = 1.00
            
            if top_auto.max_auto_amount >= (float(amount) + increment):
                auto_amount = float(amount) + increment
                Bid.objects.create(
                    item=item,
                    user=top_auto.user,
                    amount=auto_amount,
                    is_auto_bid=True,
                    max_auto_amount=top_auto.max_auto_amount
                )
                item.current_price = auto_amount
                item.save()
                
                # Notify the person who just bid that they were outbid
                Notification.objects.create(
                    user=user,
                    message=f"You were immediately outbid by an auto-bid on '{item.title}'.",
                    link=f"/auctions/item/{item.id}/"
                )
                
                # Update return info for broadcast
                return {
                    'status': 'success',
                    'message': 'Bid placed, but outbid by auto-bid.',
                    'data': {
                        'amount': item.current_price,
                        'user': top_auto.user.email,
                        'end_time': item.end_time.isoformat()
                    }
                }

        return {
            'status': 'success',
            'message': 'Bid placed successfully!',
            'data': {
                'amount': item.current_price,
                'user': user.email,
                'end_time': item.end_time.isoformat()
            }
        }
