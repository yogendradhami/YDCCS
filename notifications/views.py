from django.contrib.auth.decorators import login_required
from django.db.models import Count
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
    unread_by_type = {
        item["notification_type"]: item["total"]
        for item in request.user.notifications.filter(is_read=False)
        .values("notification_type")
        .annotate(total=Count("id"))
    }
    return JsonResponse(
        {
            "success": True,
            "unread_count": request.user.notifications.filter(is_read=False).count(),
            "unread_by_type": unread_by_type,
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
