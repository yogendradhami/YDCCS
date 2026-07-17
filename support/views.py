<<<<<<< HEAD
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from customers.models import Customer
from notifications.models import Notification

from .forms import SupportTicketForm
from .models import SupportTicket
=======
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from customers.models import Customer
from .models import SupportTicket
from .forms import SupportTicketForm
from django.contrib.auth.models import User
from notifications.models import Notification
>>>>>>> 5815f15 (Initial project commit)


@login_required
def create_ticket(request):

<<<<<<< HEAD
    customer = get_object_or_404(Customer, user=request.user)

    if request.method == "POST":

        form = SupportTicketForm(request.POST)

        if form.is_valid():

            ticket = form.save(commit=False)
=======
    customer = get_object_or_404(
        Customer,
        user=request.user
    )

    if request.method == "POST":

        form = SupportTicketForm(
            request.POST
        )

        if form.is_valid():

            ticket = form.save(
                commit=False
            )
>>>>>>> 5815f15 (Initial project commit)

            ticket.customer = customer
            ticket.save()

<<<<<<< HEAD
            admin_users = User.objects.filter(is_staff=True)
=======

            admin_users = User.objects.filter(
                is_staff=True
            )
>>>>>>> 5815f15 (Initial project commit)

            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    title="New Support Ticket",
                    message=(
                        f"{customer.full_name} submitted a "
                        f"{ticket.get_priority_display()} priority ticket: "
                        f"{ticket.subject}"
                    ),
                    notification_type="system",
                    link="/dashboard/support/",
                )

<<<<<<< HEAD
            messages.success(
                request,
                "✅ Support ticket submitted successfully. Our team will review your request shortly.",
            )

            return redirect("customer_tickets")
=======

            messages.success(
                request,
                "✅ Support ticket submitted successfully. Our team will review your request shortly."
            )

            return redirect(
                "customer_tickets"
            )
>>>>>>> 5815f15 (Initial project commit)

    else:

        form = SupportTicketForm()

<<<<<<< HEAD
    return render(request, "support/create_ticket.html", {"form": form})
=======
    return render(
        request,
        "support/create_ticket.html",
        {
            "form": form
        }
    )
>>>>>>> 5815f15 (Initial project commit)


@login_required
def customer_tickets(request):

<<<<<<< HEAD
    customer = get_object_or_404(Customer, user=request.user)

    tickets = SupportTicket.objects.filter(customer=customer)

    return render(request, "support/customer_tickets.html", {"tickets": tickets})
=======
    customer = get_object_or_404(
        Customer,
        user=request.user
    )

    tickets = SupportTicket.objects.filter(
        customer=customer
    )

    return render(
        request,
        "support/customer_tickets.html",

        {
            "tickets": tickets
        }
    )
>>>>>>> 5815f15 (Initial project commit)


from django.contrib.auth.decorators import login_required

<<<<<<< HEAD

@login_required
def support_dashboard(request):

    tickets = SupportTicket.objects.select_related("customer").all()

    open_tickets = tickets.filter(status="open").count()

    in_progress_tickets = tickets.filter(status="in_progress").count()

    resolved_tickets = tickets.filter(status="resolved").count()

    closed_tickets = tickets.filter(status="closed").count()

    urgent_tickets = tickets.filter(priority="urgent").count()

    high_tickets = tickets.filter(priority="high").count()
=======
@login_required
def support_dashboard(request):

    tickets = SupportTicket.objects.select_related(
        "customer"
    ).all()

    open_tickets = tickets.filter(status="open").count()

    in_progress_tickets = tickets.filter(
        status="in_progress"
    ).count()

    resolved_tickets = tickets.filter(
        status="resolved"
    ).count()

    closed_tickets = tickets.filter(
        status="closed"
    ).count()

    urgent_tickets = tickets.filter(
        priority="urgent"
    ).count()

    high_tickets = tickets.filter(
        priority="high"
    ).count()
>>>>>>> 5815f15 (Initial project commit)

    recent_tickets = tickets[:15]

    return render(
        request,
        "support/support_dashboard.html",
        {
            "tickets": tickets,
            "open_tickets": open_tickets,
            "in_progress_tickets": in_progress_tickets,
            "resolved_tickets": resolved_tickets,
            "closed_tickets": closed_tickets,
            "urgent_tickets": urgent_tickets,
            "high_tickets": high_tickets,
            "recent_tickets": recent_tickets,
<<<<<<< HEAD
        },
    )
=======
        }
    )
>>>>>>> 5815f15 (Initial project commit)
