from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)

<<<<<<< HEAD
    return JsonResponse(
        {
            "success": True,
            "unread_count": 0,
        }
    )
=======
    return JsonResponse({
        "success": True,
        "unread_count": 0,
    })
>>>>>>> 5815f15 (Initial project commit)
