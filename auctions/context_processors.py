from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        return {
            'notifications_list': Notification.objects.filter(user=request.user).order_by('-created_at')[:10],
            'unread_notifications_count': Notification.objects.filter(user=request.user, is_read=False).count()
        }
    return {}
