from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from attendance.models import AttendanceLog
from bookings.models import Booking, JobPhoto
from contracts.models import CleaningContract
from customers.models import Customer
from employees.models import Employee
from gallery.models import GalleryItem
from invoices.models import Invoice
from leave_management.models import LeaveRequest
from payroll.models import PayrollRecord
from quotes.models import QuoteRequest
from reviews.models import Review
from rosters.models import Roster

from .utils import notify_admins, notify_user


@receiver(post_save, sender=QuoteRequest)
def quote_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Quote Request",
            f"{instance.name} submitted a new quote request.",
            "quote",
            "/dashboard/leads/",
        )


@receiver(post_save, sender=Customer)
def customer_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Customer Added",
            f"{instance.full_name} was added as a customer.",
            "customer",
            "/dashboard/customers/",
        )


@receiver(post_save, sender=Employee)
def employee_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Employee Added",
            f"{instance.full_name} was added as an employee.",
            "employee",
            "/dashboard/employees/",
        )


@receiver(pre_save, sender=Booking)
def remember_booking_notification_state(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values(
            "status", "assigned_employee_id"
        ).first()
    instance._notification_previous_status = previous["status"] if previous else None
    instance._notification_previous_employee_id = (
        previous["assigned_employee_id"] if previous else None
    )


@receiver(post_save, sender=Booking)
def booking_notification(sender, instance, created, **kwargs):
    if created:
        customer_name = (
            instance.customer.full_name if instance.customer else "No customer"
        )
        notify_admins(
            "New Booking Created",
            f"Booking created for {customer_name}.",
            "booking",
            "/dashboard/bookings/",
        )

    employee_assignment_changed = created or (
        instance.assigned_employee_id != getattr(
            instance, "_notification_previous_employee_id", None
        )
    )
    if (
        employee_assignment_changed
        and instance.assigned_employee
        and instance.assigned_employee.user
    ):
        notify_user(
            instance.assigned_employee.user,
            "Booking Assigned",
            (
                f"You have a job: {instance.service_type} on "
                f"{instance.booking_date}."
            ),
            "booking",
            f"/employee/jobs/{instance.id}/",
        )

    status_changed = created or (
        instance.status
        != getattr(instance, "_notification_previous_status", instance.status)
    )
    if (
        status_changed
        and not getattr(
            instance,
            "_suppress_customer_status_notification",
            False,
        )
        and instance.customer
        and instance.customer.user
    ):
        notify_user(
            instance.customer.user,
            "Booking Updated",
            (
                f"Your booking for {instance.service_type} is now "
                f"{instance.get_status_display()}."
            ),
            "booking",
            f"/portal/bookings/{instance.id}/",
        )


@receiver(post_save, sender=Invoice)
def invoice_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Invoice Created",
            f"Invoice {instance.invoice_number} created.",
            "invoice",
            "/dashboard/invoices/",
        )

    if instance.booking.customer and instance.booking.customer.user:
        notify_user(
            instance.booking.customer.user,
            "Invoice Updated",
            (
                f"Invoice {instance.invoice_number} is now "
                f"{instance.get_status_display()}."
            ),
            "invoice",
            f"/portal/invoices/{instance.id}/",
        )


@receiver(post_save, sender=GalleryItem)
def gallery_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "Gallery Updated",
            "A new gallery item was added.",
            "gallery",
            "/dashboard/gallery/",
        )


@receiver(post_save, sender=Review)
def review_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Review Added",
            "A new customer review was added.",
            "review",
            "/dashboard/reviews/",
        )


@receiver(post_save, sender=JobPhoto)
def job_photo_notification(sender, instance, created, **kwargs):
    if created:
        uploader = instance.employee.full_name if instance.employee else "An employee"
        notify_admins(
            "Job Photo Uploaded",
            (
                f"{uploader} uploaded a {instance.get_photo_type_display().lower()} "
                f"photo for booking #{instance.booking.id}."
            ),
            "report",
            f"/reports/booking/{instance.booking.id}/",
        )

        if instance.booking.customer and instance.booking.customer.user:
            notify_user(
                instance.booking.customer.user,
                "Job Photo Uploaded",
                (
                    f"A {instance.get_photo_type_display()} photo was uploaded "
                    f"for your booking."
                ),
                "report",
                f"/portal/bookings/{instance.booking.id}/",
            )


@receiver(post_save, sender=CleaningContract)
def contract_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Recurring Contract",
            f"Recurring contract created for {instance.customer.full_name}.",
            "contract",
            "/dashboard/contracts/",
        )


@receiver(pre_save, sender=AttendanceLog)
def remember_attendance_notification_state(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values("check_out_time").first()
    instance._notification_previous_check_out = (
        previous["check_out_time"] if previous else None
    )


@receiver(post_save, sender=AttendanceLog)
def attendance_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "Employee Checked In",
            (
                f"{instance.employee.full_name} checked in for booking #"
                f"{instance.booking.id}."
            ),
            "attendance",
            "/dashboard/attendance/",
        )
    elif (
        instance.check_out_time
        and not getattr(instance, "_notification_previous_check_out", None)
    ):
        notify_admins(
            "Employee Checked Out",
            (
                f"{instance.employee.full_name} checked out. Total hours: "
                f"{instance.total_hours}."
            ),
            "attendance",
            "/dashboard/attendance/",
        )


@receiver(post_save, sender=PayrollRecord)
def payroll_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "Payroll Record Created",
            f"Payroll created for {instance.employee.full_name}.",
            "payroll",
            "/dashboard/payroll/",
        )


@receiver(pre_save, sender=LeaveRequest)
def remember_leave_notification_state(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values("status").first()
    instance._notification_previous_status = previous["status"] if previous else None


@receiver(post_save, sender=LeaveRequest)
def leave_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Leave Request",
            f"{instance.employee.full_name} requested leave.",
            "leave",
            "/dashboard/leave/",
        )

    status_changed = not created and instance.status != getattr(
        instance, "_notification_previous_status", instance.status
    )
    if status_changed and instance.employee.user:
        notify_user(
            instance.employee.user,
            "Leave Request Updated",
            (f"Your leave request is now " f"{instance.get_status_display()}."),
            "leave",
            "/employee/leave/",
        )
    if status_changed:
        notify_admins(
            "Leave Request Updated",
            (
                f"{instance.employee.full_name}'s leave request is now "
                f"{instance.get_status_display()}."
            ),
            "leave",
            "/dashboard/leave/",
        )


@receiver(pre_save, sender=Roster)
def remember_roster_notification_state(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values(
            "shift_date", "start_time", "end_time", "employee_id", "booking_id", "status"
        ).first()
    instance._notification_previous_roster = previous


@receiver(post_save, sender=Roster)
def roster_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Roster Shift Created",
            f"{instance.employee.full_name} has a new roster shift.",
            "roster",
            "/dashboard/rosters/",
        )

    previous = getattr(instance, "_notification_previous_roster", None)
    shift_changed = created or (
        previous
        and any(
            previous[field] != getattr(instance, field)
            for field in (
                "shift_date",
                "start_time",
                "end_time",
                "employee_id",
                "booking_id",
                "status",
            )
        )
    )
    if shift_changed and not created:
        notify_admins(
            "Roster Shift Updated",
            f"{instance.employee.full_name}'s roster shift for {instance.shift_date} was updated.",
            "roster",
            "/dashboard/rosters/",
        )
    if shift_changed and instance.employee.user:
        title = "New Roster Shift" if created else "Roster Shift Updated"
        message = (
            f"You have a shift on {instance.shift_date} from "
            f"{instance.start_time} to {instance.end_time}."
            if instance.status != "cancelled"
            else f"Your shift on {instance.shift_date} was cancelled."
        )
        notify_user(
            instance.employee.user,
            title,
            message,
            "roster",
            "/employee/roster/",
        )
