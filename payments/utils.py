import razorpay
import stripe
from django.conf import settings

# Razorpay Client
razorpay_client = razorpay.Client(auth=(
    getattr(settings, 'RAZORPAY_KEY_ID', ''), 
    getattr(settings, 'RAZORPAY_KEY_SECRET', '')
))

# Stripe API Key
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

def create_razorpay_order(amount, currency='INR', receipt=None):
    """
    Creates a Razorpay order. Amount should be in paise (e.g. 100 paise = 1 INR).
    """
    data = {
        'amount': int(amount * 100), 
        'currency': currency,
        'receipt': receipt,
        'payment_capture': 1  # Auto capture
    }
    return razorpay_client.order.create(data=data)

def verify_razorpay_signature(params):
    """
    Verifies the signature returned by Razorpay.
    """
    return razorpay_client.utility.verify_payment_signature(params)

def create_stripe_checkout_session(amount, item_name, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session.
    """
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': item_name,
                },
                'unit_amount': int(amount * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session

def generate_paytm_checksum(params):
    """
    Placeholder for Paytm checksum generation.
    In a real app, use paytmchecksum library.
    """
    # Dummy logic for now
    return "DUMMY_PAYTM_CHECKSUM"
