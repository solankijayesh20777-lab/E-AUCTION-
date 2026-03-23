from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Item(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('sold', 'Sold'),
    )

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='auction_items/')
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reserve_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_approved = models.BooleanField(default=False)
    received_by_buyer = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    fraud_score = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.current_price:
            self.current_price = self.starting_price
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.is_approved and self.status == 'active' and self.start_time <= now <= self.end_time

    @property
    def winner(self):
        if self.status in ['ended', 'sold']:
            highest_bid = self.bids.order_by('-amount').first()
            if highest_bid:
                return highest_bid.user
        return None

    @property
    def buyer(self):
        return self.winner

class Bid(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_auto_bid = models.BooleanField(default=False)
    max_auto_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-amount']

    def __str__(self):
        return f"{self.user.email} - {self.amount} on {self.item.title}"

class Watchlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist')
    items = models.ManyToManyField(Item, blank=True, related_name='watched_by')

    def __str__(self):
        return f"Watchlist for {self.user.email}"

class CommissionSetting(models.Model):
    name = models.CharField(max_length=100, default="Standard Commission")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage fee on final sale price.")
    flat_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Flat fee per transaction.")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.message[:20]}"

# --- Real-time Notifications Signal ---
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=Notification)
def send_notification_realtime(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_notifications_{instance.user.id}',
            {
                'type': 'send_notification',
                'message': instance.message,
                'link': instance.link
            }
        )
