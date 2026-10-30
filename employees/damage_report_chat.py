from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

from .models import PropertyDamageReportPresence


PRESENCE_TIMEOUT = timedelta(seconds=20)


def update_report_presence(report, user, is_typing=None):
    defaults = {"last_seen_at": timezone.now()}
    if is_typing is not None:
        defaults["is_typing"] = is_typing
    return PropertyDamageReportPresence.objects.update_or_create(
        report=report,
        user=user,
        defaults=defaults,
    )


def conversation_response(report, user, other_side):
    employee_user_id = report.employee.user_id if report.employee_id else None
    replies = []
    for reply in report.replies.select_related("responder").all():
        is_employee = reply.responder_id == employee_user_id
        is_mine = reply.responder_id == user.pk
        responder_name = (
            reply.responder.get_full_name() or reply.responder.get_username()
            if reply.responder
            else ("Employee" if is_employee else "Dashboard team")
        )
        replies.append(
            {
                "id": reply.pk,
                "message": reply.message,
                "author_name": "You" if is_mine else responder_name,
                "role": "employee" if is_employee else "dashboard",
                "role_label": (
                    "You"
                    if is_mine
                    else "Employee"
                    if is_employee
                    else "Dashboard"
                ),
                "mine": is_mine,
                "timestamp": timezone.localtime(reply.created_at).strftime(
                    "%d %b %Y, %I:%M %p"
                ).lstrip("0"),
                "timestamp_iso": reply.created_at.isoformat(),
            }
        )

    active_since = timezone.now() - PRESENCE_TIMEOUT
    presence_query = report.conversation_presence.filter(
        last_seen_at__gte=active_since
    ).exclude(user=user)
    if other_side == "employee":
        presence_query = presence_query.filter(user_id=employee_user_id)
    else:
        presence_query = presence_query.filter(
            user__is_staff=True,
        )
    presence = []
    for item in presence_query.select_related("user"):
        if item.user_id == employee_user_id and report.employee_id:
            name = report.employee.full_name
        else:
            name = item.user.get_full_name() or item.user.get_username()
        presence.append({"name": name, "is_typing": item.is_typing})

    return JsonResponse(
        {
            "replies": replies,
            "presence": presence,
            "status": report.status,
            "status_label": report.get_status_display(),
        }
    )
