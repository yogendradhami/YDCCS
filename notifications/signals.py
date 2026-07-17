<<<<<<< HEAD
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

=======
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Notification

from quotes.models import QuoteRequest
from bookings.models import Booking, JobPhoto
from customers.models import Customer
from employees.models import Employee
from invoices.models import Invoice
from gallery.models import GalleryItem
from reviews.models import Review
from contracts.models import CleaningContract
from attendance.models import AttendanceLog
from payroll.models import PayrollRecord
from leave_management.models import LeaveRequest
from rosters.models import Roster

>>>>>>> 5815f15 (Initial project commit)

def notify_admins(title, message, notification_type="system", link=""):
    admins = User.objects.filter(is_staff=True)

    for admin in admins:
        Notification.objects.create(
            user=admin,
            title=title,
            message=message,
            notification_type=notification_type,
<<<<<<< HEAD
            link=link,
=======
            link=link
>>>>>>> 5815f15 (Initial project commit)
        )


def notify_user(user, title, message, notification_type="system", link=""):
    if user:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
<<<<<<< HEAD
            link=link,
=======
            link=link
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=QuoteRequest)
def quote_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Quote Request",
            f"{instance.name} submitted a new quote request.",
            "quote",
<<<<<<< HEAD
            "/dashboard/leads/",
=======
            "/dashboard/leads/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=Customer)
def customer_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Customer Added",
            f"{instance.full_name} was added as a customer.",
            "customer",
<<<<<<< HEAD
            "/dashboard/customers/",
=======
            "/dashboard/customers/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=Employee)
def employee_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Employee Added",
            f"{instance.full_name} was added as an employee.",
            "employee",
<<<<<<< HEAD
            "/dashboard/employees/",
=======
            "/dashboard/employees/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=Booking)
def booking_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Booking Created",
            f"Booking created for {instance.customer.full_name}.",
            "booking",
<<<<<<< HEAD
            "/dashboard/bookings/",
=======
            "/dashboard/bookings/"
>>>>>>> 5815f15 (Initial project commit)
        )

    if instance.assigned_employee and instance.assigned_employee.user:
        notify_user(
            instance.assigned_employee.user,
            "Booking Assigned",
<<<<<<< HEAD
            (
                f"You have a job: {instance.service_type} on "
                f"{instance.booking_date}."
            ),
            "booking",
            f"/employee/jobs/{instance.id}/",
=======
            f"You have a job: {instance.service_type} on {instance.booking_date}.",
            "booking",
            f"/employee/jobs/{instance.id}/"
>>>>>>> 5815f15 (Initial project commit)
        )

    if instance.customer and instance.customer.user:
        notify_user(
            instance.customer.user,
            "Booking Updated",
<<<<<<< HEAD
            (
                f"Your booking for {instance.service_type} is now "
                f"{instance.get_status_display()}."
            ),
            "booking",
            f"/portal/bookings/{instance.id}/",
=======
            f"Your booking for {instance.service_type} is now {instance.get_status_display()}.",
            "booking",
            f"/portal/bookings/{instance.id}/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=Invoice)
def invoice_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Invoice Created",
            f"Invoice {instance.invoice_number} created.",
            "invoice",
<<<<<<< HEAD
            "/dashboard/invoices/",
=======
            "/dashboard/invoices/"
>>>>>>> 5815f15 (Initial project commit)
        )

    if instance.booking.customer.user:
        notify_user(
            instance.booking.customer.user,
            "Invoice Updated",
<<<<<<< HEAD
            (
                f"Invoice {instance.invoice_number} is now "
                f"{instance.get_status_display()}."
            ),
            "invoice",
            f"/portal/invoices/{instance.id}/",
=======
            f"Invoice {instance.invoice_number} is now {instance.get_status_display()}.",
            "invoice",
            f"/portal/invoices/{instance.id}/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=GalleryItem)
def gallery_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "Gallery Updated",
            "A new gallery item was added.",
            "gallery",
<<<<<<< HEAD
            "/dashboard/gallery/",
=======
            "/dashboard/gallery/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=Review)
def review_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Review Added",
            "A new customer review was added.",
            "review",
<<<<<<< HEAD
            "/dashboard/reviews/",
=======
            "/dashboard/reviews/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=JobPhoto)
def job_photo_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "Job Photo Uploaded",
<<<<<<< HEAD
            (
                f"{instance.get_photo_type_display()} photo uploaded for booking #"
                f"{instance.booking.id}."
            ),
            "report",
            f"/reports/booking/{instance.booking.id}/",
=======
            f"{instance.get_photo_type_display()} photo uploaded for booking #{instance.booking.id}.",
            "report",
            f"/reports/booking/{instance.booking.id}/"
>>>>>>> 5815f15 (Initial project commit)
        )

        if instance.booking.customer.user:
            notify_user(
                instance.booking.customer.user,
                "Job Photo Uploaded",
<<<<<<< HEAD
                (
                    f"A {instance.get_photo_type_display()} photo was uploaded "
                    f"for your booking."
                ),
                "report",
                f"/portal/bookings/{instance.booking.id}/",
=======
                f"A {instance.get_photo_type_display()} photo was uploaded for your booking.",
                "report",
                f"/portal/bookings/{instance.booking.id}/"
>>>>>>> 5815f15 (Initial project commit)
            )


@receiver(post_save, sender=CleaningContract)
def contract_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Recurring Contract",
            f"Recurring contract created for {instance.customer.full_name}.",
            "contract",
<<<<<<< HEAD
            "/dashboard/contracts/",
=======
            "/dashboard/contracts/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=AttendanceLog)
def attendance_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "Employee Checked In",
<<<<<<< HEAD
            (
                f"{instance.employee.full_name} checked in for booking #"
                f"{instance.booking.id}."
            ),
            "attendance",
            "/dashboard/attendance/",
=======
            f"{instance.employee.full_name} checked in for booking #{instance.booking.id}.",
            "attendance",
            "/dashboard/attendance/"
>>>>>>> 5815f15 (Initial project commit)
        )
    elif instance.check_out_time:
        notify_admins(
            "Employee Checked Out",
<<<<<<< HEAD
            (
                f"{instance.employee.full_name} checked out. Total hours: "
                f"{instance.total_hours}."
            ),
            "attendance",
            "/dashboard/attendance/",
=======
            f"{instance.employee.full_name} checked out. Total hours: {instance.total_hours}.",
            "attendance",
            "/dashboard/attendance/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=PayrollRecord)
def payroll_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "Payroll Record Created",
            f"Payroll created for {instance.employee.full_name}.",
            "payroll",
<<<<<<< HEAD
            "/dashboard/payroll/",
=======
            "/dashboard/payroll/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=LeaveRequest)
def leave_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Leave Request",
            f"{instance.employee.full_name} requested leave.",
            "leave",
<<<<<<< HEAD
            "/dashboard/leave/",
=======
            "/dashboard/leave/"
>>>>>>> 5815f15 (Initial project commit)
        )

    if instance.employee.user:
        notify_user(
            instance.employee.user,
            "Leave Request Updated",
<<<<<<< HEAD
            (f"Your leave request is now " f"{instance.get_status_display()}."),
            "leave",
            "/employee/leave/",
=======
            f"Your leave request is now {instance.get_status_display()}.",
            "leave",
            "/employee/leave/"
>>>>>>> 5815f15 (Initial project commit)
        )


@receiver(post_save, sender=Roster)
def roster_notification(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            "New Roster Shift Created",
            f"{instance.employee.full_name} has a new roster shift.",
            "roster",
<<<<<<< HEAD
            "/dashboard/rosters/",
=======
            "/dashboard/rosters/"
>>>>>>> 5815f15 (Initial project commit)
        )

    if instance.employee.user:
        notify_user(
            instance.employee.user,
            "New Roster Shift",
<<<<<<< HEAD
            (
                f"You have a shift on {instance.shift_date} from "
                f"{instance.start_time} to {instance.end_time}."
            ),
            "roster",
            "/employee/roster/",
        )
=======
            f"You have a shift on {instance.shift_date} from {instance.start_time} to {instance.end_time}.",
            "roster",
            "/employee/roster/"
        )
>>>>>>> 5815f15 (Initial project commit)
