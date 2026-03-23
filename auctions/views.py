from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Item, Category, Bid, Watchlist, Notification
from payments.models import Wallet, Transaction
from .forms import ItemForm

def item_list(request):
    items = Item.objects.filter(is_approved=True, status='active')
    categories = Category.objects.all()
    
    # Search
    query = request.GET.get('q')
    if query:
        items = items.filter(title__icontains=query)
    
    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        items = items.filter(category__slug=category_slug)
        
    context = {
        'items': items,
        'categories': categories,
    }
    return render(request, 'auctions/item_list.html', context)

from .services import process_bid

def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    # Only allow viewing if approved, OR if user is the seller, OR if user is staff
    if not item.is_approved:
        if not (request.user.is_authenticated and (request.user == item.seller or request.user.is_staff)):
            from django.http import Http404
            raise Http404("No Item matches the given query.")
    bids = item.bids.all()[:10]
    
    if request.method == 'POST' and request.user.is_authenticated:
        bid_amount = request.POST.get('amount')
        is_auto = request.POST.get('is_auto_bid') == 'on'
        max_amount = request.POST.get('max_auto_amount')

        try:
            bid_amount = float(bid_amount)
            max_auto_amount = float(max_amount) if is_auto and max_amount else None
            
            result = process_bid(request.user, item, bid_amount, is_auto, max_auto_amount)
            
            if result['status'] == 'success':
                messages.success(request, result['message'])
            else:
                messages.error(request, result['message'])
                
        except (ValueError, TypeError):
            messages.error(request, "Invalid bid amount.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
        return redirect('item_detail', pk=item.id)
    context = {
        'item': item,
        'bids': bids,
    }
    return render(request, 'auctions/item_detail.html', context)

@login_required
def seller_dashboard(request):
    items = Item.objects.filter(seller=request.user).order_by('-created_at')
    # Real Stats
    sold_items = items.filter(status='sold')
    total_sales = sold_items.count()
    
    # Calculate total earnings from release transactions
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    total_earnings = Transaction.objects.filter(
        wallet=wallet, 
        transaction_type='release', 
        status='success'
    ).aggregate(models.Sum('amount'))['amount__sum'] or 0
    
    active_bids_count = Item.objects.filter(seller=request.user, status='active', bids__isnull=False).distinct().count()

    return render(request, 'auctions/dashboard.html', {
        'items': items,
        'total_sales': total_sales,
        'total_earnings': total_earnings,
        'active_bids': active_bids_count,
    })

@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.seller = request.user
            item.status = 'active'  # Automatically set to active for now
            item.save()
            Notification.objects.create(
                user=request.user,
                message=f"Your item '{item.title}' has been uploaded successfully.",
                link=f"/auctions/item/{item.id}/"
            )
            messages.success(request, "Item uploaded successfully!")
            return redirect('seller_dashboard')
    else:
        form = ItemForm()
    return render(request, 'auctions/item_form.html', {'form': form, 'title': 'Upload New Item'})

@login_required
def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk, seller=request.user)
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully!")
            return redirect('seller_dashboard')
    else:
        form = ItemForm(instance=item)
    return render(request, 'auctions/item_form.html', {'form': form, 'title': 'Edit Item'})

@login_required
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk, seller=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, "Item deleted successfully!")
        return redirect('seller_dashboard')
    return render(request, 'auctions/item_confirm_delete.html', {'item': item})

@login_required
def toggle_watchlist(request, pk):
    item = get_object_or_404(Item, pk=pk)
    watchlist, created = Watchlist.objects.get_or_create(user=request.user)
    
    if item in watchlist.items.all():
        watchlist.items.remove(item)
        messages.info(request, f"Removed {item.title} from your watchlist.")
    else:
        watchlist.items.add(item)
        messages.success(request, f"Added {item.title} to your watchlist!")
        
    return redirect('item_detail', pk=pk)

@login_required
def watchlist_view(request):
    watchlist, created = Watchlist.objects.get_or_create(user=request.user)
    items = watchlist.items.all()
    return render(request, 'auctions/watchlist.html', {'items': items})

@login_required
def buyer_dashboard(request):
    # Items the user has placed bids on
    items = Item.objects.filter(bids__user=request.user).distinct().order_by('-end_time')
    
    total_bids = request.user.bids.count()
    active_bids = items.filter(status='active').count()
    # Correct Won Items Logic
    won_items_list = []
    for item in items:
        if item.status in ['sold', 'ended']:
            highest_bid = item.bids.order_by('-amount').first()
            if highest_bid and highest_bid.user == request.user:
                won_items_list.append(item)
    
    won_items_count = len(won_items_list)
    
    return render(request, 'auctions/buyer_dashboard.html', {
        'items': items,
        'total_bids': total_bids,
        'active_bids': active_bids,
        'won_items': won_items_count,
    })

from django.http import JsonResponse

@login_required
def mark_notifications_as_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
