from django.contrib.auth.models import User
from django.db.models.signals import post_save
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

from .models import Notification


def notify_admins(title, message, notification_type="system", link=""):
    admins = User.objects.filter(is_staff=True)

    for admin in admins:
        Notification.objects.create(
            user=admin,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )


def notify_user(user, title, message, notification_type="system", link=""):
    if user:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )


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


@receiver(post_save, sender=Booking)
def booking_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Booking Created",
            f"Booking created for {instance.customer.full_name}.",
            "booking",
            "/dashboard/bookings/",
        )

    if instance.assigned_employee and instance.assigned_employee.user:
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

    if instance.customer and instance.customer.user:
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

    if instance.booking.customer.user:
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
        notify_admins(
            "Job Photo Uploaded",
            (
                f"{instance.get_photo_type_display()} photo uploaded for booking #"
                f"{instance.booking.id}."
            ),
            "report",
            f"/reports/booking/{instance.booking.id}/",
        )

        if instance.booking.customer.user:
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
    elif instance.check_out_time:
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


@receiver(post_save, sender=LeaveRequest)
def leave_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Leave Request",
            f"{instance.employee.full_name} requested leave.",
            "leave",
            "/dashboard/leave/",
        )

    if instance.employee.user:
        notify_user(
            instance.employee.user,
            "Leave Request Updated",
            (f"Your leave request is now " f"{instance.get_status_display()}."),
            "leave",
            "/employee/leave/",
        )


@receiver(post_save, sender=Roster)
def roster_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Roster Shift Created",
            f"{instance.employee.full_name} has a new roster shift.",
            "roster",
            "/dashboard/rosters/",
        )

    if instance.employee.user:
        notify_user(
            instance.employee.user,
            "New Roster Shift",
            (
                f"You have a shift on {instance.shift_date} from "
                f"{instance.start_time} to {instance.end_time}."
            ),
            "roster",
            "/employee/roster/",
        )
