from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from auctions.models import Item, CommissionSetting, Notification
from .models import Payment, Wallet, Transaction
from .utils import create_razorpay_order, verify_razorpay_signature

@login_required
def initiate_payment(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    amount = item.current_price
    gateway = request.GET.get('gateway', 'razorpay')

    try:
        if gateway == 'razorpay':
            try:
                order = create_razorpay_order(amount, receipt=f'rcpt_{item.id}')
            except Exception as e:
                if settings.DEBUG:
                    # Unique dummy order for development using timestamp
                    import time
                    order = {'id': f'dummy_ord_{item.id}_{int(time.time())}', 'amount': amount * 100, 'currency': 'INR'}
                else:
                    raise e
            
            payment = Payment.objects.create(
                item=item,
                buyer=request.user,
                amount=amount,
                gateway_name='Razorpay',
                gateway_order_id=order['id']
            )
            context = {
                'order': order,
                'payment': payment,
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', ''),
                'item': item,
                'gateway': 'razorpay',
                'debug': settings.DEBUG
            }
            return render(request, 'payments/checkout.html', context)
        
        elif gateway == 'stripe':
            success_url = request.build_absolute_uri('/payments/stripe-success/') + f"?item_id={item.id}"
            cancel_url = request.build_absolute_uri('/payments/stripe-cancel/')
            session = create_stripe_checkout_session(
                amount, 
                item.title, 
                success_url, 
                cancel_url
            )
            Payment.objects.create(
                item=item,
                buyer=request.user,
                amount=amount,
                gateway_name='Stripe',
                gateway_order_id=session.id
            )
            return redirect(session.url, code=303)

        elif gateway == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance >= amount:
                wallet.balance -= amount
                wallet.save()
                
                # Create Payment
                payment = Payment.objects.create(
                    item=item,
                    buyer=request.user,
                    amount=amount,
                    gateway_name='Wallet',
                    status='completed'
                )
                
                # Mark item as sold
                item.status = 'sold'
                item.save()
                
                # Record transaction for buyer
                Transaction.objects.create(
                    wallet=wallet,
                    amount=-amount,
                    transaction_type='withdrawal',
                    status='success',
                    description=f"Paid for {item.title} using wallet balance"
                )
                
                # Create Escrow for seller
                Transaction.objects.create(
                    wallet=Wallet.objects.get_or_create(user=item.seller)[0],
                    amount=amount,
                    transaction_type='escrow',
                    status='pending',
                    description=f"Payment held in escrow (via Wallet) for {item.title}"
                )
                
                messages.success(request, f"Successfully paid ${amount} using wallet balance!")
                return redirect('item_detail', pk=item.id)
            else:
                messages.error(request, "Insufficient wallet balance.")
                return redirect('item_detail', pk=item.id)

    except Exception as e:
        messages.error(request, f"Error initiating payment: {str(e)}")
        return redirect('item_detail', pk=item.id)

@csrf_exempt
def payment_callback(request):
    # Razorpay callback
    if request.method == "POST":
        try:
            params_dict = {
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }
            
            from .utils import verify_razorpay_signature
            verify_razorpay_signature(params_dict)
            
            payment = Payment.objects.get(gateway_order_id=params_dict['razorpay_order_id'])
            payment.gateway_payment_id = params_dict['razorpay_payment_id']
            payment.status = 'completed'
            payment.save()
            
            if payment.item:
                item = payment.item
                item.status = 'sold'
                item.save()
                
                # Initial Escrow Transaction
                Transaction.objects.create(
                    wallet=Wallet.objects.get_or_create(user=item.seller)[0],
                    amount=payment.amount,
                    transaction_type='escrow',
                    status='pending',
                    description=f"Payment held in escrow for {item.title}"
                )
                messages.success(request, "Payment successful!")
            else:
                # Wallet Deposit
                wallet, _ = Wallet.objects.get_or_create(user=payment.buyer)
                wallet.balance += payment.amount
                wallet.save()
                Transaction.objects.create(
                    wallet=wallet,
                    amount=payment.amount,
                    transaction_type='deposit',
                    status='success',
                    description="Wallet top-up successful"
                )
                # Add Notification
                Notification.objects.create(
                    user=payment.buyer,
                    message=f"Success! ${payment.amount} has been added to your wallet.",
                    link="/payments/wallet/"
                )
                messages.success(request, f"Wallet topped up with ${payment.amount}!")
                print(f"DEBUG: Real payment success logic finished. User: {payment.buyer}, Amount: {payment.amount}")
            
            if payment.item:
                item = payment.item
                # Notify Seller
                Notification.objects.create(
                    user=item.seller,
                    message=f"Payment received for '{item.title}'. Funds are held in escrow.",
                    link=f"/auctions/dashboard/"
                )
                # Notify Buyer
                Notification.objects.create(
                    user=request.user,
                    message=f"Payment successful for '{item.title}'. Please confirm delivery once received.",
                    link=f"/auctions/item/{item.id}/"
                )
                return redirect('item_detail', pk=item.id)
            else:
                return redirect('wallet_dashboard')
            
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect('item_list')
    return redirect('item_list')

@login_required
def stripe_success(request):
    item_id = request.GET.get('item_id')
    item = get_object_or_404(Item, id=item_id)
    
    # In a real app, verify the session with Stripe API here
    payment = Payment.objects.filter(item=item, buyer=request.user, gateway_name='Stripe').last()
    if payment:
        payment.status = 'completed'
        payment.save()
        
        item.status = 'sold'
        item.save()
        
        # Log Escrow
        Transaction.objects.create(
            wallet=Wallet.objects.get_or_create(user=item.seller)[0],
            amount=payment.amount,
            transaction_type='escrow',
            status='pending',
            description=f"Stripe payment held in escrow for {item.title}"
        )
        
        messages.success(request, "Stripe payment successful! Funds are in escrow.")
    return redirect('item_detail', pk=item.id)

@login_required
def stripe_cancel(request):
    messages.warning(request, "Stripe payment was cancelled.")
    return redirect('item_list')

@login_required
def wallet_dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by('-created_at')
    return render(request, 'payments/wallet.html', {'wallet': wallet, 'transactions': transactions})

@login_required
def deposit_funds(request):
            
    if request.method == "POST":
        amount = request.POST.get('amount')
        gateway = request.POST.get('gateway', 'razorpay')
        
        try:
            amount = Decimal(amount)
            if gateway == 'razorpay':
                from .utils import create_razorpay_order
                try:
                    order = create_razorpay_order(amount, receipt=f'wallet_{request.user.id}')
                except Exception as e:
                    if settings.DEBUG:
                        # Unique dummy order for development using timestamp
                        import time
                        order = {'id': f'dummy_ord_{request.user.id}_{int(time.time())}', 'amount': amount * 100, 'currency': 'INR'}
                    else:
                        raise e

                payment = Payment.objects.create(
                    buyer=request.user,
                    amount=amount,
                    gateway_name='Razorpay',
                    gateway_order_id=order['id'],
                    status='pending'
                )
                if settings.DEBUG:
                    return redirect('mock_payment_success', payment_id=payment.id)

                return render(request, 'payments/checkout.html', {
                    'order': order,
                    'payment': payment,
                    'gateway': 'razorpay',
                    'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', ''),
                    'is_wallet_deposit': True,
                    'debug': settings.DEBUG
                })
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
    return redirect('wallet_dashboard')

@login_required
def request_withdrawal(request):
    if request.method == "POST":
        amount_str = request.POST.get('amount', '0')
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        try:
            amount = Decimal(amount_str)
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount.")
            return redirect('wallet_dashboard')
            
        if amount > 0 and wallet.balance >= amount:
            wallet.balance -= amount
            wallet.save()
            Transaction.objects.create(
                wallet=wallet,
                amount=-amount,
                transaction_type='withdrawal',
                status='pending',
                description="Withdrawal request submitted"
            )
            # Add Notification
            Notification.objects.create(
                user=request.user,
                message=f"Your withdrawal request for ${amount} has been submitted.",
                link="/payments/wallet/"
            )
            messages.success(request, f"Withdrawal request for ${amount} submitted successfully.")
        else:
            messages.error(request, "Invalid amount or insufficient balance.")
            
    return redirect('wallet_dashboard')

@login_required
def mock_payment_success(request, payment_id):
    if not settings.DEBUG:
        return redirect('home')
        
    payment = get_object_or_404(Payment, id=payment_id, buyer=request.user)
    
    payment.status = 'completed'
    payment.save()
    
    if payment.item:
        item = payment.item
        item.status = 'sold'
        item.save()
        Transaction.objects.create(
            wallet=Wallet.objects.get_or_create(user=item.seller)[0],
            amount=payment.amount,
            transaction_type='escrow',
            status='pending',
            description=f"Mock payment held in escrow for {item.title}"
        )
    else:
        wallet, _ = Wallet.objects.get_or_create(user=payment.buyer)
        wallet.balance += payment.amount
        wallet.save()
        Transaction.objects.create(
            wallet=wallet,
            amount=payment.amount,
            transaction_type='deposit',
            status='success',
            description="Mock wallet top-up successful"
        )
        # Add Notification
        Notification.objects.create(
            user=payment.buyer,
            message=f"Mock Success! ${payment.amount} added to your wallet.",
            link="/payments/wallet/"
        )
        
    messages.success(request, f"Mock payment of ${payment.amount} successful!")
    if payment.item:
        return redirect('item_detail', pk=payment.item.id)
    return redirect('wallet_dashboard')

@login_required
def confirm_delivery(request, item_id):
    item = get_object_or_404(Item, id=item_id, buyer=request.user, status='sold', received_by_buyer=False)
    
    # Escrow Release Logic
    payment = Payment.objects.filter(item=item, status='completed').first()
    if payment:
        seller_wallet, _ = Wallet.objects.get_or_create(user=item.seller)
        
        # 1. Update pending escrow transaction to success
        escrow_tx = Transaction.objects.filter(wallet=seller_wallet, transaction_type='escrow', status='pending').last()
        if escrow_tx:
            escrow_tx.status = 'success'
            escrow_tx.save()

        # 2. Release funds to seller balance (minus commission)
        commission_setting = CommissionSetting.objects.filter(is_active=True).first()
        commission_amount = 0
        if commission_setting:
            commission_amount = (payment.amount * (commission_setting.percentage / 100)) + commission_setting.flat_fee
        
        net_amount = payment.amount - commission_amount
        seller_wallet.balance += net_amount
        seller_wallet.save()
        
        # 3. Log Release Transaction
        Transaction.objects.create(
            wallet=seller_wallet,
            amount=net_amount,
            transaction_type='release',
            status='success',
            description=f"Escrow release for {item.title} (Net after ${commission_amount} commission)"
        )

        if commission_amount > 0:
            # Optionally log commission as well
            Transaction.objects.create(
                wallet=seller_wallet,
                amount=-commission_amount,
                transaction_type='withdrawal', # Or a new type 'commission'
                status='success',
                description=f"Commission fee for {item.title}"
            )
        
        item.received_by_buyer = True
        item.save()
        messages.success(request, f"Delivery confirmed! ${net_amount} released to your wallet.")
        
        # Notify Seller
        Notification.objects.create(
            user=item.seller,
            message=f"Funds released for '{item.title}'. Net amount: ${net_amount}",
            link=f"/payments/wallet/"
        )
    
    return redirect('item_detail', pk=item.id)

@login_required
def download_invoice(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    if payment.item:
        if request.user != payment.buyer and request.user != payment.item.seller:
            messages.error(request, "Access denied.")
            return redirect('home')
    else:
        if request.user != payment.buyer:
            messages.error(request, "Access denied.")
            return redirect('home')
        
    return render(request, 'payments/invoice.html', {'payment': payment})
