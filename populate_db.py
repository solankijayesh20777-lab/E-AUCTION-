import os
import django
import random
import requests
from django.core.files.base import ContentFile
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_auction.settings')
django.setup()

from users.models import CustomUser
from auctions.models import Category, Item, Bid

def populate():
    print("Creating users...")
    # 1. Create Sellers and Buyers
    seller1, _ = CustomUser.objects.get_or_create(email='seller1@example.com', defaults={'first_name': 'John', 'is_seller': True, 'is_seller_approved': True})
    if not seller1.has_usable_password():
        seller1.set_password('password123')
        seller1.save()
        
    buyer1, _ = CustomUser.objects.get_or_create(email='buyer1@example.com', defaults={'first_name': 'Alice'})
    if not buyer1.has_usable_password():
        buyer1.set_password('password123')
        buyer1.save()
        
    buyer2, _ = CustomUser.objects.get_or_create(email='buyer2@example.com', defaults={'first_name': 'Bob'})
    if not buyer2.has_usable_password():
        buyer2.set_password('password123')
        buyer2.save()

    print("Creating categories...")
    # 2. Categories
    cat_art, _ = Category.objects.get_or_create(name='Art', slug='art')
    cat_tech, _ = Category.objects.get_or_create(name='Technology', slug='tech')
    cat_vintage, _ = Category.objects.get_or_create(name='Vintage', slug='vintage')
    cat_fashion, _ = Category.objects.get_or_create(name='Fashion', slug='fashion')

    # 3. Items
    items_data = [
        {'title': 'Vintage Rolex Watch', 'desc': 'A beautiful vintage watch in perfect condition.', 'cat': cat_vintage, 'price': 5000.00, 'img_seed': '1'},
        {'title': 'Original Oil Painting', 'desc': 'Original artwork by a renowned artist.', 'cat': cat_art, 'price': 1200.00, 'img_seed': '2'},
        {'title': 'Gaming Laptop RTX 4090', 'desc': 'High end gaming laptop lightly used. Extremely fast with 64GB RAM.', 'cat': cat_tech, 'price': 2500.00, 'img_seed': '3'},
        {'title': 'Antique Wooden Chair', 'desc': 'Handcrafted wooden chair from the 18th century, fully restored.', 'cat': cat_vintage, 'price': 300.00, 'img_seed': '4'},
        {'title': 'Gucci Handbag', 'desc': 'Authentic Gucci handbag, excellent interior condition.', 'cat': cat_fashion, 'price': 1500.00, 'img_seed': '5'},
        {'title': 'Abstract Architecture Sculpture', 'desc': 'Modern 3D sculpture, perfect for a modern living room.', 'cat': cat_art, 'price': 800.00, 'img_seed': '6'}
    ]

    print("Creating items and downloading dummy images...")
    now = timezone.now()
    created_items = []
    
    for i, data in enumerate(items_data):
        item, created = Item.objects.get_or_create(title=data['title'], defaults={
            'seller': seller1,
            'category': data['cat'],
            'description': data['desc'],
            'starting_price': data['price'],
            'current_price': data['price'],
            'status': 'active',
            'is_approved': True,
            'end_time': now + timedelta(days=random.randint(2, 7))
        })
        
        # Download image if it doesn't have one
        if not item.image:
            image_url = f"https://picsum.photos/seed/{data['img_seed']}/600/400"
            try:
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    filename = f"dummy_item_{i}_{data['title'].replace(' ', '_')}.jpg"
                    item.image.save(filename, ContentFile(response.content), save=True)
                    print(f"Downloaded image for {item.title}")
                else:
                    print(f"Failed to download image for {item.title}, HTTP {response.status_code}")
            except Exception as e:
                print(f"Exception downloading image for {item.title}: {e}")
        
        created_items.append(item)

    print("Adding dummy bids from buyers...")
    # 4. Add Bids
    for item in created_items:
        # Check if item already has bids, skip if it does
        if getattr(item, 'bids', None) and item.bids.exists():
            continue
            
        current_price = item.starting_price
        # Randomly decide how many bids this item has
        num_bids = random.randint(1, 4)
        print(f"Adding {num_bids} bids for {item.title}...")
        
        for _ in range(num_bids):
            buyer = random.choice([buyer1, buyer2])
            increment = random.choice([50, 100, 200, 250])
            current_price = float(current_price) + increment
            
            Bid.objects.create(
                item=item,
                user=buyer,
                amount=current_price
            )
            item.current_price = current_price
            item.save()

    print("Success! Dummy data has been populated successfully.")

if __name__ == '__main__':
    populate()
