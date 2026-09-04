from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST


@login_required
@require_POST
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)

    return JsonResponse(
        {
            "success": True,
            "unread_count": 0,
        }
    )


@login_required
@require_GET
def notification_status(request):
    notifications = request.user.notifications.all()[:10]
    return JsonResponse(
        {
            "success": True,
            "unread_count": request.user.notifications.filter(is_read=False).count(),
            "notifications": [
                {
                    "title": notification.title,
                    "message": notification.message,
                    "link": notification.link or "#",
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.strftime("%d %b, %I:%M %p"),
                }
                for notification in notifications
            ],
        }
    )
