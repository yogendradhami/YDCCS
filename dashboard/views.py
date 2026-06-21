# ==========================================================
# Create Activity Log Entry
# ==========================================================


def create_activity_log(user, action_type, title, description=""):
    ActivityLog.objects.create(
        user=user, action_type=action_type, title=title, description=description
    )


import csv
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage, send_mail
from django.db.models import Avg, Count, F, Max, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from attendance.models import AttendanceLog
from bookings.forms import BookingForm
from bookings.models import Booking
from contracts.models import CleaningContract
from customers.forms import CustomerForm
from customers.models import Customer
from dashboard.models import CampaignLog, CleaningSupply, Equipment, Vehicle
from employees.forms import EmployeeForm
from employees.models import Employee
from expenses.models import Expense
from gallery.forms import GalleryItemForm
from gallery.models import GalleryItem
from google_reviews.calendar_utils import (
    create_or_update_booking_event,
    delete_booking_event,
)
from invoices.models import Invoice
from invoices.pdf_utils import generate_invoice_pdf
from leave_management.models import LeaveRequest
from notifications.models import Notification
from payroll.models import PayrollRecord
from quotes.models import QuoteRequest
from reviews.forms import ReviewForm
from reviews.models import Review

# Company settings form
from .forms import CompanySettingsForm
from .models import (
    ActivityLog,
    CompanySettings,
    EmailLog,
    PurchaseOrder,
    ReviewRequestLog,
)


@login_required
def dashboard_home(request):
    today = timezone.now().date()
    week_start = today - timedelta(days=7)
    overdue_date = today - timedelta(days=2)
    month_start = today.replace(day=1)

    active_vehicles = Vehicle.objects.filter(status="active").count()

    vehicle_alerts = (
        Vehicle.objects.filter(insurance_expiry__lt=today).count()
        + Vehicle.objects.filter(registration_expiry__lt=today).count()
        + Vehicle.objects.filter(service_due_date__lt=today).count()
    )

    insurance_expiring = Vehicle.objects.filter(
        insurance_expiry__lte=today + timedelta(days=30), insurance_expiry__gte=today
    ).count()

    service_due = Vehicle.objects.filter(
        service_due_date__lte=today + timedelta(days=30), service_due_date__gte=today
    ).count()

    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today).count()

    due_today_equipment = Equipment.objects.filter(next_service_date=today).count()

    active_equipment = Equipment.objects.exclude(condition="retired").count()

    total_equipment_value = (
        Equipment.objects.aggregate(total=Sum("purchase_cost"))["total"] or 0
    )

    low_stock_supplies = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    ).count()

    total_supplies = CleaningSupply.objects.count()

    total_supplies_value = sum(
        item.total_value() for item in CleaningSupply.objects.all()
    )

    new_quotes = QuoteRequest.objects.filter(status="new").count()
    contacted_quotes = QuoteRequest.objects.filter(status="contacted").count()
    quoted_quotes = QuoteRequest.objects.filter(status="quoted").count()
    booked_quotes = QuoteRequest.objects.filter(status="booked").count()
    completed_quotes = QuoteRequest.objects.filter(status="completed").count()
    lost_quotes = QuoteRequest.objects.filter(status="lost").count()

    pending_bookings = Booking.objects.filter(status="pending").count()
    confirmed_bookings = Booking.objects.filter(status="confirmed").count()
    assigned_bookings = Booking.objects.filter(status="assigned").count()
    in_progress_bookings = Booking.objects.filter(status="in_progress").count()
    completed_bookings = Booking.objects.filter(status="completed").count()
    cancelled_bookings = Booking.objects.filter(status="cancelled").count()

    booking_revenue = (
        Booking.objects.filter(status="completed").aggregate(total=Sum("quoted_price"))[
            "total"
        ]
        or 0
    )

    unassigned_jobs = (
        Booking.objects.filter(assigned_employee__isnull=True, booking_date__gte=today)
        .exclude(status="cancelled")
        .order_by("booking_date", "booking_time")[:10]
    )

    urgent_jobs_today = (
        Booking.objects.filter(booking_date=today)
        .exclude(status="cancelled")
        .order_by("booking_time")[:10]
    )

    overdue_leads = QuoteRequest.objects.filter(
        status__in=["new", "contacted", "quoted"], created_at__date__lte=overdue_date
    ).order_by("created_at")[:10]

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .order_by("booking_date", "booking_time")[:10]
    )

    employee_workload = (
        Booking.objects.filter(assigned_employee__isnull=False, booking_date__gte=today)
        .exclude(status="cancelled")
        .values("assigned_employee__full_name")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )

    property_type_data = (
        QuoteRequest.objects.values("property_type")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    quote_trend_data = (
        QuoteRequest.objects.filter(created_at__date__gte=week_start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    booking_trend_data = (
        Booking.objects.filter(created_at__date__gte=week_start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    revenue_trend_data = (
        Booking.objects.filter(status="completed", booking_date__gte=week_start)
        .values("booking_date")
        .annotate(total=Sum("quoted_price"))
        .order_by("booking_date")
    )

    action_alert_count = (
        unassigned_jobs.count()
        + urgent_jobs_today.count()
        + overdue_leads.count()
        + pending_bookings
    )
    recent_activity = ActivityLog.objects.select_related("user").all()[:10]
    context = {
        "recent_activity": recent_activity,
        "total_quotes": QuoteRequest.objects.count(),
        "today_quotes": QuoteRequest.objects.filter(created_at__date=today).count(),
        "week_quotes": QuoteRequest.objects.filter(
            created_at__date__gte=week_start
        ).count(),
        "month_quotes": QuoteRequest.objects.filter(
            created_at__date__gte=month_start
        ).count(),
        "new_quotes": new_quotes,
        "contacted_quotes": contacted_quotes,
        "quoted_quotes": quoted_quotes,
        "booked_quotes": booked_quotes,
        "completed_quotes": completed_quotes,
        "lost_quotes": lost_quotes,
        "gallery_count": GalleryItem.objects.count(),
        "reviews_count": Review.objects.count(),
        "customer_count": Customer.objects.count(),
        "employee_count": Employee.objects.count(),
        "available_employees": Employee.objects.filter(
            availability="available", active=True
        ).count(),
        "active_employees": Employee.objects.filter(active=True).count(),
        "total_bookings": Booking.objects.count(),
        "today_bookings": Booking.objects.filter(booking_date=today).count(),
        "upcoming_bookings": Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .count(),
        "completed_bookings": completed_bookings,
        "booking_revenue": booking_revenue,
        "pending_bookings": pending_bookings,
        "confirmed_bookings": confirmed_bookings,
        "assigned_bookings": assigned_bookings,
        "in_progress_bookings": in_progress_bookings,
        "cancelled_bookings": cancelled_bookings,
        "overdue_equipment": overdue_equipment,
        "due_today_equipment": due_today_equipment,
        "active_equipment": active_equipment,
        "total_equipment_value": total_equipment_value,
        "low_stock_supplies": low_stock_supplies,
        "total_supplies": total_supplies,
        "total_supplies_value": total_supplies_value,
        "recent_quotes": QuoteRequest.objects.order_by("-created_at")[:15],
        "recent_customers": Customer.objects.order_by("-created_at")[:5],
        "recent_employees": Employee.objects.order_by("-created_at")[:5],
        "upcoming_jobs": upcoming_jobs,
        "urgent_jobs_today": urgent_jobs_today,
        "unassigned_jobs": unassigned_jobs,
        "overdue_leads": overdue_leads,
        "employee_workload": employee_workload,
        "action_alert_count": action_alert_count,
        "active_vehicles": active_vehicles,
        "vehicle_alerts": vehicle_alerts,
        "insurance_expiring": insurance_expiring,
        "service_due": service_due,
        "property_type_labels": [item["property_type"] for item in property_type_data],
        "property_type_counts": [item["total"] for item in property_type_data],
        "quote_trend_labels": [
            item["day"].strftime("%d %b") for item in quote_trend_data
        ],
        "quote_trend_counts": [item["total"] for item in quote_trend_data],
        "booking_trend_labels": [
            item["day"].strftime("%d %b") for item in booking_trend_data
        ],
        "booking_trend_counts": [item["total"] for item in booking_trend_data],
        "revenue_trend_labels": [
            item["booking_date"].strftime("%d %b") for item in revenue_trend_data
        ],
        "revenue_trend_counts": [
            float(item["total"] or 0) for item in revenue_trend_data
        ],
    }

    return render(request, "dashboard.html", context)


@login_required
def lead_list(request):
    quotes = QuoteRequest.objects.all().order_by("-created_at")
    return render(request, "lead_list.html", {"quotes": quotes})


@login_required
def update_quote_status(request, quote_id):
    quote = get_object_or_404(QuoteRequest, id=quote_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        admin_notes = request.POST.get("admin_notes", "")

        if new_status in dict(QuoteRequest.STATUS_CHOICES):
            quote.status = new_status
            quote.admin_notes = admin_notes
            quote.save()

    return redirect("lead_list")


@login_required
def customer_list(request):
    customers = Customer.objects.all().order_by("-created_at")
    return render(request, "customer_list.html", {"customers": customers})


@login_required
def add_customer(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)

        if form.is_valid():
            customer = form.save()

            # Save activity log when a customer is created.
            create_activity_log(
                request.user,
                "customer",
                "Customer Added",
                f"{customer.full_name} was added to the CRM.",
            )

            messages.success(request, "✅ Customer added successfully.")
            return redirect("customer_list")

        messages.error(request, "❌ Please check the customer form.")
    else:
        form = CustomerForm()

    return render(
        request,
        "customer_form.html",
        {
            "form": form,
            "page_title": "Add Customer",
            "button_text": "Save Customer",
        },
    )


@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)

        if form.is_valid():
            updated_customer = form.save()

            # Save activity log when customer details are updated.
            create_activity_log(
                request.user,
                "customer",
                "Customer Updated",
                f"{updated_customer.full_name}'s details were updated.",
            )

            messages.success(request, "✅ Customer updated successfully.")
            return redirect("customer_list")

        messages.error(request, "❌ Please check the customer form.")
    else:
        form = CustomerForm(instance=customer)

    return render(
        request,
        "customer_form.html",
        {
            "form": form,
            "page_title": "Edit Customer",
            "button_text": "Update Customer",
        },
    )


@login_required
def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    customer_name = customer.full_name

    if request.method == "POST":
        customer.delete()

        # Save activity log when a customer is deleted.
        create_activity_log(
            request.user,
            "customer",
            "Customer Deleted",
            f"{customer_name} was removed from the CRM.",
        )

        messages.success(request, "✅ Customer deleted successfully.")
        return redirect("customer_list")

    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": customer.full_name,
            "cancel_url": "/dashboard/customers/",
        },
    )


@login_required
def booking_list(request):
    bookings = Booking.objects.all().order_by("-booking_date", "-booking_time")
    return render(request, "booking_list.html", {"bookings": bookings})


@login_required
def add_booking(request):
    if request.method == "POST":
        form = BookingForm(request.POST)

        if form.is_valid():
            # booking = form.save()

            booking = form.save()

            try:
                create_or_update_booking_event(booking)
            except Exception as error:
                messages.warning(
                    request, f"Booking saved, but Google Calendar sync failed: {error}"
                )

            if booking.assigned_employee and booking.assigned_employee.user:
                Notification.objects.create(
                    user=booking.assigned_employee.user,
                    title="New Job Assigned",
                    message=(
                        f"You have been assigned "
                        f"{booking.service_type} on "
                        f"{booking.booking_date} at "
                        f"{booking.booking_time}."
                    ),
                    notification_type="booking",
                    link="/employee/jobs/",
                )

            create_activity_log(
                request.user,
                "booking",
                "Booking Created",
                f"{booking.customer.full_name} - {booking.service_type} on {booking.booking_date}",
            )

            messages.success(request, "✅ Booking created successfully.")
            return redirect("booking_list")

    else:
        form = BookingForm()

    return render(
        request,
        "booking_form.html",
        {
            "form": form,
            "page_title": "Add New Booking",
            "button_text": "Save Booking",
        },
    )


@login_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == "POST":
        form = BookingForm(request.POST, instance=booking)

        if form.is_valid():
            # updated_booking = form.save()

            updated_booking = form.save()

            if updated_booking.status == "completed":

                existing_invoice = Invoice.objects.filter(
                    booking=updated_booking
                ).first()

                if existing_invoice:

                    messages.info(
                        request,
                        f"Invoice already exists: {existing_invoice.invoice_number}",
                    )

                else:

                    invoice = Invoice.objects.create(
                        booking=updated_booking,
                        amount=updated_booking.quoted_price,
                        description=(
                            f"{updated_booking.service_type} "
                            f"completed on "
                            f"{updated_booking.booking_date}"
                        ),
                        notes=updated_booking.notes,
                    )

                    messages.success(
                        request,
                        f"Invoice automatically created: {invoice.invoice_number}",
                    )

            try:
                create_or_update_booking_event(updated_booking)
            except Exception as error:
                messages.warning(
                    request,
                    f"Booking updated, but Google Calendar sync failed: {error}",
                )

            if (
                updated_booking.assigned_employee
                and updated_booking.assigned_employee.user
            ):
                Notification.objects.create(
                    user=updated_booking.assigned_employee.user,
                    title="Booking Updated",
                    message=(
                        f"Booking updated: "
                        f"{updated_booking.service_type} "
                        f"on {updated_booking.booking_date} "
                        f"at {updated_booking.booking_time}."
                    ),
                    notification_type="booking",
                    link="/employee/jobs/",
                )

            create_activity_log(
                request.user,
                "booking",
                "Booking Updated",
                f"{updated_booking.customer.full_name} - {updated_booking.service_type} on {updated_booking.booking_date}",
            )

            messages.success(request, "✅ Booking updated successfully.")
            return redirect("booking_list")

    else:
        form = BookingForm(instance=booking)

    return render(
        request,
        "booking_form.html",
        {
            "form": form,
            "page_title": "Edit Booking",
            "button_text": "Update Booking",
        },
    )


@login_required
def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    booking_name = f"{booking.customer.full_name} - {booking.service_type} on {booking.booking_date}"

    if request.method == "POST":
        try:
            delete_booking_event(booking)
        except Exception as error:
            messages.warning(
                request,
                f"Booking deleted, but Google Calendar event could not be removed: {error}",
            )

        booking.delete()

        create_activity_log(request.user, "booking", "Booking Deleted", booking_name)

        messages.success(request, "✅ Booking deleted successfully.")
        return redirect("booking_list")

    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": booking_name,
            "cancel_url": "/dashboard/bookings/",
        },
    )


@login_required
def booking_calendar(request):
    today = timezone.now().date()

    start_date = request.GET.get("start")

    if start_date:
        try:
            week_start = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            week_start = today
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    bookings = (
        Booking.objects.filter(booking_date__gte=week_start, booking_date__lte=week_end)
        .exclude(status="cancelled")
        .select_related("customer", "assigned_employee")
        .order_by("booking_date", "booking_time")
    )

    week_days = []

    # for i in range(7):
    #     day = week_start + timedelta(days=i)

    #     day_bookings = bookings.filter(
    #         booking_date=day
    #     )

    for i in range(7):
        day = week_start + timedelta(days=i)

        day_bookings = bookings.filter(booking_date=day)

        day_leave = LeaveRequest.objects.filter(
            status="approved", start_date__lte=day, end_date__gte=day
        ).select_related("employee")

        week_days.append(
            {
                "date": day,
                "bookings": day_bookings,
                "leave_requests": day_leave,
            }
        )

    today_jobs = (
        Booking.objects.filter(booking_date=today).exclude(status="cancelled").count()
    )

    tomorrow_jobs = (
        Booking.objects.filter(booking_date=today + timedelta(days=1))
        .exclude(status="cancelled")
        .count()
    )

    week_jobs = bookings.count()

    unassigned_jobs = bookings.filter(assigned_employee__isnull=True).count()

    return render(
        request,
        "booking_calendar.html",
        {
            "week_days": week_days,
            "week_start": week_start,
            "week_end": week_end,
            "previous_week": previous_week,
            "next_week": next_week,
            "today_jobs": today_jobs,
            "tomorrow_jobs": tomorrow_jobs,
            "week_jobs": week_jobs,
            "unassigned_jobs": unassigned_jobs,
        },
    )


@login_required
def employee_list(request):
    employees = Employee.objects.all().order_by("-created_at")
    return render(request, "employee_list.html", {"employees": employees})


@login_required
def add_employee(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)

        if form.is_valid():
            employee = form.save()

            # ==================================================
            # Activity Log
            # ==================================================
            create_activity_log(
                request.user,
                "employee",
                "Employee Added",
                f"{employee.full_name} was added to the employee database.",
            )

            messages.success(request, "✅ Employee added successfully.")

            return redirect("employee_list")

        messages.error(request, "❌ Please check the employee form.")

    else:
        form = EmployeeForm()

    return render(
        request,
        "employee_form.html",
        {
            "form": form,
            "page_title": "Add Employee",
            "button_text": "Save Employee",
        },
    )


@login_required
def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)

        if form.is_valid():
            updated_employee = form.save()

            # ==================================================
            # Activity Log
            # ==================================================
            create_activity_log(
                request.user,
                "employee",
                "Employee Updated",
                f"{updated_employee.full_name}'s profile was updated.",
            )

            messages.success(request, "✅ Employee updated successfully.")

            return redirect("employee_list")

        messages.error(request, "❌ Please check the employee form.")

    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "employee_form.html",
        {
            "form": form,
            "page_title": "Edit Employee",
            "button_text": "Update Employee",
        },
    )


@login_required
def delete_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)

    employee_name = employee.full_name

    if request.method == "POST":

        employee.delete()

        # ==================================================
        # Activity Log
        # ==================================================
        create_activity_log(
            request.user,
            "employee",
            "Employee Deleted",
            f"{employee_name} was removed from the employee database.",
        )

        messages.success(request, "✅ Employee deleted successfully.")

        return redirect("employee_list")

    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": employee_name,
            "cancel_url": "/dashboard/employees/",
        },
    )


@login_required
def gallery_list(request):
    items = GalleryItem.objects.all().order_by("-id")
    return render(request, "dashboard_gallery_list.html", {"items": items})


@login_required
def add_gallery_item(request):
    if request.method == "POST":
        form = GalleryItemForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Gallery item added successfully.")
            return redirect("gallery_list")

        messages.error(request, "❌ Please check the gallery form.")
    else:
        form = GalleryItemForm()

    return render(
        request,
        "dashboard_gallery_form.html",
        {
            "form": form,
            "page_title": "Add Gallery Item",
            "button_text": "Save Gallery Item",
        },
    )


@login_required
def edit_gallery_item(request, item_id):
    item = get_object_or_404(GalleryItem, id=item_id)

    if request.method == "POST":
        form = GalleryItemForm(request.POST, request.FILES, instance=item)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Gallery item updated successfully.")
            return redirect("gallery_list")

        messages.error(request, "❌ Please check the gallery form.")
    else:
        form = GalleryItemForm(instance=item)

    return render(
        request,
        "dashboard_gallery_form.html",
        {
            "form": form,
            "page_title": "Edit Gallery Item",
            "button_text": "Update Gallery Item",
        },
    )


@login_required
def delete_gallery_item(request, item_id):
    item = get_object_or_404(GalleryItem, id=item_id)

    if request.method == "POST":
        item.delete()
        messages.success(request, "✅ Gallery item deleted successfully.")
        return redirect("gallery_list")

    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": str(item),
            "cancel_url": "/dashboard/gallery/",
        },
    )


@login_required
def review_list(request):
    reviews = Review.objects.all().order_by("-id")
    return render(request, "dashboard_review_list.html", {"reviews": reviews})


@login_required
def add_review(request):
    if request.method == "POST":
        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save()

            create_activity_log(
                request.user,
                "review",
                "Review Added",
                f"{review.customer_name} review added with {review.rating} stars.",
            )

            messages.success(request, "✅ Review added successfully.")
            return redirect("review_list")

        messages.error(request, "❌ Please check the review form.")
    else:
        initial_data = {}

        customer_name = request.GET.get("customer_name")
        suburb = request.GET.get("suburb")

        if customer_name:
            initial_data["customer_name"] = customer_name

        if suburb:
            initial_data["suburb"] = suburb

        form = ReviewForm(initial=initial_data)

    return render(
        request,
        "dashboard_review_form.html",
        {
            "form": form,
            "page_title": "Add Review",
            "button_text": "Save Review",
        },
    )


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)

        if form.is_valid():
            updated_review = form.save()

            create_activity_log(
                request.user,
                "review",
                "Review Updated",
                f"{updated_review.customer_name} review was updated.",
            )

            messages.success(request, "✅ Review updated successfully.")
            return redirect("review_list")

        messages.error(request, "❌ Please check the review form.")
    else:
        form = ReviewForm(instance=review)

    return render(
        request,
        "dashboard_review_form.html",
        {
            "form": form,
            "page_title": "Edit Review",
            "button_text": "Update Review",
        },
    )


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    review_name = review.customer_name

    if request.method == "POST":
        review.delete()

        create_activity_log(
            request.user,
            "review",
            "Review Deleted",
            f"{review_name} review was deleted.",
        )

        messages.success(request, "✅ Review deleted successfully.")
        return redirect("review_list")

    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": str(review),
            "cancel_url": "/dashboard/reviews/",
        },
    )


@login_required
def export_quotes_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="yd-cleaning-quotes.csv"'

    writer = csv.writer(response)

    writer.writerow(
        [
            "Name",
            "Email",
            "Phone",
            "Property Type",
            "Suburb/Postcode",
            "Preferred Date",
            "Status",
            "Admin Notes",
            "Message",
            "Created At",
        ]
    )

    for quote in QuoteRequest.objects.all().order_by("-created_at"):
        writer.writerow(
            [
                quote.name,
                quote.email,
                quote.phone,
                quote.property_type,
                quote.suburb_postcode,
                quote.preferred_date,
                quote.get_status_display(),
                quote.admin_notes,
                quote.message,
                quote.created_at,
            ]
        )

    return response


@login_required
def attendance_report(request):
    logs = AttendanceLog.objects.select_related(
        "employee", "booking", "booking__customer"
    ).order_by("-check_in_time", "-created_at")

    return render(request, "attendance_report.html", {"logs": logs})


@login_required
def company_settings(request):
    # Get the first company settings record.
    # If it does not exist, create one automatically.
    settings, created = CompanySettings.objects.get_or_create(id=1)

    if request.method == "POST":
        # Use request.FILES because logo/favicon are file uploads.
        form = CompanySettingsForm(request.POST, request.FILES, instance=settings)

        if form.is_valid():
            form.save()

            # ==================================================
            # Activity Log
            # ==================================================
            create_activity_log(
                request.user,
                "settings",
                "Company Settings Updated",
                "Business settings, branding, contact details or invoice settings were updated.",
            )

            messages.success(request, "✅ Company settings updated successfully.")

            return redirect("company_settings")

        messages.error(request, "❌ Please check the settings form.")

    else:
        form = CompanySettingsForm(instance=settings)

    return render(
        request,
        "company_settings.html",
        {
            "form": form,
            "settings": settings,
        },
    )


# ==========================================================
# Employee Performance Dashboard
# Purpose:
# Show employee jobs, hours, payroll and revenue performance.
# ==========================================================


@login_required
def employee_performance(request):
    employees = Employee.objects.filter(active=True).order_by("full_name")

    performance_rows = []

    for employee in employees:
        jobs_completed = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        ).count()

        assigned_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue_generated = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        attendance_logs = AttendanceLog.objects.filter(
            employee=employee, check_out_time__isnull=False
        )

        total_hours = 0

        for log in attendance_logs:
            if log.total_hours:
                total_hours += float(log.total_hours)

        payroll_total = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        revenue_per_hour = 0
        efficiency = 0

        if total_hours > 0:
            revenue_per_hour = round(float(revenue_generated) / total_hours, 2)

        if payroll_total > 0:
            efficiency = round(
                (float(revenue_generated) / float(payroll_total)) * 100, 2
            )

        revenue_per_hour = 0
        efficiency = 0

        if total_hours > 0:
            revenue_per_hour = round(float(revenue_generated) / total_hours, 2)

        if payroll_total > 0:
            efficiency = round(
                (float(revenue_generated) / float(payroll_total)) * 100, 2
            )

        performance_rows.append(
            {
                "employee": employee,
                "assigned_jobs": assigned_jobs,
                "jobs_completed": jobs_completed,
                "total_hours": round(total_hours, 2),
                "revenue_generated": revenue_generated,
                "payroll_total": payroll_total,
                "revenue_per_hour": revenue_per_hour,
                "efficiency": efficiency,
            }
        )

    # ==================================================
    # Sort employees by efficiency (highest first)
    # ==================================================

    performance_rows = sorted(
        performance_rows, key=lambda row: row["efficiency"], reverse=True
    )

    top_performer = performance_rows[0] if performance_rows else None

    highest_revenue = max(
        performance_rows, key=lambda row: row["revenue_generated"], default=None
    )

    most_jobs_completed = max(
        performance_rows, key=lambda row: row["jobs_completed"], default=None
    )

    highest_efficiency = max(
        performance_rows, key=lambda row: row["efficiency"], default=None
    )

    employee_labels = [row["employee"].full_name for row in performance_rows]

    revenue_data = [float(row["revenue_generated"]) for row in performance_rows]

    jobs_data = [row["jobs_completed"] for row in performance_rows]

    efficiency_data = [float(row["efficiency"]) for row in performance_rows]

    return render(
        request,
        "employee_performance.html",
        {
            "performance_rows": performance_rows,
            "top_performer": top_performer,
            "highest_revenue": highest_revenue,
            "most_jobs_completed": most_jobs_completed,
            "highest_efficiency": highest_efficiency,
            "employee_labels": employee_labels,
            "revenue_data": revenue_data,
            "jobs_data": jobs_data,
            "efficiency_data": efficiency_data,
        },
    )


# ==========================================================
# Activity Log Dashboard
# Purpose:
# Show recent CRM actions.
# ==========================================================


@login_required
def activity_log_list(request):

    activities = ActivityLog.objects.select_related("user").all()[:200]

    return render(request, "activity_log.html", {"activities": activities})


# ==========================================================
# Business Health Dashboard
# Purpose:
# Owner-level overview of revenue, quotes, payroll and jobs.
# ==========================================================


@login_required
def business_health(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)
    total_revenue = (
        Booking.objects.filter(status="completed").aggregate(total=Sum("quoted_price"))[
            "total"
        ]
        or 0
    )

    monthly_revenue = (
        Booking.objects.filter(
            status="completed", booking_date__gte=month_start
        ).aggregate(total=Sum("quoted_price"))["total"]
        or 0
    )

    completed_jobs = Booking.objects.filter(status="completed").count()

    average_job_value = 0

    if completed_jobs > 0:
        average_job_value = round(float(total_revenue) / completed_jobs, 2)

    total_quotes = QuoteRequest.objects.count()
    booked_quotes = QuoteRequest.objects.filter(status="booked").count()

    quote_conversion_rate = 0

    if total_quotes > 0:
        quote_conversion_rate = round((booked_quotes / total_quotes) * 100, 2)

    payroll_total = (
        PayrollRecord.objects.aggregate(total=Sum("gross_pay"))["total"] or 0
    )

    payroll_cost_percent = 0

    if total_revenue > 0:
        payroll_cost_percent = round(
            (float(payroll_total) / float(total_revenue)) * 100, 2
        )

    top_service = (
        Booking.objects.filter(status="completed")
        .values("service_type")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    top_employee = (
        Booking.objects.filter(status="completed", assigned_employee__isnull=False)
        .values("assigned_employee__full_name")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .count()
    )

    pending_bookings = Booking.objects.filter(status="pending").count()

    return render(
        request,
        "business_health.html",
        {
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "completed_jobs": completed_jobs,
            "average_job_value": average_job_value,
            "quote_conversion_rate": quote_conversion_rate,
            "payroll_total": payroll_total,
            "payroll_cost_percent": payroll_cost_percent,
            "top_service": top_service,
            "top_employee": top_employee,
            "upcoming_jobs": upcoming_jobs,
            "pending_bookings": pending_bookings,
        },
    )


@login_required
def financial_dashboard(request):
    today = timezone.now().date()
    week_start = today - timedelta(days=7)
    week_due_end = today + timedelta(days=7)

    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    today_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date=today).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    week_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date__gte=week_start).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    month_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date__gte=month_start).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    year_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date__gte=year_start).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    paid_invoices = Invoice.objects.filter(status="paid").count()
    unpaid_invoices = Invoice.objects.exclude(status="paid").count()
    overdue_invoices = Invoice.objects.filter(status="overdue").count()

    due_this_week = Invoice.objects.filter(
        status__in=["draft", "sent", "overdue"],
        due_date__gte=today,
        due_date__lte=week_due_end,
    ).count()

    outstanding_balance = (
        Invoice.objects.exclude(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    payroll_total = (
        PayrollRecord.objects.aggregate(total=Sum("gross_pay"))["total"] or 0
    )

    estimated_profit = float(year_revenue) - float(payroll_total)

    recent_outstanding_invoices = (
        Invoice.objects.exclude(status="paid")
        .select_related("booking", "booking__customer")
        .order_by("due_date", "-created_at")[:10]
    )

    # -----------------------------
    # Revenue Trend Chart
    # -----------------------------
    revenue_trend = (
        Invoice.objects.filter(status="paid")
        .annotate(day=TruncDate("paid_at"))
        .values("day")
        .annotate(total=Sum("total_amount"))
        .order_by("day")
    )

    revenue_labels = [
        item["day"].strftime("%d %b") for item in revenue_trend if item["day"]
    ]

    revenue_values = [float(item["total"] or 0) for item in revenue_trend]

    # -----------------------------
    # Top Customers
    # -----------------------------
    top_customers = Customer.objects.order_by("-total_revenue")[:10]

    customer_labels = [customer.full_name for customer in top_customers]

    customer_values = [float(customer.total_revenue) for customer in top_customers]

    return render(
        request,
        "financial_dashboard.html",
        {
            "today_revenue": today_revenue,
            "week_revenue": week_revenue,
            "month_revenue": month_revenue,
            "year_revenue": year_revenue,
            "paid_invoices": paid_invoices,
            "unpaid_invoices": unpaid_invoices,
            "overdue_invoices": overdue_invoices,
            "due_this_week": due_this_week,
            "outstanding_balance": outstanding_balance,
            "payroll_total": payroll_total,
            "estimated_profit": estimated_profit,
            "recent_outstanding_invoices": recent_outstanding_invoices,
            "revenue_labels": revenue_labels,
            "revenue_values": revenue_values,
            "customer_labels": customer_labels,
            "customer_values": customer_values,
        },
    )


@login_required
def executive_dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    monthly_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date__gte=month_start).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    outstanding_balance = (
        Invoice.objects.exclude(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    payroll_total = (
        PayrollRecord.objects.aggregate(total=Sum("gross_pay"))["total"] or 0
    )

    profit_estimate = float(total_revenue) - float(payroll_total)

    payroll_percent = 0
    if total_revenue:
        payroll_percent = round((float(payroll_total) / float(total_revenue)) * 100, 2)

    total_quotes = QuoteRequest.objects.count()
    booked_quotes = QuoteRequest.objects.filter(status="booked").count()

    conversion_rate = 0
    if total_quotes:
        conversion_rate = round((booked_quotes / total_quotes) * 100, 2)

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .count()
    )

    pending_bookings = Booking.objects.filter(status="pending").count()

    top_service = (
        Booking.objects.filter(status="completed")
        .values("service_type")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    top_employee = (
        Booking.objects.filter(status="completed", assigned_employee__isnull=False)
        .values("assigned_employee__full_name")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    recent_activity = ActivityLog.objects.select_related("user").all()[:10]

    return render(
        request,
        "executive_dashboard.html",
        {
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "outstanding_balance": outstanding_balance,
            "payroll_total": payroll_total,
            "profit_estimate": profit_estimate,
            "payroll_percent": payroll_percent,
            "conversion_rate": conversion_rate,
            "upcoming_jobs": upcoming_jobs,
            "pending_bookings": pending_bookings,
            "top_service": top_service,
            "top_employee": top_employee,
            "recent_activity": recent_activity,
        },
    )


@login_required
def reminder_center(request):
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    overdue_quote_date = today - timedelta(days=2)

    overdue_invoices = (
        Invoice.objects.exclude(status="paid")
        .filter(due_date__lt=today)
        .order_by("due_date")
    )

    jobs_tomorrow = (
        Booking.objects.filter(booking_date=tomorrow)
        .exclude(status="cancelled")
        .order_by("booking_time")
    )

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today, booking_date__lte=week_end)
        .exclude(status="cancelled")
        .order_by("booking_date", "booking_time")
    )

    unassigned_jobs = (
        Booking.objects.filter(assigned_employee__isnull=True, booking_date__gte=today)
        .exclude(status="cancelled")
        .order_by("booking_date", "booking_time")
    )

    pending_quotes = QuoteRequest.objects.filter(
        status__in=["new", "contacted", "quoted"],
        created_at__date__lte=overdue_quote_date,
    ).order_by("created_at")

    urgent_count = (
        overdue_invoices.count() + unassigned_jobs.count() + pending_quotes.count()
    )

    return render(
        request,
        "reminder_center.html",
        {
            "today": today,
            "tomorrow": tomorrow,
            "overdue_invoices": overdue_invoices,
            "jobs_tomorrow": jobs_tomorrow,
            "upcoming_jobs": upcoming_jobs,
            "unassigned_jobs": unassigned_jobs,
            "pending_quotes": pending_quotes,
            "urgent_count": urgent_count,
        },
    )


# ==========================================================
# Email Center
# Purpose:
# Send invoice reminders, booking reminders and quote follow-ups.
# ==========================================================


@login_required
def email_center(request):
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    overdue_quote_date = today - timedelta(days=2)

    overdue_invoices = (
        Invoice.objects.exclude(status="paid")
        .filter(due_date__lt=today)
        .order_by("due_date")
    )

    tomorrow_bookings = (
        Booking.objects.filter(booking_date=tomorrow)
        .exclude(status="cancelled")
        .order_by("booking_time")
    )

    quote_followups = QuoteRequest.objects.filter(
        status__in=["new", "contacted", "quoted"],
        created_at__date__lte=overdue_quote_date,
    ).order_by("created_at")

    return render(
        request,
        "email_center.html",
        {
            "overdue_invoices": overdue_invoices,
            "tomorrow_bookings": tomorrow_bookings,
            "quote_followups": quote_followups,
        },
    )


@login_required
def send_invoice_reminder(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    customer = invoice.booking.customer

    if request.method == "POST":
        if customer.email:
            subject = f"Payment Reminder - Invoice {invoice.invoice_number}"

            message = f"""
Dear {customer.full_name},

This is a friendly reminder that your invoice {invoice.invoice_number} is currently outstanding.

Invoice Amount: ${invoice.total_amount}
Due Date: {invoice.due_date}

Please complete payment at your earliest convenience.

Thank you,
YD Commercial Cleaning Services
"""

            email = EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
            )

            pdf_buffer = generate_invoice_pdf(invoice)

            email.attach(
                f"{invoice.invoice_number}.pdf",
                pdf_buffer.getvalue(),
                "application/pdf",
            )

            email.send(fail_silently=False)

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="invoice_reminder",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object=invoice.invoice_number,
            )

            create_activity_log(
                request.user,
                "invoice",
                "Invoice Reminder Sent",
                f"Reminder sent for {invoice.invoice_number} to {customer.full_name}.",
            )

            messages.success(request, "✅ Invoice reminder email sent successfully.")
        else:
            messages.error(request, "❌ Customer does not have an email address.")

    return redirect("email_center")


@login_required
def send_booking_reminder(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    customer = booking.customer

    if request.method == "POST":
        if customer.email:
            subject = "Cleaning Booking Reminder"

            message = f"""
Dear {customer.full_name},

This is a reminder for your upcoming cleaning booking.

Service: {booking.service_type}
Date: {booking.booking_date}
Time: {booking.booking_time}
Address: {booking.address}, {booking.suburb_postcode}

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="booking_reminder",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object=f"Booking #{booking.id}",
            )

            create_activity_log(
                request.user,
                "booking",
                "Booking Reminder Sent",
                f"Reminder sent to {customer.full_name} for booking #{booking.id}.",
            )

            messages.success(request, "✅ Booking reminder email sent successfully.")
        else:
            messages.error(request, "❌ Customer does not have an email address.")

    return redirect("email_center")


@login_required
def send_quote_followup(request, quote_id):
    quote = get_object_or_404(QuoteRequest, id=quote_id)

    if request.method == "POST":
        if quote.email:
            subject = "Following Up On Your Cleaning Quote"

            message = f"""
Dear {quote.name},

Thank you for requesting a cleaning quote from YD Commercial Cleaning Services.

We are just following up to see if you would like to proceed or if you have any questions.

Service/Property Type: {quote.property_type}
Suburb/Postcode: {quote.suburb_postcode}
Preferred Date: {quote.preferred_date}

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [quote.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="quote_followup",
                recipient_name=quote.name,
                recipient_email=quote.email,
                subject=subject,
                related_object=f"Quote #{quote.id}",
            )

            create_activity_log(
                request.user,
                "quote",
                "Quote Follow-up Sent",
                f"Follow-up email sent to {quote.name}.",
            )

            messages.success(request, "✅ Quote follow-up email sent successfully.")
        else:
            messages.error(request, "❌ Quote request does not have an email address.")

    return redirect("email_center")


@login_required
def email_log_list(request):
    email_logs = EmailLog.objects.select_related("sent_by").all()[:200]

    return render(request, "email_log_list.html", {"email_logs": email_logs})


@login_required
def customer_analytics(request):

    total_customers = Customer.objects.count()

    current_month = timezone.now().month
    current_year = timezone.now().year

    new_customers = Customer.objects.filter(
        created_at__month=current_month, created_at__year=current_year
    ).count()

    repeat_customers = Customer.objects.filter(jobs_completed__gt=1).count()

    retention_rate = 0

    if total_customers > 0:
        retention_rate = round((repeat_customers / total_customers) * 100, 2)

    top_customers = Customer.objects.order_by("-total_revenue")[:10]

    customer_labels = [customer.full_name for customer in top_customers]

    revenue_data = [float(customer.total_revenue) for customer in top_customers]

    booking_data = [customer.jobs_completed for customer in top_customers]

    return render(
        request,
        "customer_analytics.html",
        {
            "total_customers": total_customers,
            "new_customers": new_customers,
            "repeat_customers": repeat_customers,
            "retention_rate": retention_rate,
            "top_customers": top_customers,
            "customer_labels": customer_labels,
            "revenue_data": revenue_data,
            "booking_data": booking_data,
        },
    )


@login_required
def review_requests(request):

    completed_bookings = (
        Booking.objects.filter(status="completed")
        .select_related("customer")
        .prefetch_related("review_request_log")
        .order_by("-booking_date")
    )

    return render(
        request, "review_requests.html", {"completed_bookings": completed_bookings}
    )


@login_required
def send_review_request(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)

    customer = booking.customer

    if request.method == "POST":

        if customer.email:

            subject = "Thank You For Choosing " "YD Commercial Cleaning"

            review_link = "https://g.page/r/CXH9ygKf16Y4EBM/review"

            message = f"""
Dear {customer.full_name},

Thank you for choosing YD Commercial Cleaning Services.

We hope you were happy with the service.

Would you mind leaving us a quick Google review?

{review_link}

Your feedback helps our business grow.

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object=f"Review Request Booking #{booking.id}",
            )

            review_log, created = ReviewRequestLog.objects.get_or_create(
                booking=booking,
                defaults={
                    "sent_by": request.user,
                    "sent_count": 1,
                    "last_sent_at": timezone.now(),
                },
            )

            if not created:
                review_log.sent_count += 1
                review_log.sent_by = request.user
                review_log.last_sent_at = timezone.now()
                review_log.save()

            create_activity_log(
                request.user,
                "review",
                "Review Request Sent",
                f"Review request sent to {customer.full_name}",
            )

            messages.success(request, "✅ Review request email sent.")

    return redirect("review_requests")


@login_required
def review_analytics(request):
    total_reviews = Review.objects.count()

    featured_reviews = Review.objects.filter(featured=True).count()

    average_rating = Review.objects.aggregate(average=Avg("rating"))["average"] or 0

    average_rating = round(average_rating, 2)

    five_star_reviews = Review.objects.filter(rating=5).count()

    review_requests_sent = ReviewRequestLog.objects.count()

    review_conversion_rate = 0

    if review_requests_sent > 0:
        review_conversion_rate = round((total_reviews / review_requests_sent) * 100, 2)

    rating_breakdown = {
        "five": Review.objects.filter(rating=5).count(),
        "four": Review.objects.filter(rating=4).count(),
        "three": Review.objects.filter(rating=3).count(),
        "two": Review.objects.filter(rating=2).count(),
        "one": Review.objects.filter(rating=1).count(),
    }

    latest_reviews = Review.objects.order_by("-created_at")[:10]

    return render(
        request,
        "review_analytics.html",
        {
            "total_reviews": total_reviews,
            "featured_reviews": featured_reviews,
            "average_rating": average_rating,
            "five_star_reviews": five_star_reviews,
            "review_requests_sent": review_requests_sent,
            "review_conversion_rate": review_conversion_rate,
            "rating_breakdown": rating_breakdown,
            "latest_reviews": latest_reviews,
        },
    )


@login_required
def customer_loyalty(request):

    customers = Customer.objects.all().order_by("-total_revenue")

    vip_count = 0
    repeat_count = 0
    new_count = 0

    loyalty_rows = []

    for customer in customers:

        if customer.total_revenue >= 1000 or customer.jobs_completed >= 5:
            level = "VIP"
            vip_count += 1

        elif customer.jobs_completed >= 2:
            level = "Repeat"
            repeat_count += 1

        else:
            level = "New"
            new_count += 1

        loyalty_rows.append(
            {
                "customer": customer,
                "level": level,
            }
        )

    return render(
        request,
        "customer_loyalty.html",
        {
            "loyalty_rows": loyalty_rows,
            "vip_count": vip_count,
            "repeat_count": repeat_count,
            "new_count": new_count,
            "total_customers": customers.count(),
        },
    )


@login_required
def customer_profile_360(request, customer_id):

    customer = get_object_or_404(Customer, id=customer_id)

    bookings = Booking.objects.filter(customer=customer).order_by("-booking_date")

    invoices = Invoice.objects.filter(booking__customer=customer).order_by(
        "-created_at"
    )

    reviews = Review.objects.filter(customer_name=customer.full_name).order_by(
        "-created_at"
    )

    email_logs = EmailLog.objects.filter(recipient_email=customer.email).order_by(
        "-sent_at"
    )[:20]

    total_bookings = bookings.count()

    outstanding_invoices = invoices.exclude(status="paid").count()

    total_quotes = QuoteRequest.objects.filter(email=customer.email).count()

    completed_bookings = bookings.filter(status="completed").count()

    total_spent = customer.total_revenue

    customer_lifetime_value = 0

    if total_bookings > 0:

        customer_lifetime_value = round(total_spent / total_bookings, 2)

    last_booking = bookings.first()

    customer_risk = "New Customer"

    if last_booking:

        days_since_last_booking = (
            timezone.localdate() - last_booking.booking_date
        ).days

        if days_since_last_booking >= 120:
            customer_risk = "High Risk"

        elif days_since_last_booking >= 60:
            customer_risk = "Medium Risk"

        else:
            customer_risk = "Active Customer"
    else:
        days_since_last_booking = None

    loyalty_level = "New"

    if customer.total_revenue >= 1000 or customer.jobs_completed >= 5:
        loyalty_level = "VIP"

    elif customer.jobs_completed >= 2:
        loyalty_level = "Repeat"

    timeline_events = []

    for booking in bookings:
        timeline_events.append(
            {
                "date": booking.created_at,
                "type": "Booking",
                "title": "Booking Created",
                "description": f"{booking.service_type} booked for {booking.booking_date}",
            }
        )

        if booking.status == "completed":
            timeline_events.append(
                {
                    "date": timezone.make_aware(
                        datetime.combine(booking.booking_date, time.min)
                    ),
                    "type": "Job",
                    "title": "Job Completed",
                    "description": f"{booking.service_type} marked as completed.",
                }
            )

    for invoice in invoices:
        timeline_events.append(
            {
                "date": invoice.created_at,
                "type": "Invoice",
                "title": "Invoice Created",
                "description": f"{invoice.invoice_number} - ${invoice.total_amount}",
            }
        )

        if invoice.status == "paid" and invoice.paid_at:
            timeline_events.append(
                {
                    "date": invoice.paid_at,
                    "type": "Payment",
                    "title": "Invoice Paid",
                    "description": f"{invoice.invoice_number} was paid.",
                }
            )

    for review in reviews:
        timeline_events.append(
            {
                "date": review.created_at,
                "type": "Review",
                "title": "Review Added",
                "description": f"{review.rating} star review added.",
            }
        )

    for email in email_logs:
        timeline_events.append(
            {
                "date": email.sent_at,
                "type": "Email",
                "title": email.get_email_type_display(),
                "description": email.subject,
            }
        )

    timeline_events = sorted(
        timeline_events,
        key=lambda item: (
            datetime.combine(item["date"], time.min)
            if not isinstance(item["date"], datetime)
            else item["date"]
        ),
        reverse=True,
    )

    return render(
        request,
        "customer_profile_360.html",
        {
            "customer": customer,
            "bookings": bookings,
            "invoices": invoices,
            "reviews": reviews,
            "email_logs": email_logs,
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "outstanding_invoices": outstanding_invoices,
            "total_quotes": total_quotes,
            "total_spent": total_spent,
            "customer_lifetime_value": customer_lifetime_value,
            "customer_risk": customer_risk,
            "days_since_last_booking": days_since_last_booking,
            "loyalty_level": loyalty_level,
            "timeline_events": timeline_events,
        },
    )


@login_required
def employee_bonuses(request):
    employees = Employee.objects.filter(active=True).order_by("full_name")

    bonus_rows = []

    total_bonus = 0
    top_bonus_employee = None

    for employee in employees:
        completed_bookings = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        )

        jobs_completed = completed_bookings.count()

        revenue_generated = (
            completed_bookings.aggregate(total=Sum("quoted_price"))["total"] or 0
        )

        # Bonus Rule:
        # 5% of revenue generated from completed jobs.
        revenue_bonus = float(revenue_generated) * 0.05

        # Bonus Rule:
        # $10 per completed job.
        job_bonus = jobs_completed * 10

        total_employee_bonus = round(revenue_bonus + job_bonus, 2)

        total_bonus += total_employee_bonus

        row = {
            "employee": employee,
            "jobs_completed": jobs_completed,
            "revenue_generated": revenue_generated,
            "revenue_bonus": round(revenue_bonus, 2),
            "job_bonus": job_bonus,
            "total_bonus": total_employee_bonus,
        }

        bonus_rows.append(row)

        if (
            top_bonus_employee is None
            or total_employee_bonus > top_bonus_employee["total_bonus"]
        ):
            top_bonus_employee = row

    bonus_rows = sorted(bonus_rows, key=lambda row: row["total_bonus"], reverse=True)

    return render(
        request,
        "employee_bonuses.html",
        {
            "bonus_rows": bonus_rows,
            "total_bonus": round(total_bonus, 2),
            "top_bonus_employee": top_bonus_employee,
            "bonus_rate": 5,
            "job_bonus_amount": 10,
        },
    )


@login_required
def campaign_center(request):

    vip_customers = Customer.objects.filter(total_revenue__gte=1000)

    inactive_customers = Customer.objects.annotate(
        last_booking=Max("bookings__booking_date")
    )

    review_opportunities = Booking.objects.filter(status="completed")

    campaigns_sent = CampaignLog.objects.count()

    campaign_history = CampaignLog.objects.all()[:20]

    return render(
        request,
        "campaign_center.html",
        {
            "vip_count": vip_customers.count(),
            "inactive_count": inactive_customers.count(),
            "review_count": review_opportunities.count(),
            "campaigns_sent": campaigns_sent,
            "campaign_history": campaign_history,
        },
    )


@login_required
def send_vip_campaign(request):
    vip_customers = Customer.objects.filter(total_revenue__gte=1000).exclude(email="")

    sent_count = 0

    if request.method == "POST":
        for customer in vip_customers:
            subject = "Exclusive Offer from YD Commercial Cleaning Services"

            message = f"""
Dear {customer.full_name},

Thank you for being one of our valued VIP customers.

YD Commercial Cleaning Services appreciates your continued support.

We would like to offer you priority booking access and exclusive promotions.

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object="VIP Customer Campaign",
            )

            sent_count += 1

        CampaignLog.objects.create(
            sent_by=request.user,
            campaign_type="vip",
            title="VIP Customer Campaign",
            recipients_count=sent_count,
        )

        create_activity_log(
            request.user,
            "customer",
            "VIP Campaign Sent",
            f"VIP campaign sent to {sent_count} customers.",
        )

        messages.success(request, f"✅ VIP campaign sent to {sent_count} customers.")

    return redirect("campaign_center")


@login_required
def send_inactive_campaign(request):
    inactive_customers = Customer.objects.filter(jobs_completed__lte=1).exclude(
        email=""
    )

    sent_count = 0

    if request.method == "POST":
        for customer in inactive_customers:
            subject = "We Miss You - YD Commercial Cleaning Services"

            message = f"""
Dear {customer.full_name},

We have not seen you for a while.

YD Commercial Cleaning Services would love to help with your next cleaning service.

Book again and enjoy a special returning customer offer.

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object="Inactive Customer Campaign",
            )

            sent_count += 1

        CampaignLog.objects.create(
            sent_by=request.user,
            campaign_type="inactive",
            title="Inactive Customer Campaign",
            recipients_count=sent_count,
        )

        create_activity_log(
            request.user,
            "customer",
            "Inactive Customer Campaign Sent",
            f"Inactive customer campaign sent to {sent_count} customers.",
        )

        messages.success(
            request, f"✅ Inactive campaign sent to {sent_count} customers."
        )

    return redirect("campaign_center")


@login_required
def send_review_campaign(request):
    completed_bookings = Booking.objects.filter(status="completed").select_related(
        "customer"
    )

    sent_count = 0

    if request.method == "POST":
        for booking in completed_bookings:
            customer = booking.customer

            if not customer.email:
                continue

            subject = "Would You Leave a Review for YD Commercial Cleaning Services?"

            review_link = "https://g.page/r/CXH9ygKf16Y4EBM/review"

            message = f"""
Dear {customer.full_name},

Thank you for choosing YD Commercial Cleaning Services.

Your feedback helps YD Commercial Cleaning Services continue providing excellent service.

Would you mind leaving us a quick Google review?

{review_link}

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object=f"Review Campaign Booking #{booking.id}",
            )

            sent_count += 1

        CampaignLog.objects.create(
            sent_by=request.user,
            campaign_type="review",
            title="Review Follow-up Campaign",
            recipients_count=sent_count,
        )

        create_activity_log(
            request.user,
            "review",
            "Review Campaign Sent",
            f"Review campaign sent to {sent_count} customers.",
        )

        messages.success(request, f"✅ Review campaign sent to {sent_count} customers.")

    return redirect("campaign_center")


@login_required
def campaign_preview(request, campaign_type):

    recipients = []
    title = ""

    if campaign_type == "vip":
        title = "VIP Campaign Recipients"

        recipients = (
            Customer.objects.filter(total_revenue__gte=1000)
            .exclude(email="")
            .order_by("-total_revenue")
        )

    elif campaign_type == "inactive":
        title = "Inactive Campaign Recipients"

        recipients = (
            Customer.objects.filter(jobs_completed__lte=1)
            .exclude(email="")
            .order_by("full_name")
        )

    elif campaign_type == "review":
        title = "Review Campaign Recipients"

        completed_bookings = Booking.objects.filter(status="completed").select_related(
            "customer"
        )

        customer_ids = []

        for booking in completed_bookings:
            if booking.customer.email:
                customer_ids.append(booking.customer.id)

        recipients = Customer.objects.filter(id__in=customer_ids).order_by("full_name")

    else:
        messages.error(request, "Invalid campaign type.")
        return redirect("campaign_center")

    return render(
        request,
        "campaign_preview.html",
        {
            "campaign_type": campaign_type,
            "title": title,
            "recipients": recipients,
            "recipient_count": recipients.count(),
        },
    )


@login_required
def campaign_performance(request):

    campaigns = CampaignLog.objects.all()

    total_campaigns = campaigns.count()

    total_emails_sent = sum(campaign.recipients_count for campaign in campaigns)

    vip_campaigns = campaigns.filter(campaign_type="vip").count()

    inactive_campaigns = campaigns.filter(campaign_type="inactive").count()

    review_campaigns = campaigns.filter(campaign_type="review").count()

    campaign_type_totals = {
        "VIP Campaign": vip_campaigns,
        "Inactive Campaign": inactive_campaigns,
        "Review Campaign": review_campaigns,
    }

    top_campaign = (
        max(campaign_type_totals, key=campaign_type_totals.get)
        if total_campaigns
        else "N/A"
    )

    return render(
        request,
        "campaign_performance.html",
        {
            "campaigns": campaigns[:50],
            "total_campaigns": total_campaigns,
            "total_emails_sent": total_emails_sent,
            "vip_campaigns": vip_campaigns,
            "inactive_campaigns": inactive_campaigns,
            "review_campaigns": review_campaigns,
            "top_campaign": top_campaign,
        },
    )


@login_required
def profit_loss_dashboard(request):
    paid_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    payroll_cost = PayrollRecord.objects.aggregate(total=Sum("gross_pay"))["total"] or 0

    completed_bookings = Booking.objects.filter(status="completed")

    bonus_cost = 0

    for employee in Employee.objects.filter(active=True):
        employee_bookings = completed_bookings.filter(assigned_employee=employee)

        revenue_generated = (
            employee_bookings.aggregate(total=Sum("quoted_price"))["total"] or 0
        )

        jobs_completed = employee_bookings.count()

        revenue_bonus = float(revenue_generated) * 0.05
        job_bonus = jobs_completed * 10

        bonus_cost += revenue_bonus + job_bonus

    expense_cost = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

    estimated_profit = (
        float(paid_revenue)
        - float(payroll_cost)
        - float(bonus_cost)
        - float(expense_cost)
    )

    profit_margin = 0

    if paid_revenue:
        profit_margin = round((estimated_profit / float(paid_revenue)) * 100, 2)

    return render(
        request,
        "profit_loss_dashboard.html",
        {
            "paid_revenue": paid_revenue,
            "payroll_cost": payroll_cost,
            "bonus_cost": round(bonus_cost, 2),
            "expense_cost": expense_cost,
            "estimated_profit": round(estimated_profit, 2),
            "profit_margin": profit_margin,
        },
    )


@login_required
def business_kpis(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    today_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date=today).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    month_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date__gte=month_start).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    outstanding_invoices = (
        Invoice.objects.exclude(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    payroll_month = (
        PayrollRecord.objects.filter(period_end__gte=month_start).aggregate(
            total=Sum("gross_pay")
        )["total"]
        or 0
    )

    completed_jobs_month = Booking.objects.filter(
        status="completed", booking_date__gte=month_start
    ).count()

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .count()
    )

    active_customers = Customer.objects.count()

    new_customers_month = Customer.objects.filter(
        created_at__date__gte=month_start
    ).count()

    total_employees = Employee.objects.filter(active=True).count()

    average_rating = Review.objects.aggregate(average=Avg("rating"))["average"] or 0

    average_rating = round(average_rating, 2)

    reviews_received = Review.objects.count()

    campaigns_sent = CampaignLog.objects.count()

    vip_customers = Customer.objects.filter(total_revenue__gte=1000).count()

    estimated_profit_month = float(month_revenue) - float(payroll_month)

    profit_margin = 0

    if month_revenue:
        profit_margin = round((estimated_profit_month / float(month_revenue)) * 100, 2)

    health_score = 0

    if month_revenue > 0:
        health_score += 25

    if profit_margin > 20:
        health_score += 25
    elif profit_margin > 0:
        health_score += 15

    if average_rating >= 4.5:
        health_score += 20
    elif average_rating >= 4:
        health_score += 15

    if new_customers_month > 0:
        health_score += 15

    if outstanding_invoices == 0:
        health_score += 15
    else:
        health_score += 5

    if health_score >= 85:
        health_status = "Excellent"
    elif health_score >= 65:
        health_status = "Good"
    elif health_score >= 40:
        health_status = "Needs Attention"
    else:
        health_status = "Critical"

    return render(
        request,
        "business_kpis.html",
        {
            "today_revenue": today_revenue,
            "month_revenue": month_revenue,
            "outstanding_invoices": outstanding_invoices,
            "payroll_month": payroll_month,
            "completed_jobs_month": completed_jobs_month,
            "upcoming_jobs": upcoming_jobs,
            "active_customers": active_customers,
            "new_customers_month": new_customers_month,
            "total_employees": total_employees,
            "average_rating": average_rating,
            "reviews_received": reviews_received,
            "campaigns_sent": campaigns_sent,
            "vip_customers": vip_customers,
            "estimated_profit_month": round(estimated_profit_month, 2),
            "profit_margin": profit_margin,
            "health_score": health_score,
            "health_status": health_status,
        },
    )


# leave_management.LeaveRequest already imported near the top of this module
# (duplicate import removed to avoid redefinition warnings)


@login_required
def employee_schedule(request):
    today = timezone.now().date()

    start_date = request.GET.get("start")

    if start_date:
        try:
            week_start = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            week_start = today - timedelta(days=today.weekday())
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    employees = Employee.objects.filter(active=True).order_by("full_name")

    week_days = []

    for i in range(7):
        week_days.append(week_start + timedelta(days=i))

    schedule_rows = []

    for employee in employees:
        employee_days = []

        total_jobs = 0

        for day in week_days:
            jobs = (
                Booking.objects.filter(assigned_employee=employee, booking_date=day)
                .exclude(status="cancelled")
                .select_related("customer")
                .order_by("booking_time")
            )

            total_jobs += jobs.count()
        approved_leave = LeaveRequest.objects.filter(
            employee=employee, status="approved", start_date__lte=day, end_date__gte=day
        ).first()

        employee_days.append(
            {
                "date": day,
                "jobs": jobs,
                "approved_leave": approved_leave,
            }
        )

        schedule_rows.append(
            {
                "employee": employee,
                "days": employee_days,
                "total_jobs": total_jobs,
            }
        )

    return render(
        request,
        "employee_schedule.html",
        {
            "week_start": week_start,
            "week_end": week_end,
            "previous_week": previous_week,
            "next_week": next_week,
            "week_days": week_days,
            "schedule_rows": schedule_rows,
        },
    )


@login_required
def gst_report(request):

    from expenses.models import Expense

    company_gst_rate = 10

    paid_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    total_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

    gst_collected = round(float(paid_revenue) / 11, 2)

    gst_paid = round(float(total_expenses) / 11, 2)

    net_gst_payable = round(gst_collected - gst_paid, 2)

    return render(
        request,
        "gst_report.html",
        {
            "paid_revenue": paid_revenue,
            "total_expenses": total_expenses,
            "gst_collected": gst_collected,
            "gst_paid": gst_paid,
            "net_gst_payable": net_gst_payable,
            "company_gst_rate": company_gst_rate,
        },
    )


@login_required
def finance_trends(request):
    from django.db.models.functions import TruncMonth

    from expenses.models import Expense

    revenue_data = (
        Invoice.objects.filter(status="paid")
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )

    expense_data = (
        Expense.objects.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    payroll_data = (
        PayrollRecord.objects.annotate(month=TruncMonth("period_end"))
        .values("month")
        .annotate(total=Sum("gross_pay"))
        .order_by("month")
    )

    months = []
    revenue_map = {}
    expense_map = {}
    payroll_map = {}

    for item in revenue_data:
        if item["month"]:
            label = item["month"].strftime("%b %Y")
            months.append(label)
            revenue_map[label] = float(item["total"] or 0)

    for item in expense_data:
        if item["month"]:
            label = item["month"].strftime("%b %Y")
            months.append(label)
            expense_map[label] = float(item["total"] or 0)

    for item in payroll_data:
        if item["month"]:
            label = item["month"].strftime("%b %Y")
            months.append(label)
            payroll_map[label] = float(item["total"] or 0)

    months = sorted(set(months))

    revenue_values = []
    expense_values = []
    payroll_values = []
    profit_values = []

    for month in months:
        revenue = revenue_map.get(month, 0)
        expenses = expense_map.get(month, 0)
        payroll = payroll_map.get(month, 0)
        profit = revenue - expenses - payroll

        revenue_values.append(revenue)
        expense_values.append(expenses)
        payroll_values.append(payroll)
        profit_values.append(round(profit, 2))

    return render(
        request,
        "finance_trends.html",
        {
            "months": months,
            "revenue_values": revenue_values,
            "expense_values": expense_values,
            "payroll_values": payroll_values,
            "profit_values": profit_values,
        },
    )


@login_required
def update_booking_quick_status(request, booking_id, new_status):
    booking = get_object_or_404(Booking, id=booking_id)

    allowed_statuses = [
        "pending",
        "confirmed",
        "assigned",
        "in_progress",
        "completed",
        "cancelled",
    ]

    if request.method == "POST":

        if new_status in allowed_statuses:
            old_status = booking.status
            booking.status = new_status
            booking.save()

            if new_status == "completed":

                existing_invoice = Invoice.objects.filter(booking=booking).first()

                if existing_invoice:

                    messages.info(
                        request,
                        f"Invoice already exists: {existing_invoice.invoice_number}",
                    )

                else:

                    invoice = Invoice.objects.create(
                        booking=booking,
                        amount=booking.quoted_price,
                        description=(
                            f"{booking.service_type} "
                            f"completed on "
                            f"{booking.booking_date}"
                        ),
                    )

                    customer = booking.customer

                    if customer.email:

                        subject = (
                            f"Invoice {invoice.invoice_number} - "
                            f"YD Commercial Cleaning Services"
                        )

                        message = f"""
Dear {customer.full_name},

Thank you for choosing YD Commercial Cleaning Services.

Your cleaning service has been completed and your invoice has been generated.

Invoice Number: {invoice.invoice_number}
Amount: ${invoice.total_amount}

You can view your invoice by logging into the customer portal.

Thank you,
YD Commercial Cleaning Services
"""

                        email = EmailMessage(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [customer.email],
                        )

                        pdf_buffer = generate_invoice_pdf(invoice)

                        email.attach(
                            f"{invoice.invoice_number}.pdf",
                            pdf_buffer.getvalue(),
                            "application/pdf",
                        )

                        email.send(fail_silently=False)

                        EmailLog.objects.create(
                            sent_by=request.user,
                            email_type="system",
                            recipient_name=customer.full_name,
                            recipient_email=customer.email,
                            subject=subject,
                            related_object=invoice.invoice_number,
                        )

                        create_activity_log(
                            request.user,
                            "invoice",
                            "Invoice Email Sent",
                            f"Invoice {invoice.invoice_number} emailed to {customer.full_name}.",
                        )

                        messages.success(
                            request, "✅ Invoice automatically created and emailed."
                        )

                    else:
                        messages.warning(
                            request,
                            "Invoice created, but customer has no email address.",
                        )

            try:
                if new_status == "cancelled":
                    delete_booking_event(booking)
                else:
                    create_or_update_booking_event(booking)

            except Exception as error:
                messages.warning(request, f"Google Calendar sync failed: {error}")

            create_activity_log(
                request.user,
                "booking",
                "Booking Status Updated",
                f"{booking.customer.full_name} booking changed from {old_status} to {new_status}.",
            )

            messages.success(request, "✅ Booking status updated successfully.")

        else:
            messages.error(request, "❌ Invalid booking status.")

    return redirect("booking_calendar")


# ==========================================================
# Equipment Inventory
# ==========================================================


@login_required
def equipment_list(request):
    from datetime import timedelta

    from django.utils import timezone

    from .models import Equipment

    today = timezone.localdate()
    due_limit = today + timedelta(days=30)

    equipment_items = Equipment.objects.all().order_by("-created_at")

    for item in equipment_items:
        item.service_status = ""

        if item.next_service_date:
            if item.next_service_date < today:
                item.service_status = "overdue"
            elif item.next_service_date == today:
                item.service_status = "today"
            elif item.next_service_date <= due_limit:
                item.service_status = "upcoming"
            else:
                item.service_status = "ok"

    return render(
        request,
        "equipment_list.html",
        {
            "equipment_items": equipment_items,
            "today": today,
        },
    )


@login_required
def add_equipment(request):
    from .forms import EquipmentForm

    if request.method == "POST":
        form = EquipmentForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Equipment added successfully.")
            return redirect("equipment_list")

        messages.error(request, "❌ Please check the equipment form.")
    else:
        form = EquipmentForm()

    return render(
        request,
        "equipment_form.html",
        {
            "form": form,
            "page_title": "Add Equipment",
            "button_text": "Save Equipment",
        },
    )


@login_required
def edit_equipment(request, equipment_id):
    from .forms import EquipmentForm
    from .models import Equipment

    equipment = get_object_or_404(Equipment, id=equipment_id)

    if request.method == "POST":
        form = EquipmentForm(request.POST, instance=equipment)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Equipment updated successfully.")
            return redirect("equipment_list")

        messages.error(request, "❌ Please check the equipment form.")
    else:
        form = EquipmentForm(instance=equipment)

    return render(
        request,
        "equipment_form.html",
        {
            "form": form,
            "page_title": "Edit Equipment",
            "button_text": "Update Equipment",
        },
    )


@login_required
def delete_equipment(request, equipment_id):
    from .models import Equipment

    equipment = get_object_or_404(Equipment, id=equipment_id)

    if request.method == "POST":
        equipment.delete()
        messages.success(request, "✅ Equipment deleted successfully.")
        return redirect("equipment_list")

    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": equipment.name,
            "cancel_url": "/dashboard/equipment/",
        },
    )


@login_required
def supplies_list(request):

    from .models import CleaningSupply

    supplies = CleaningSupply.objects.all().order_by("name")

    return render(
        request,
        "supplies_list.html",
        {
            "supplies": supplies,
        },
    )


@login_required
def add_supply(request):

    from .forms import CleaningSupplyForm

    if request.method == "POST":

        form = CleaningSupplyForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(request, "Supply added successfully.")

            return redirect("supplies_list")

    else:
        form = CleaningSupplyForm()

    return render(
        request,
        "supply_form.html",
        {
            "form": form,
            "title": "Add Supply",
        },
    )


@login_required
def edit_supply(request, supply_id):

    from .forms import CleaningSupplyForm
    from .models import CleaningSupply

    supply = get_object_or_404(CleaningSupply, id=supply_id)

    if request.method == "POST":

        form = CleaningSupplyForm(request.POST, instance=supply)

        if form.is_valid():
            form.save()

            messages.success(request, "Supply updated successfully.")

            return redirect("supplies_list")

    else:

        form = CleaningSupplyForm(instance=supply)

    return render(
        request,
        "supply_form.html",
        {
            "form": form,
            "title": "Edit Supply",
        },
    )


@login_required
def purchase_orders(request):

    from .models import PurchaseOrder

    orders = PurchaseOrder.objects.all().order_by("-id")

    return render(request, "purchase_orders.html", {"orders": orders})


@login_required
def add_purchase_order(request):

    from .forms import PurchaseOrderForm

    if request.method == "POST":

        form = PurchaseOrderForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(request, "Purchase Order Created.")

            return redirect("purchase_orders")

    else:

        form = PurchaseOrderForm()

    return render(request, "purchase_order_form.html", {"form": form})


@login_required
def receive_purchase_order(request, order_id):

    from .models import PurchaseOrder

    order = get_object_or_404(PurchaseOrder, id=order_id)

    if order.status != "received":

        supply = order.supply

        supply.current_stock += order.quantity
        supply.save()

        order.status = "received"
        order.save()

        messages.success(request, f"{order.quantity} units added to stock.")

    return redirect("purchase_orders")


@login_required
def supplier_list(request):
    from .models import Supplier

    suppliers = Supplier.objects.all().order_by("name")

    return render(
        request,
        "supplier_list.html",
        {
            "suppliers": suppliers,
        },
    )


@login_required
def add_supplier(request):
    from .forms import SupplierForm

    if request.method == "POST":
        form = SupplierForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Supplier added successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm()

    return render(
        request,
        "supplier_form.html",
        {
            "form": form,
            "title": "Add Supplier",
        },
    )


@login_required
def edit_supplier(request, supplier_id):
    from .forms import SupplierForm
    from .models import Supplier

    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Supplier updated successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm(instance=supplier)

    return render(
        request,
        "supplier_form.html",
        {
            "form": form,
            "title": "Edit Supplier",
        },
    )


@login_required
def vehicle_list(request):
    from .models import Vehicle

    vehicles = Vehicle.objects.all().order_by("vehicle_name")
    return render(request, "vehicle_list.html", {"vehicles": vehicles})


@login_required
def add_vehicle(request):
    from .forms import VehicleForm

    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Vehicle added successfully.")
            return redirect("vehicle_list")
    else:
        form = VehicleForm()

    return render(
        request,
        "vehicle_form.html",
        {
            "form": form,
            "title": "Add Vehicle",
        },
    )


@login_required
def edit_vehicle(request, vehicle_id):
    from .forms import VehicleForm
    from .models import Vehicle

    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Vehicle updated successfully.")
            return redirect("vehicle_list")
    else:
        form = VehicleForm(instance=vehicle)

    return render(
        request,
        "vehicle_form.html",
        {
            "form": form,
            "title": "Edit Vehicle",
        },
    )


@login_required
def maintenance_list(request):

    from .models import MaintenanceHistory

    records = MaintenanceHistory.objects.all().order_by("-maintenance_date")

    return render(request, "maintenance_list.html", {"records": records})


@login_required
def add_maintenance(request):

    from .forms import MaintenanceHistoryForm

    if request.method == "POST":

        form = MaintenanceHistoryForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(request, "Maintenance record added.")

            return redirect("maintenance_list")

    else:

        form = MaintenanceHistoryForm()

    return render(request, "maintenance_form.html", {"form": form})


@login_required
def reminder_centre(request):

    from contracts.models import Contract
    from dashboard.models import (
        CleaningSupply,
        Equipment,
        MaintenanceHistory,
        PurchaseOrder,
        Vehicle,
    )

    today = timezone.localdate()

    context = {
        "overdue_equipment": Equipment.objects.filter(next_service_date__lt=today),
        "low_stock_supplies": CleaningSupply.objects.filter(
            current_stock__lte=F("minimum_stock")
        ),
        "draft_purchase_orders": PurchaseOrder.objects.filter(status="draft"),
        "vehicle_alerts": Vehicle.objects.filter(service_due_date__lt=today),
        "maintenance_due": MaintenanceHistory.objects.filter(
            next_service_date__lt=today
        ),
        "contracts_expiring": Contract.objects.filter(
            end_date__lte=today + timedelta(days=30)
        ),
    }

    return render(request, "reminder_centre.html", context)


@login_required
def business_intelligence(request):

    today = timezone.localdate()
    current_month = today.month
    current_year = today.year

    if current_month == 1:

        previous_month = 12
        previous_year = current_year - 1

    else:

        previous_month = current_month - 1
        previous_year = current_year
    month_start = today.replace(day=1)

    monthly_expenses = (
        Expense.objects.filter(date__gte=month_start).aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )

    monthly_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date__gte=month_start).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    this_month_revenue = (
        Invoice.objects.filter(
            status="paid", paid_at__month=current_month, paid_at__year=current_year
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    last_month_revenue = (
        Invoice.objects.filter(
            status="paid", paid_at__month=previous_month, paid_at__year=previous_year
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    monthly_growth = 0

    if last_month_revenue > 0:

        monthly_growth = round(
            ((this_month_revenue - last_month_revenue) / last_month_revenue) * 100, 2
        )

    estimated_profit = float(monthly_revenue) - float(monthly_expenses)

    expense_categories = (
        Expense.objects.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    revenue_trend = (
        Invoice.objects.filter(status="paid")
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )

    expense_trend = (
        Expense.objects.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    revenue_labels = [
        item["month"].strftime("%b %Y") for item in revenue_trend if item["month"]
    ]

    revenue_values = [float(item["total"] or 0) for item in revenue_trend]

    expense_map = {}

    for item in expense_trend:

        if item["month"]:

            expense_map[item["month"].strftime("%b %Y")] = float(item["total"] or 0)

    profit_values = []

    for i, month in enumerate(revenue_labels):

        revenue = revenue_values[i]

        expenses = expense_map.get(month, 0)

        profit_values.append(round(revenue - expenses, 2))

    category_labels = [item["category"] for item in expense_categories]

    category_values = [float(item["total"] or 0) for item in expense_categories]

    top_customers = Customer.objects.annotate(
        total_bookings=Count("bookings")
    ).order_by("-total_bookings")[:5]

    top_employees = (
        Employee.objects.filter(active=True)
        .annotate(
            completed_jobs=Count(
                "assigned_bookings", filter=Q(assigned_bookings__status="completed")
            )
        )
        .order_by("-completed_jobs")[:5]
    )

    employee_revenue = (
        Employee.objects.filter(active=True)
        .annotate(
            completed_jobs=Count(
                "assigned_bookings", filter=Q(assigned_bookings__status="completed")
            ),
            revenue_generated=Sum(
                "assigned_bookings__quoted_price",
                filter=Q(assigned_bookings__status="completed"),
            ),
        )
        .order_by("-revenue_generated")[:10]
    )

    total_quotes = QuoteRequest.objects.count()

    accepted_quotes = QuoteRequest.objects.filter(status="accepted").count()

    quote_conversion_rate = 0

    if total_quotes > 0:

        quote_conversion_rate = round((accepted_quotes / total_quotes) * 100, 2)

    new_customers_this_month = Customer.objects.filter(
        created_at__month=current_month, created_at__year=current_year
    ).count()

    completed_jobs_count = Booking.objects.filter(status="completed").count()

    average_job_value = 0

    if completed_jobs_count > 0:

        average_job_value = round(monthly_revenue / completed_jobs_count, 2)

    revenue_by_service = (
        Booking.objects.filter(status="completed")
        .values("service_type")
        .annotate(total_revenue=Sum("quoted_price"), total_jobs=Count("id"))
        .order_by("-total_revenue")[:10]
    )

    revenue_by_suburb = (
        Booking.objects.filter(status="completed")
        .values("suburb_postcode")
        .annotate(total_revenue=Sum("quoted_price"), total_jobs=Count("id"))
        .order_by("-total_revenue")[:10]
    )

    top_10_customers = Customer.objects.annotate(total_jobs=Count("bookings")).order_by(
        "-total_revenue"
    )[:10]

    top_services = (
        Booking.objects.values("service_type")
        .annotate(total_jobs=Count("id"))
        .order_by("-total_jobs")[:5]
    )

    top_revenue_customers = Customer.objects.order_by("-total_revenue")[:5]

    customer_lifetime_value = Customer.objects.annotate(
        booking_count=Count("bookings")
    ).order_by("-total_revenue")[:10]

    top_suburbs = (
        Booking.objects.values("suburb_postcode")
        .annotate(total_jobs=Count("id"))
        .order_by("-total_jobs")[:10]
    )

    repeat_customers = Customer.objects.annotate(
        booking_count=Count("bookings")
    ).filter(booking_count__gt=1)

    repeat_customer_count = repeat_customers.count()

    total_customer_count = Customer.objects.count()

    repeat_customer_rate = 0

    if total_customer_count > 0:

        repeat_customer_rate = round(
            (repeat_customer_count / total_customer_count) * 100, 2
        )

        health_score = 0

        # Revenue Growth

        if monthly_growth >= 20:
            health_score += 25
        elif monthly_growth >= 10:
            health_score += 20
        elif monthly_growth > 0:
            health_score += 15

        # Repeat Customer Rate

        if repeat_customer_rate >= 50:
            health_score += 25
        elif repeat_customer_rate >= 30:
            health_score += 20
        elif repeat_customer_rate >= 15:
            health_score += 10

        # Quote Conversion

        if quote_conversion_rate >= 50:
            health_score += 25
        elif quote_conversion_rate >= 30:
            health_score += 20
        elif quote_conversion_rate >= 15:
            health_score += 10

        # Average Job Value

        if average_job_value >= 1000:
            health_score += 25
        elif average_job_value >= 500:
            health_score += 20
        elif average_job_value >= 250:
            health_score += 10

            # STEP 3 — Add
        if health_score >= 80:

            health_status = "Excellent"

        elif health_score >= 60:

            health_status = "Good"

        elif health_score >= 40:

            health_status = "Average"

        else:

            health_status = "Needs Attention"

    today_jobs = Booking.objects.filter(booking_date=today).count()

    outstanding_invoices = Invoice.objects.exclude(status="paid").count()

    low_stock_items = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    ).count()

    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today).count()

    vehicles_due_service = Vehicle.objects.filter(service_due_date__lt=today).count()

    executive_alerts = (
        outstanding_invoices
        + low_stock_items
        + overdue_equipment
        + vehicles_due_service
    )

    context = {
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
        "estimated_profit": round(estimated_profit, 2),
        "category_labels": category_labels,
        "category_values": category_values,
        "revenue_labels": revenue_labels,
        "revenue_values": revenue_values,
        "profit_values": profit_values,
        "top_customers": top_customers,
        "top_employees": top_employees,
        "top_services": top_services,
        "top_revenue_customers": top_revenue_customers,
        "customer_lifetime_value": customer_lifetime_value,
        "top_suburbs": top_suburbs,
        "repeat_customer_count": repeat_customer_count,
        "total_customer_count": total_customer_count,
        "repeat_customer_rate": repeat_customer_rate,
        "top_employees": top_employees,
        "employee_revenue": employee_revenue,
        "total_quotes": total_quotes,
        "accepted_quotes": accepted_quotes,
        "quote_conversion_rate": quote_conversion_rate,
        "new_customers_this_month": new_customers_this_month,
        "completed_jobs_count": completed_jobs_count,
        "average_job_value": average_job_value,
        "revenue_by_service": revenue_by_service,
        "revenue_by_suburb": revenue_by_suburb,
        "top_10_customers": top_10_customers,
        "health_score": health_score,
        "health_status": health_status,
        "today_jobs": today_jobs,
        "outstanding_invoices": outstanding_invoices,
        "low_stock_items": low_stock_items,
        "overdue_equipment": overdue_equipment,
        "vehicles_due_service": vehicles_due_service,
        "executive_alerts": executive_alerts,
    }

    return render(request, "business_intelligence.html", context)


@login_required
def export_business_report(request):

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = 'attachment; filename="business_report.pdf"'

    doc = SimpleDocTemplate(response)

    styles = getSampleStyleSheet()

    content = []

    monthly_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

    monthly_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    estimated_profit = monthly_revenue - monthly_expenses

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph("Business Intelligence Report", styles["Heading2"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Generated: {timezone.localdate()}", styles["Normal"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Revenue: ${monthly_revenue}", styles["Normal"]))

    content.append(Paragraph(f"Expenses: ${monthly_expenses}", styles["Normal"]))

    content.append(Paragraph(f"Profit: ${estimated_profit}", styles["Normal"]))

    doc.build(content)

    return response


@login_required
def email_business_report(request):

    from io import BytesIO

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    content = []

    monthly_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

    monthly_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    estimated_profit = monthly_revenue - monthly_expenses

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph("Business Intelligence Report", styles["Heading2"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Revenue: ${monthly_revenue}", styles["Normal"]))

    content.append(Paragraph(f"Expenses: ${monthly_expenses}", styles["Normal"]))

    content.append(Paragraph(f"Profit: ${estimated_profit}", styles["Normal"]))

    doc.build(content)

    pdf = buffer.getvalue()

    buffer.close()

    email = EmailMessage(
        subject="Business Intelligence Report",
        body="Attached is your latest business report.",
        to=["ydcommercialcleaning@gmail.com"],
    )

    email.attach("business_report.pdf", pdf, "application/pdf")

    email.send()

    messages.success(request, "PDF report emailed successfully.")

    return redirect("business_intelligence")

    subject = "Business Intelligence Report"

    message = """
Business Intelligence Report

Generated automatically from
YD Commercial Cleaning Services.
"""

    email = EmailMessage(subject, message, to=["ydcommercialcleaning@gmail.com"])

    email.send()

    messages.success(request, "Business report emailed successfully.")

    return redirect("business_intelligence")


@login_required
def operations_command_centre(request):

    today = timezone.localdate()

    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today)

    vehicles_due_service = Vehicle.objects.filter(service_due_date__lt=today)

    low_stock_supplies = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    )

    draft_purchase_orders = PurchaseOrder.objects.filter(status="draft")

    outstanding_invoices = Invoice.objects.exclude(status="paid")

    unassigned_jobs = Booking.objects.filter(assigned_employee__isnull=True)

    context = {
        "overdue_equipment": overdue_equipment,
        "vehicles_due_service": vehicles_due_service,
        "low_stock_supplies": low_stock_supplies,
        "draft_purchase_orders": draft_purchase_orders,
        "outstanding_invoices": outstanding_invoices,
        "unassigned_jobs": unassigned_jobs,
    }

    return render(request, "operations_command_centre.html", context)


@login_required
def customer_360(request, customer_id):

    customer = Customer.objects.get(id=customer_id)

    bookings = customer.bookings.all().order_by("-created_at")[:10]

    invoices = Invoice.objects.filter(customer=customer).order_by("-created_at")[:10]

    quotes = QuoteRequest.objects.filter(customer=customer).order_by("-created_at")[:10]

    outstanding_invoices = invoices.exclude(status="paid").count()

    context = {
        "customer": customer,
        "bookings": bookings,
        "invoices": invoices,
        "quotes": quotes,
        "outstanding_invoices": outstanding_invoices,
    }

    return render(request, "customer_360.html", context)


@login_required
def send_customer_followup(request, customer_id):

    customer = get_object_or_404(Customer, id=customer_id)

    send_mail(
        subject="We Miss You!",
        message=f"""
Hi {customer.full_name},

It's been a while since we last helped you.

YD Commercial Cleaning Services would love to assist you again.

Contact us anytime for your next cleaning service.

Thank you.
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[customer.email],
        fail_silently=False,
    )

    messages.success(request, "Follow-up email sent successfully.")

    return redirect("customer_profile_360", customer_id=customer.id)


@login_required
def employee_performance_centre(request):

    employees = Employee.objects.filter(active=True).order_by("full_name")

    employee_rows = []

    for employee in employees:

        completed_jobs = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        ).count()

        total_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue_generated = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        payroll_total = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        profit_contribution = revenue_generated - payroll_total
        kpi_score = 0

        bonus_recommendation = 0

        if kpi_score >= 90:
            bonus_recommendation = 500

        elif kpi_score >= 80:
            bonus_recommendation = 300

        elif kpi_score >= 70:
            bonus_recommendation = 150

        # Completed Jobs (40 points)

        if completed_jobs >= 50:
            kpi_score += 40

        elif completed_jobs >= 25:
            kpi_score += 30

        elif completed_jobs >= 10:
            kpi_score += 20

        # Revenue (30 points)

        if revenue_generated >= 20000:
            kpi_score += 30

        elif revenue_generated >= 10000:
            kpi_score += 20

        elif revenue_generated >= 5000:
            kpi_score += 10

        # Profit (30 points)

        if profit_contribution >= 10000:
            kpi_score += 30

        elif profit_contribution >= 5000:
            kpi_score += 20

        elif profit_contribution >= 2500:
            kpi_score += 10

        profit_contribution = revenue_generated - payroll_total

        attendance_logs = AttendanceLog.objects.filter(employee=employee)

        total_attendance = attendance_logs.count()

        completed_attendance = attendance_logs.filter(
            check_out_time__isnull=False
        ).count()

        attendance_score = 0

        if total_attendance > 0:
            attendance_score = round((completed_attendance / total_attendance) * 100, 2)

        employee_rows.append(
            {
                "employee": employee,
                "completed_jobs": completed_jobs,
                "total_jobs": total_jobs,
                "revenue_generated": revenue_generated,
                "payroll_total": payroll_total,
                "profit_contribution": profit_contribution,
                "kpi_score": kpi_score,
                "attendance_score": attendance_score,
                "bonus_recommendation": bonus_recommendation,
            }
        )

        employee_rows = sorted(
            employee_rows, key=lambda row: row["kpi_score"], reverse=True
        )

        top_performer = employee_rows[0] if employee_rows else None
        second_performer = employee_rows[1] if len(employee_rows) > 1 else None
        third_performer = employee_rows[2] if len(employee_rows) > 2 else None

    return render(
        request,
        "employee_performance_centre.html",
        {
            "employee_rows": employee_rows,
            "top_performer": top_performer,
            "second_performer": second_performer,
            "third_performer": third_performer,
        },
    )


@login_required
def employee_performance_detail(request, employee_id):

    employee = get_object_or_404(Employee, id=employee_id)

    bookings = Booking.objects.filter(assigned_employee=employee).order_by(
        "-booking_date"
    )

    payrolls = PayrollRecord.objects.filter(employee=employee).order_by("-created_at")

    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by(
        "-created_at"
    )

    completed_jobs = bookings.filter(status="completed").count()

    revenue_generated = (
        bookings.filter(status="completed").aggregate(total=Sum("quoted_price"))[
            "total"
        ]
        or 0
    )

    payroll_total = payrolls.aggregate(total=Sum("gross_pay"))["total"] or 0

    profit_contribution = revenue_generated - payroll_total

    return render(
        request,
        "employee_performance_detail.html",
        {
            "employee": employee,
            "bookings": bookings,
            "payrolls": payrolls,
            "leave_requests": leave_requests,
            "completed_jobs": completed_jobs,
            "revenue_generated": revenue_generated,
            "payroll_total": payroll_total,
            "profit_contribution": profit_contribution,
        },
    )


@login_required
def export_employee_performance_pdf(request):

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="employee_performance_report.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=landscape(A4))

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))
    content.append(Paragraph("Employee Performance Report", styles["Heading2"]))
    content.append(Spacer(1, 20))

    data = [
        [
            "Employee",
            "Total Jobs",
            "Completed",
            "Revenue",
            "Payroll",
            "Profit",
            "KPI",
            "Attendance",
            "Bonus",
        ]
    ]

    employees = Employee.objects.filter(active=True).order_by("full_name")

    for employee in employees:

        completed_jobs = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        ).count()

        total_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue_generated = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        payroll_total = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        profit = revenue_generated - payroll_total

        data.append(
            [
                employee.full_name,
                total_jobs,
                completed_jobs,
                f"${revenue_generated}",
                f"${payroll_total}",
                f"${profit}",
                "-",
                "-",
                "-",
            ]
        )

    table = Table(data)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ]
        )
    )

    content.append(table)

    doc.build(content)

    return response


@login_required
def email_employee_performance_report(request):

    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))

    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))

    content.append(Paragraph("Employee Performance Report", styles["Heading2"]))

    content.append(Spacer(1, 20))

    data = [
        [
            "Employee",
            "Jobs",
            "Revenue",
            "Payroll",
        ]
    ]

    employees = Employee.objects.filter(active=True)

    for employee in employees:

        total_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        payroll = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        data.append(
            [
                employee.full_name,
                total_jobs,
                f"${revenue}",
                f"${payroll}",
            ]
        )

    table = Table(data)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    content.append(table)

    doc.build(content)

    pdf = buffer.getvalue()

    buffer.close()

    email = EmailMessage(
        subject="Employee Performance Report",
        body="Attached is the latest Employee Performance Report.",
        to=["ydcommercialcleaning@gmail.com"],
    )

    email.attach("employee_performance_report.pdf", pdf, "application/pdf")

    email.send()

    messages.success(request, "Employee Performance PDF emailed successfully.")

    return redirect("employee_performance_centre")


@login_required
def employee_attendance_analytics(request):

    employees = Employee.objects.filter(active=True)

    analytics_rows = []

    for employee in employees:

        attendance_count = AttendanceLog.objects.filter(employee=employee).count()

        completed_attendance = AttendanceLog.objects.filter(
            employee=employee, check_out_time__isnull=False
        ).count()

        attendance_percentage = 0

        if attendance_count > 0:
            attendance_percentage = round(
                (completed_attendance / attendance_count) * 100, 2
            )

        leave_count = LeaveRequest.objects.filter(employee=employee).count()

        approved_leave_count = LeaveRequest.objects.filter(
            employee=employee, status="approved"
        ).count()

        analytics_rows.append(
            {
                "employee": employee,
                "attendance_count": attendance_count,
                "attendance_percentage": attendance_percentage,
                "leave_count": leave_count,
                "approved_leave_count": approved_leave_count,
            }
        )

    return render(
        request,
        "employee_attendance_analytics.html",
        {"analytics_rows": analytics_rows},
    )


@login_required
def owner_command_centre(request):

    today = timezone.localdate()

    today_jobs = Booking.objects.filter(booking_date=today).count()

    outstanding_invoices = Invoice.objects.exclude(status="paid").count()

    monthly_revenue = (
        Invoice.objects.filter(created_at__month=today.month)
        .exclude(status="cancelled")
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    monthly_expenses = (
        Expense.objects.filter(date__month=today.month).aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )

    estimated_profit = monthly_revenue - monthly_expenses

    low_stock_items = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    ).count()

    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today).count()

    vehicles_due_service = Vehicle.objects.filter(service_due_date__lt=today).count()

    pending_leave_requests = LeaveRequest.objects.filter(status="pending").count()

    draft_purchase_orders = PurchaseOrder.objects.filter(status="draft").count()

    return render(
        request,
        "owner_command_centre.html",
        {
            "today_jobs": today_jobs,
            "outstanding_invoices": outstanding_invoices,
            "monthly_revenue": monthly_revenue,
            "monthly_expenses": monthly_expenses,
            "estimated_profit": estimated_profit,
            "low_stock_items": low_stock_items,
            "overdue_equipment": overdue_equipment,
            "vehicles_due_service": vehicles_due_service,
            "pending_leave_requests": pending_leave_requests,
            "draft_purchase_orders": draft_purchase_orders,
        },
    )


@login_required
def business_forecasting_centre(request):

    today = timezone.localdate()

    current_revenue = (
        Invoice.objects.filter(created_at__month=today.month)
        .exclude(status="cancelled")
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    current_expenses = (
        Expense.objects.filter(date__month=today.month).aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )

    current_profit = current_revenue - current_expenses

    day_of_month = max(today.day, 1)

    projected_revenue = round((current_revenue / day_of_month) * 30, 2)

    projected_expenses = round((current_expenses / day_of_month) * 30, 2)

    projected_profit = round(projected_revenue - projected_expenses, 2)

    return render(
        request,
        "business_forecasting_centre.html",
        {
            "current_revenue": current_revenue,
            "current_expenses": current_expenses,
            "current_profit": current_profit,
            "projected_revenue": projected_revenue,
            "projected_expenses": projected_expenses,
            "projected_profit": projected_profit,
            "revenue_chart": [
                current_revenue,
                projected_revenue,
            ],
            "expense_chart": [
                current_expenses,
                projected_expenses,
            ],
            "profit_chart": [
                current_profit,
                projected_profit,
            ],
        },
    )


@login_required
def ai_quote_estimator(request):

    estimated_price = None
    confidence_level = None

    if request.method == "POST":

        bedrooms = int(request.POST.get("bedrooms", 0))

        bathrooms = int(request.POST.get("bathrooms", 0))

        property_type = request.POST.get("property_type", "")

        # completed_bookings = Booking.objects.filter(status="completed")  # unused in estimator

        average_job_value = (
            Invoice.objects.filter(status="paid").aggregate(avg=Avg("total_amount"))[
                "avg"
            ]
            or 250
        )

        estimated_price = average_job_value

        estimated_price += bedrooms * 20
        estimated_price += bathrooms * 15

        if property_type == "house":
            estimated_price += 50

        elif property_type == "commercial":
            estimated_price += 150

        estimated_price = round(estimated_price, 2)

        confidence_level = "Medium"

        paid_invoice_count = Invoice.objects.filter(status="paid").count()

        if paid_invoice_count > 100:
            confidence_level = "High"

        elif paid_invoice_count > 25:
            confidence_level = "Medium"

        else:
            confidence_level = "Low"

    return render(
        request,
        "ai_quote_estimator.html",
        {
            "estimated_price": estimated_price,
            "confidence_level": confidence_level,
        },
    )


@login_required
def quote_conversion_analytics(request):

    total_quotes = QuoteRequest.objects.count()

    accepted_quotes = QuoteRequest.objects.filter(status="accepted").count()

    declined_quotes = QuoteRequest.objects.filter(status="declined").count()

    total_quote_value = (
        QuoteRequest.objects.aggregate(total=Sum("estimated_price"))["total"] or 0
    )

    booked_revenue = (
        QuoteRequest.objects.filter(status="booked").aggregate(
            total=Sum("estimated_price")
        )["total"]
        or 0
    )

    lost_revenue = (
        QuoteRequest.objects.filter(status="lost").aggregate(
            total=Sum("estimated_price")
        )["total"]
        or 0
    )

    average_quote_value = (
        QuoteRequest.objects.aggregate(avg=Avg("estimated_price"))["avg"] or 0
    )

    lost_quote_value = (
        QuoteRequest.objects.filter(status="declined").aggregate(
            total=Sum("estimated_price")
        )["total"]
        or 0
    )

    conversion_rate = 0

    source_rows = []

    sources = QuoteRequest.objects.values_list("lead_source", flat=True).distinct()

    for source in sources:

        source_total = QuoteRequest.objects.filter(lead_source=source).count()

        source_accepted = QuoteRequest.objects.filter(
            lead_source=source, status="booked"
        ).count()

        source_rate = 0

        if source_total > 0:
            source_rate = round((source_accepted / source_total) * 100, 2)

        source_rows.append(
            {
                "source": source,
                "total": source_total,
                "accepted": source_accepted,
                "rate": source_rate,
            }
        )

    if total_quotes > 0:
        conversion_rate = round((accepted_quotes / total_quotes) * 100, 2)

    return render(
        request,
        "quote_conversion_analytics.html",
        {
            "total_quotes": total_quotes,
            "accepted_quotes": accepted_quotes,
            "declined_quotes": declined_quotes,
            "conversion_rate": conversion_rate,
            "lost_quote_value": lost_quote_value,
            "source_rows": source_rows,
            "total_quote_value": total_quote_value,
            "booked_revenue": booked_revenue,
            "lost_revenue": lost_revenue,
            "average_quote_value": round(average_quote_value, 2),
        },
    )


@login_required
def quote_followup_centre(request):

    followup_date = timezone.now() - timedelta(days=2)

    quotes = QuoteRequest.objects.filter(
        status="quoted", created_at__lte=followup_date
    ).order_by("-created_at")

    return render(request, "quote_followup_centre.html", {"quotes": quotes})


@login_required
def send_quote_followup_email(request, quote_id):

    quote = get_object_or_404(QuoteRequest, id=quote_id)

    send_mail(
        subject="Following Up On Your Cleaning Quote",
        message=f"""
Hi {quote.name},

We recently sent your cleaning quote.

If you have any questions or would like to proceed with the booking, please let us know.

YD Commercial Cleaning Services
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[quote.email],
        fail_silently=False,
    )

    messages.success(request, "Follow-up email sent.")

    return redirect("quote_followup_centre")


@login_required
def convert_quote_to_booking(request, quote_id):

    quote = get_object_or_404(QuoteRequest, id=quote_id)

    customer = Customer.objects.filter(email=quote.email).first()

    if not customer:

        customer = Customer.objects.create(
            full_name=quote.name,
            email=quote.email,
            phone=quote.phone,
            property_type=quote.property_type,
            suburb_postcode=quote.suburb_postcode,
            notes=quote.message,
        )

    if not customer.phone:
        customer.phone = quote.phone

    if not customer.suburb_postcode:
        customer.suburb_postcode = quote.suburb_postcode

    if not customer.property_type:
        customer.property_type = quote.property_type

    customer.save()

    service_type = "House Cleaning"

    if quote.property_type == "Office":
        service_type = "Office Cleaning"

    elif quote.property_type == "Commercial Property":
        service_type = "Commercial Cleaning"

    elif quote.property_type == "End of Lease Property":
        service_type = "End of Lease Cleaning"

    Booking.objects.create(
        customer=customer,
        service_type=service_type,
        booking_date=quote.preferred_date or timezone.localdate(),
        booking_time="09:00",
        address=customer.address or "Address not provided",
        suburb_postcode=quote.suburb_postcode,
        quoted_price=quote.estimated_price,
        status="pending",
        notes=quote.message,
    )

    quote.status = "booked"
    quote.save()

    messages.success(request, "Quote converted to booking successfully.")

    return redirect("booking_list")


@login_required
def create_invoice_from_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)

    existing_invoice = Invoice.objects.filter(booking=booking).first()

    if existing_invoice:

        messages.warning(request, "Invoice already exists.")

        return redirect("invoice_detail", invoice_id=existing_invoice.id)

    invoice = Invoice.objects.create(
        booking=booking,
        description=booking.service_type,
        amount=booking.quoted_price,
        status="draft",
        notes=booking.notes,
    )

    messages.success(request, "Invoice created successfully.")

    return redirect("invoice_detail", invoice_id=invoice.id)


@login_required
def owner_alert_centre(request):

    context = {
        "overdue_invoices": Invoice.objects.filter(status="overdue").count(),
        "expiring_contracts": CleaningContract.objects.filter(status="active").count(),
        "pending_leave_requests": LeaveRequest.objects.filter(status="pending").count(),
        "low_stock_items": 0,
        "vehicles_due_service": 0,
    }

    return render(request, "owner_alert_centre.html", context)


@login_required
def customer_value_dashboard(request):

    customers = Customer.objects.all().order_by("-total_revenue")

    top_customer = customers.first()

    total_customer_revenue = (
        customers.aggregate(total=Sum("total_revenue"))["total"] or 0
    )

    average_customer_value = customers.aggregate(avg=Avg("total_revenue"))["avg"] or 0

    return render(
        request,
        "customer_value_dashboard.html",
        {
            "customers": customers,
            "top_customer": top_customer,
            "total_customer_revenue": total_customer_revenue,
            "average_customer_value": average_customer_value,
        },
    )


@login_required
def vip_campaigns(request):

    vip_customers = Customer.objects.filter(total_revenue__gte=1000).order_by(
        "-total_revenue"
    )

    gold_customers = Customer.objects.filter(
        total_revenue__gte=500, total_revenue__lt=1000
    ).order_by("-total_revenue")

    inactive_customers = Customer.objects.filter(jobs_completed=0)

    context = {
        "vip_customers": vip_customers,
        "gold_customers": gold_customers,
        "inactive_customers": inactive_customers,
        "vip_count": vip_customers.count(),
        "gold_count": gold_customers.count(),
        "inactive_count": inactive_customers.count(),
    }

    return render(request, "vip_campaigns.html", context)


@login_required
def job_profitability_dashboard(request):

    bookings = Booking.objects.all().order_by("-booking_date")

    job_rows = []

    for booking in bookings:

        invoice_total = (
            Invoice.objects.filter(booking=booking).aggregate(
                total=Sum("total_amount")
            )["total"]
            or 0
        )

        estimated_profit = invoice_total - booking.quoted_price

        job_rows.append(
            {
                "booking": booking,
                "invoice_total": invoice_total,
                "quoted_price": booking.quoted_price,
                "estimated_profit": estimated_profit,
            }
        )

    return render(request, "job_profitability_dashboard.html", {"job_rows": job_rows})


@login_required
def service_performance_dashboard(request):

    bookings = Booking.objects.all()

    services = defaultdict(
        lambda: {
            "jobs": 0,
            "revenue": 0,
        }
    )

    for booking in bookings:

        services[booking.service_type]["jobs"] += 1

        services[booking.service_type]["revenue"] += booking.quoted_price or 0

    service_rows = []

    for service, data in services.items():

        service_rows.append(
            {
                "service": service,
                "jobs": data["jobs"],
                "revenue": data["revenue"],
            }
        )

    service_rows = sorted(service_rows, key=lambda x: x["revenue"], reverse=True)

    service_labels = [row["service"] for row in service_rows]

    service_revenues = [float(row["revenue"]) for row in service_rows]

    monthly_revenue = defaultdict(float)

    for booking in bookings:

        month_name = booking.booking_date.strftime("%b %Y")

        monthly_revenue[month_name] += float(booking.quoted_price or 0)

    revenue_labels = list(monthly_revenue.keys())

    revenue_values = list(monthly_revenue.values())

    return render(
        request,
        "service_performance_dashboard.html",
        {
            "service_rows": service_rows,
            "service_labels": service_labels,
            "service_revenues": service_revenues,
            "revenue_labels": revenue_labels,
            "revenue_values": revenue_values,
        },
    )


@login_required
def executive_bi_dashboard(request):

    total_customers = Customer.objects.count()

    total_bookings = Booking.objects.count()

    total_contracts = CleaningContract.objects.filter(status="active").count()

    total_revenue = Customer.objects.aggregate(total=Sum("total_revenue"))["total"] or 0

    vip_customers = Customer.objects.filter(total_revenue__gte=1000).count()

    context = {
        "total_customers": total_customers,
        "total_bookings": total_bookings,
        "total_contracts": total_contracts,
        "total_revenue": total_revenue,
        "vip_customers": vip_customers,
    }

    # monthly_revenue_labels/values removed; build monthly_revenue below

    bookings_by_month = {}

    for booking in Booking.objects.all():

        month = booking.booking_date.strftime("%b %Y")

        if month not in bookings_by_month:
            bookings_by_month[month] = 0

        bookings_by_month[month] += float(booking.quoted_price or 0)

    # monthly_revenue_labels/values not used later; use `monthly_revenue` instead

    monthly_revenue = {}
    monthly_bookings = {}
    customer_growth = {}
    service_revenue = {}

    for booking in Booking.objects.all().order_by("booking_date"):

        month = booking.booking_date.strftime("%b %Y")

        if month not in monthly_revenue:
            monthly_revenue[month] = 0

        if month not in monthly_bookings:
            monthly_bookings[month] = 0

        monthly_revenue[month] += float(booking.quoted_price or 0)

        monthly_bookings[month] += 1

        service = booking.service_type

        if service not in service_revenue:
            service_revenue[service] = 0

        service_revenue[service] += float(booking.quoted_price or 0)

    for customer in Customer.objects.all().order_by("created_at"):

        month = customer.created_at.strftime("%b %Y")

        if month not in customer_growth:
            customer_growth[month] = 0

        customer_growth[month] += 1

    contract_revenue = {}

    for contract in CleaningContract.objects.filter(status="active"):

        frequency = contract.frequency

        if frequency not in contract_revenue:
            contract_revenue[frequency] = 0

        contract_revenue[frequency] += float(contract.price_per_visit or 0)

        context.update(
            {
                "monthly_revenue_labels": list(monthly_revenue.keys()),
                "monthly_revenue_values": list(monthly_revenue.values()),
                "monthly_booking_labels": list(monthly_bookings.keys()),
                "monthly_booking_values": list(monthly_bookings.values()),
                "customer_growth_labels": list(customer_growth.keys()),
                "customer_growth_values": list(customer_growth.values()),
                "service_revenue_labels": list(service_revenue.keys()),
                "service_revenue_values": list(service_revenue.values()),
                "contract_revenue_labels": list(contract_revenue.keys()),
                "contract_revenue_values": list(contract_revenue.values()),
            }
        )

    return render(request, "executive_bi_dashboard.html", context)


@login_required
def employee_kpi_dashboard(request):

    employees = Employee.objects.all()

    employee_rows = []

    for employee in employees:

        booking_count = Booking.objects.filter(assigned_employee=employee).count()

        revenue = (
            Booking.objects.filter(assigned_employee=employee).aggregate(
                total=Sum("quoted_price")
            )["total"]
            or 0
        )

        hours_worked = (
            AttendanceLog.objects.filter(employee=employee).aggregate(
                total=Sum("total_hours")
            )["total"]
            or 0
        )

        employee_rows.append(
            {
                "employee": employee,
                "booking_count": booking_count,
                "revenue": revenue,
                "hours_worked": hours_worked,
            }
        )

    employee_rows = sorted(employee_rows, key=lambda x: x["revenue"], reverse=True)

    return render(
        request,
        "employee_kpi_dashboard.html",
        {
            "employee_rows": employee_rows,
        },
    )


@login_required
def staff_schedule_dashboard(request):

    today = timezone.localdate()

    bookings = Booking.objects.filter(booking_date=today).select_related(
        "customer", "assigned_employee"
    )

    return render(
        request,
        "staff_schedule_dashboard.html",
        {
            "bookings": bookings,
            "today": today,
        },
    )
