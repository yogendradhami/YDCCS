from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import AttendanceLog


def sync_roster_attendance(roster):
    """Keep allocated attendance hours aligned with a non-cancelled roster."""
    using = roster._state.db or "default"
    with transaction.atomic(using=using):
        roster = (
            roster.__class__.objects.using(using)
            .select_related("booking", "employee")
            .select_for_update()
            .get(pk=roster.pk)
        )
        allocated_log = (
            AttendanceLog.objects.using(using)
            .select_for_update()
            .filter(roster=roster)
            .first()
        )

        if roster.status == "cancelled":
            if allocated_log:
                allocated_log.delete()
            return None

        portal_log = (
            AttendanceLog.objects.using(using)
            .filter(
                booking=roster.booking,
                employee=roster.employee,
                source=AttendanceLog.Source.PORTAL,
                check_out_time__isnull=False,
            )
            .order_by("created_at", "pk")
            .first()
        )
        if portal_log:
            if allocated_log:
                allocated_log.delete()
            return portal_log

        start = datetime.combine(roster.shift_date, roster.start_time)
        end_date = roster.shift_date
        if roster.end_time <= roster.start_time:
            end_date += timedelta(days=1)
        end = datetime.combine(end_date, roster.end_time)
        current_timezone = timezone.get_current_timezone()
        check_in_time = timezone.make_aware(start, current_timezone)
        check_out_time = timezone.make_aware(end, current_timezone)
        total_hours = Decimal(
            str((check_out_time - check_in_time).total_seconds() / 3600)
        ).quantize(Decimal("0.01"))

        defaults = {
            "booking": roster.booking,
            "employee": roster.employee,
            "source": AttendanceLog.Source.ROSTER,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "total_hours": total_hours,
        }
        if allocated_log:
            for field, value in defaults.items():
                setattr(allocated_log, field, value)
            allocated_log.save(update_fields=list(defaults))
            return allocated_log

        return AttendanceLog.objects.using(using).create(
            roster=roster,
            **defaults,
        )
