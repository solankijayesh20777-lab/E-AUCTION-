import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_auction.settings')
django.setup()

from django.db import connection
from users.models import CustomUser
from auctions.models import Item, Bid, Category

print("--- Public Tables ---")
with connection.cursor() as cursor:
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    for row in cursor.fetchall():
        print(row[0])

print("\n--- User Count ---")
print(CustomUser.objects.count())

print("\n--- Recent Items ---")
for item in Item.objects.all()[:5]:
    print(f"ID: {item.id}, Title: {item.title}, Price: {item.current_price}")

print("\n--- Recent Bids ---")
for bid in Bid.objects.all()[:5]:
    print(f"Item: {bid.item.title}, User: {bid.user.email}, Amount: {bid.amount}")
