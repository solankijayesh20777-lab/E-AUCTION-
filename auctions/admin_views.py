from django.shortcuts import render
from django.db.models import Sum, Count
from .models import Item
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_analytics(request):
    total_items = Item.objects.count()
    active_auctions = Item.objects.filter(status='active', is_approved=True).count()
    sold_items = Item.objects.filter(status='sold').count()
    total_sales_volume = Item.objects.filter(status='sold').aggregate(Sum('starting_price'))['starting_price__sum'] or 0
    
    # Placeholder for fraud detection monitoring
    flagged_items = Item.objects.filter(fraud_score__gt=50).count()

    context = {
        'total_items': total_items,
        'active_auctions': active_auctions,
        'sold_items': sold_items,
        'total_sales_volume': total_sales_volume,
        'flagged_items': flagged_items,
        'title': 'Platform Analytics'
    }
    return render(request, 'admin/auctions/analytics.html', context)
