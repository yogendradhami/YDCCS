from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .utils import (
    NOTIFICATION_AREAS,
    invalidate_notification_count_cache,
    notifications_for_area,
)


@login_required
@require_POST
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    invalidate_notification_count_cache(request.user)

    return JsonResponse(
        {
            "success": True,
            "unread_count": 0,
        }
    )


@login_required
@require_POST
def mark_notification_area_read(request, area):
    area_path = NOTIFICATION_AREAS.get(area)
    if area_path is None:
        return JsonResponse(
            {"success": False, "error": "Unknown notification area."},
            status=400,
        )

    updated = notifications_for_area(request.user, area).filter(
        is_read=False
    ).update(is_read=True)
    invalidate_notification_count_cache(request.user)
    return JsonResponse({"success": True, "updated": updated})


@login_required
@require_GET
def notification_status(request):
    from django.db.models import Case, IntegerField, Value, When

    area_cases = [
        When(link__startswith=path, then=Value(index))
        for index, path in enumerate(NOTIFICATION_AREAS.values())
    ]
    area_keys = list(NOTIFICATION_AREAS)
    unread_by_area = {
        area_keys[row["area_index"]]: row["total"]
        for row in request.user.notifications.filter(is_read=False)
        .annotate(
            area_index=Case(
                *area_cases,
                default=Value(-1),
                output_field=IntegerField(),
            )
        )
        .exclude(area_index=-1)
        .values("area_index")
        .annotate(total=Count("id"))
    }
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
            "unread_by_area": unread_by_area,
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
