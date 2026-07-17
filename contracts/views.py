from datetime import timedelta
<<<<<<< HEAD
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import Booking
from dashboard.models import EmailLog

from .forms import CleaningContractForm
from .models import CleaningContract
=======

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from bookings.models import Booking
from .models import CleaningContract
from .forms import CleaningContractForm
from django.db.models import Sum
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings
from dashboard.models import EmailLog
>>>>>>> 5815f15 (Initial project commit)


def get_next_date(current_date, frequency):
    if frequency == "weekly":
        return current_date + timedelta(days=7)

    if frequency == "fortnightly":
        return current_date + timedelta(days=14)

    if frequency == "monthly":
        return current_date + timedelta(days=30)

    return current_date + timedelta(days=7)


@login_required
def contract_list(request):
    today = timezone.now().date()
    expiry_limit = today + timedelta(days=30)

    contracts = CleaningContract.objects.all().order_by("-created_at")

    for contract in contracts:
        if contract.end_date:
<<<<<<< HEAD
            contract.days_remaining = (contract.end_date - today).days
        else:
            contract.days_remaining = None

    active_contracts = CleaningContract.objects.filter(status="active").count()
=======
            contract.days_remaining = (
                contract.end_date - today
            ).days
        else:
            contract.days_remaining = None

    active_contracts = CleaningContract.objects.filter(
        status="active"
    ).count()
>>>>>>> 5815f15 (Initial project commit)

    expiring_contracts = CleaningContract.objects.filter(
        status="active",
        end_date__isnull=False,
        end_date__gte=today,
<<<<<<< HEAD
        end_date__lte=expiry_limit,
    ).count()

    completed_contracts = CleaningContract.objects.filter(status="completed").count()

    cancelled_contracts = CleaningContract.objects.filter(status="cancelled").count()

    monthly_contract_value = (
        CleaningContract.objects.filter(status="active").aggregate(
            total=Sum("price_per_visit")
        )["total"]
        or 0
    )

    active_contract_value = (
        contracts.filter(status="active").aggregate(total=Sum("price_per_visit"))[
            "total"
        ]
        or 0
    )

    weekly_contracts = contracts.filter(status="active", frequency="weekly")

    weekly_revenue = sum(c.price_per_visit for c in weekly_contracts)

    monthly_revenue = round(weekly_revenue * Decimal("4.33"), 2)

    annual_revenue = round(monthly_revenue * Decimal("12"), 2)
=======
        end_date__lte=expiry_limit
    ).count()

    completed_contracts = CleaningContract.objects.filter(
        status="completed"
    ).count()

    cancelled_contracts = CleaningContract.objects.filter(
        status="cancelled"
    ).count()

    monthly_contract_value = CleaningContract.objects.filter(
        status="active"
    ).aggregate(
        total=Sum("price_per_visit")
    )["total"] or 0


    active_contract_value = contracts.filter(
        status="active"
    ).aggregate(
        total=Sum("price_per_visit")
    )["total"] or 0

    weekly_contracts = contracts.filter(
        status="active",
        frequency="weekly"
    )

    weekly_revenue = sum(
        c.price_per_visit for c in weekly_contracts
    )

    monthly_revenue = round(
        weekly_revenue * Decimal("4.33"),
        2
    )

    annual_revenue = round(
        monthly_revenue * Decimal("12"),
        2
    )

>>>>>>> 5815f15 (Initial project commit)

    today = timezone.localdate()

    contracts_expiring_30 = contracts.filter(
        status="active",
        end_date__isnull=False,
        end_date__lte=today + timedelta(days=30),
<<<<<<< HEAD
        end_date__gte=today,
=======
        end_date__gte=today
>>>>>>> 5815f15 (Initial project commit)
    ).count()

    contracts_expiring_14 = contracts.filter(
        status="active",
        end_date__isnull=False,
        end_date__lte=today + timedelta(days=14),
<<<<<<< HEAD
        end_date__gte=today,
=======
        end_date__gte=today
>>>>>>> 5815f15 (Initial project commit)
    ).count()

    contracts_expiring_7 = contracts.filter(
        status="active",
        end_date__isnull=False,
        end_date__lte=today + timedelta(days=7),
<<<<<<< HEAD
        end_date__gte=today,
    ).count()

    expired_contracts = contracts.filter(status="active", end_date__lt=today).count()

    return render(
        request,
        "contract_list.html",
        {
            "contracts": contracts,
            "active_contracts": active_contracts,
            "expiring_contracts": expiring_contracts,
            "completed_contracts": completed_contracts,
            "cancelled_contracts": cancelled_contracts,
            "monthly_contract_value": monthly_contract_value,
            "active_contract_value": active_contract_value,
            "weekly_revenue": weekly_revenue,
            "monthly_revenue": monthly_revenue,
            "annual_revenue": annual_revenue,
            "contracts_expiring_30": contracts_expiring_30,
            "contracts_expiring_14": contracts_expiring_14,
            "contracts_expiring_7": contracts_expiring_7,
            "expired_contracts": expired_contracts,
        },
    )
=======
        end_date__gte=today
    ).count()

    expired_contracts = contracts.filter(
        status="active",
        end_date__lt=today
    ).count()

    return render(request, "contracts/contract_list.html", {
        "contracts": contracts,
        "active_contracts": active_contracts,
        "expiring_contracts": expiring_contracts,
        "completed_contracts": completed_contracts,
        "cancelled_contracts": cancelled_contracts,
        "monthly_contract_value": monthly_contract_value,
        "active_contract_value": active_contract_value,
        "weekly_revenue": weekly_revenue,
        "monthly_revenue": monthly_revenue,
        "annual_revenue": annual_revenue,
        "contracts_expiring_30": contracts_expiring_30,
        "contracts_expiring_14": contracts_expiring_14,
        "contracts_expiring_7": contracts_expiring_7,
        "expired_contracts": expired_contracts,

    })


>>>>>>> 5815f15 (Initial project commit)


@login_required
def add_contract(request):
    if request.method == "POST":
        form = CleaningContractForm(request.POST)

        if form.is_valid():
            contract = form.save()
<<<<<<< HEAD
            messages.success(
                request, "✅ Recurring cleaning contract created successfully."
            )
=======
            messages.success(request, "✅ Recurring cleaning contract created successfully.")
>>>>>>> 5815f15 (Initial project commit)
            return redirect("contract_detail", contract_id=contract.id)

        messages.error(request, "❌ Please check the contract form.")
    else:
        form = CleaningContractForm()

<<<<<<< HEAD
    return render(
        request,
        "contract_form.html",
        {
            "form": form,
            "page_title": "Add Recurring Contract",
            "button_text": "Save Contract",
        },
    )
=======
    return render(request, "contracts/contract_form.html", {
        "form": form,
        "page_title": "Add Recurring Contract",
        "button_text": "Save Contract",
    })
>>>>>>> 5815f15 (Initial project commit)


@login_required
def edit_contract(request, contract_id):
    contract = get_object_or_404(CleaningContract, id=contract_id)

    if request.method == "POST":
        form = CleaningContractForm(request.POST, instance=contract)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Contract updated successfully.")
            return redirect("contract_detail", contract_id=contract.id)

        messages.error(request, "❌ Please check the contract form.")
    else:
        form = CleaningContractForm(instance=contract)

<<<<<<< HEAD
    return render(
        request,
        "contract_form.html",
        {
            "form": form,
            "page_title": "Edit Recurring Contract",
            "button_text": "Update Contract",
        },
    )
=======
    return render(request, "contracts/contract_form.html", {
        "form": form,
        "page_title": "Edit Recurring Contract",
        "button_text": "Update Contract",
    })
>>>>>>> 5815f15 (Initial project commit)


@login_required
def delete_contract(request, contract_id):
    contract = get_object_or_404(CleaningContract, id=contract_id)

    if request.method == "POST":
        contract.delete()
        messages.success(request, "✅ Contract deleted successfully.")
        return redirect("contract_list")

<<<<<<< HEAD
    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": str(contract),
            "cancel_url": "/dashboard/contracts/",
        },
    )
=======
    return render(request, "shared/confirm_delete.html", {
        "object_name": str(contract),
        "cancel_url": "/dashboard/contracts/",
    })
>>>>>>> 5815f15 (Initial project commit)


@login_required
def contract_detail(request, contract_id):
    contract = get_object_or_404(CleaningContract, id=contract_id)

    bookings = Booking.objects.filter(
        customer=contract.customer,
        service_type=contract.service_type,
<<<<<<< HEAD
        address=contract.address,
    ).order_by("-booking_date", "-booking_time")[:20]

    return render(
        request,
        "contract_detail.html",
        {
            "contract": contract,
            "bookings": bookings,
        },
    )
=======
        address=contract.address
    ).order_by("-booking_date", "-booking_time")[:20]

    return render(request, "contracts/contract_detail.html", {
        "contract": contract,
        "bookings": bookings,
    })
>>>>>>> 5815f15 (Initial project commit)


@login_required
def generate_contract_bookings(request, contract_id):
    contract = get_object_or_404(CleaningContract, id=contract_id)

    if contract.status != "active":
        messages.error(request, "❌ Only active contracts can generate bookings.")
        return redirect("contract_detail", contract_id=contract.id)

    today = timezone.now().date()
    generation_end = today + timedelta(days=90)

    if contract.bookings_generated_until and contract.bookings_generated_until > today:
        next_booking_date = get_next_date(
<<<<<<< HEAD
            contract.bookings_generated_until, contract.frequency
=======
            contract.bookings_generated_until,
            contract.frequency
>>>>>>> 5815f15 (Initial project commit)
        )
    else:
        next_booking_date = contract.start_date

    if next_booking_date < today:
        while next_booking_date < today:
            next_booking_date = get_next_date(next_booking_date, contract.frequency)

    generated_count = 0

    while next_booking_date <= generation_end:
        if contract.end_date and next_booking_date > contract.end_date:
            break

        existing_booking = Booking.objects.filter(
            customer=contract.customer,
            service_type=contract.service_type,
            booking_date=next_booking_date,
            booking_time=contract.preferred_time,
            address=contract.address,
        ).exists()

        if not existing_booking:
            Booking.objects.create(
                customer=contract.customer,
                service_type=contract.service_type,
                booking_date=next_booking_date,
                booking_time=contract.preferred_time,
                address=contract.address,
                suburb_postcode=contract.suburb_postcode,
                quoted_price=contract.price_per_visit,
                assigned_employee=contract.assigned_employee,
                status="assigned" if contract.assigned_employee else "pending",
                notes=f"Auto-generated from recurring contract #{contract.id}. {contract.notes}",
            )

            generated_count += 1

        contract.bookings_generated_until = next_booking_date
        next_booking_date = get_next_date(next_booking_date, contract.frequency)

    contract.save()

<<<<<<< HEAD
    messages.success(
        request, f"✅ {generated_count} bookings generated for the next 90 days."
    )
    return redirect("contract_detail", contract_id=contract.id)


=======
    messages.success(request, f"✅ {generated_count} bookings generated for the next 90 days.")
    return redirect("contract_detail", contract_id=contract.id)



>>>>>>> 5815f15 (Initial project commit)
@login_required
def contract_renewals(request):

    today = timezone.localdate()

    contracts = CleaningContract.objects.filter(
        status="active",
        end_date__isnull=False,
        end_date__lte=today + timedelta(days=30),
<<<<<<< HEAD
        end_date__gte=today,
=======
        end_date__gte=today
>>>>>>> 5815f15 (Initial project commit)
    ).order_by("end_date")

    return render(
        request,
<<<<<<< HEAD
        "contract_renewals.html",
        {
            "contracts": contracts,
        },
    )


@login_required
def send_contract_renewal_email(request, contract_id):

    contract = get_object_or_404(CleaningContract, id=contract_id)
=======
        "contracts/contract_renewals.html",
        {
            "contracts": contracts,
        }
    )

@login_required
def send_contract_renewal_email(
    request,
    contract_id
):

    contract = get_object_or_404(
        CleaningContract,
        id=contract_id
    )
>>>>>>> 5815f15 (Initial project commit)

    customer = contract.customer

    if not customer.email:

<<<<<<< HEAD
        messages.error(request, "Customer has no email.")

        return redirect("contract_renewals")

    subject = "Contract Renewal Reminder - " "YD Commercial Cleaning Services"
=======
        messages.error(
            request,
            "Customer has no email."
        )

        return redirect(
            "contract_renewals"
        )

    subject = (
        "Contract Renewal Reminder - "
        "YD Commercial Cleaning Services"
    )
>>>>>>> 5815f15 (Initial project commit)

    message = f"""
Dear {customer.full_name},

Your cleaning contract is due to expire on:

{contract.end_date}

We would love to continue providing cleaning services for your business.

Please contact us to renew your agreement.

Kind Regards,

YD Commercial Cleaning Services
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [customer.email],
<<<<<<< HEAD
        fail_silently=False,
=======
        fail_silently=False
>>>>>>> 5815f15 (Initial project commit)
    )

    EmailLog.objects.create(
        sent_by=request.user,
        email_type="contract_renewal",
        recipient_name=customer.full_name,
        recipient_email=customer.email,
        subject=subject,
<<<<<<< HEAD
        related_object=f"Contract #{contract.id}",
    )

    messages.success(request, "Renewal email sent successfully.")

    return redirect("contract_renewals")
=======
        related_object=f"Contract #{contract.id}"
    )

    messages.success(
        request,
        "Renewal email sent successfully."
    )

    return redirect(
        "contract_renewals"
    )
>>>>>>> 5815f15 (Initial project commit)
