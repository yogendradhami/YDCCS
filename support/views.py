from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from customers.models import Customer
from notifications.models import Notification

from .forms import SupportTicketForm
from .models import SupportTicket


@login_required
def create_ticket(request):

    customer = get_object_or_404(Customer, user=request.user)

    if request.method == "POST":

        form = SupportTicketForm(request.POST)

        if form.is_valid():

            ticket = form.save(commit=False)

            ticket.customer = customer
            ticket.save()

            admin_users = User.objects.filter(is_staff=True)

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

            messages.success(
                request,
                "✅ Support ticket submitted successfully. Our team will review your request shortly.",
            )

            return redirect("customer_tickets")

    else:

        form = SupportTicketForm()

    return render(request, "support/create_ticket.html", {"form": form})


@login_required
def customer_tickets(request):

    customer = get_object_or_404(Customer, user=request.user)

    tickets = SupportTicket.objects.filter(customer=customer)

    return render(request, "support/customer_tickets.html", {"tickets": tickets})


from django.contrib.auth.decorators import login_required


@login_required
def support_dashboard(request):

    tickets = SupportTicket.objects.select_related("customer").all()

    open_tickets = tickets.filter(status="open").count()

    in_progress_tickets = tickets.filter(status="in_progress").count()

    resolved_tickets = tickets.filter(status="resolved").count()

    closed_tickets = tickets.filter(status="closed").count()

    urgent_tickets = tickets.filter(priority="urgent").count()

    high_tickets = tickets.filter(priority="high").count()

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
        },
    )
