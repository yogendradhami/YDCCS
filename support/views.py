from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from customers.models import Customer
from notifications.models import Notification

from .chat_faq import FAQ_RESPONSES
from .forms import SupportTicketForm
from .models import (
    ChatEnquiry,
    LiveChatConversation,
    LiveChatMessage,
    SupportTicket,
)


# =========================================================
# CUSTOMER SUPPORT TICKETS
# =========================================================

@login_required
def create_ticket(request):

    customer = get_object_or_404(
        Customer,
        user=request.user,
    )

    if request.method == "POST":

        form = SupportTicketForm(request.POST)

        if form.is_valid():

            ticket = form.save(commit=False)

            ticket.customer = customer

            ticket.save()

            admin_users = User.objects.filter(
                is_staff=True
            )

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
                (
                    "✅ Support ticket submitted successfully. "
                    "Our team will review your request shortly."
                ),
            )

            return redirect("customer_tickets")

    else:

        form = SupportTicketForm()

    return render(
        request,
        "support/create_ticket.html",
        {
            "form": form,
        },
    )


@login_required
def customer_tickets(request):

    customer = get_object_or_404(
        Customer,
        user=request.user,
    )

    tickets = (
        SupportTicket.objects
        .filter(customer=customer)
        .order_by("-updated_at")
    )

    return render(
        request,
        "support/customer_tickets.html",
        {
            "tickets": tickets,
        },
    )


# =========================================================
# SUPPORT DASHBOARD
# =========================================================

@login_required
def support_dashboard(request):

    # =====================================================
    # SUPPORT TICKETS
    # =====================================================

    tickets = (
        SupportTicket.objects
        .select_related("customer")
        .order_by("-updated_at")
    )

    open_tickets = SupportTicket.objects.filter(
        status="open"
    ).count()

    in_progress_tickets = SupportTicket.objects.filter(
        status="in_progress"
    ).count()

    resolved_tickets = SupportTicket.objects.filter(
        status="resolved"
    ).count()

    closed_tickets = SupportTicket.objects.filter(
        status="closed"
    ).count()

    urgent_tickets = SupportTicket.objects.filter(
        priority="urgent"
    ).count()

    high_tickets = SupportTicket.objects.filter(
        priority="high"
    ).count()

    recent_tickets = tickets[:15]

    # =====================================================
    # LIVE CHAT
    # =====================================================
    # IMPORTANT:
    # Do NOT prefetch messages here.
    #
    # Messages are only required when an admin opens a
    # specific conversation.
    # =====================================================

    live_chats = (
        LiveChatConversation.objects
        .select_related("assigned_to")
        .order_by("-updated_at")
    )

    waiting_chats = LiveChatConversation.objects.filter(
        status="waiting"
    ).count()

    active_chats = LiveChatConversation.objects.filter(
        status="active"
    ).count()

    closed_chats = LiveChatConversation.objects.filter(
        status="closed"
    ).count()

    total_live_chats = LiveChatConversation.objects.count()

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

            "live_chats": live_chats,
            "waiting_chats": waiting_chats,
            "active_chats": active_chats,
            "closed_chats": closed_chats,
            "total_live_chats": total_live_chats,
        },
    )

# =========================================================
# LIVE CHAT COUNTS
# =========================================================

@login_required
@require_GET
def live_chat_counts(request):

    live_chats = (
        LiveChatConversation.objects.filter(
            status__in=[
                "waiting",
                "active",
            ]
        )
    )

    waiting_chats = live_chats.filter(
        status="waiting"
    ).count()

    active_chats = live_chats.filter(
        status="active"
    ).count()

    total_chats = live_chats.count()

    return JsonResponse(
        {
            "success": True,

            "total_chats": total_chats,

            "waiting_chats": waiting_chats,

            "active_chats": active_chats,
        }
    )


# =========================================================
# WEBSITE CHAT ENQUIRY
# =========================================================

@require_POST
def submit_chat_enquiry(request):

    name = request.POST.get(
        "name",
        "",
    ).strip()

    phone = request.POST.get(
        "phone",
        "",
    ).strip()

    email = request.POST.get(
        "email",
        "",
    ).strip()

    enquiry_type = request.POST.get(
        "enquiry_type",
        "general",
    ).strip()

    service = request.POST.get(
        "service",
        "",
    ).strip()

    suburb = request.POST.get(
        "suburb",
        "",
    ).strip()

    preferred_date = request.POST.get(
        "preferred_date",
        "",
    ).strip()

    message = request.POST.get(
        "message",
        "",
    ).strip()

    if not name:

        return JsonResponse(
            {
                "success": False,
                "message": "Please enter your name.",
            },
            status=400,
        )

    if not phone and not email:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Please provide your phone number "
                    "or email address."
                ),
            },
            status=400,
        )

    if not message:

        return JsonResponse(
            {
                "success": False,
                "message": "Please enter your message.",
            },
            status=400,
        )

    allowed_types = {
        choice[0]
        for choice in ChatEnquiry.ENQUIRY_TYPE_CHOICES
    }

    if enquiry_type not in allowed_types:

        enquiry_type = "general"

    enquiry = ChatEnquiry.objects.create(
        name=name,
        phone=phone,
        email=email,
        enquiry_type=enquiry_type,
        service=service,
        suburb=suburb,
        preferred_date=preferred_date or None,
        message=message,
    )

    admin_users = User.objects.filter(
        is_staff=True
    )

    for admin_user in admin_users:

        Notification.objects.create(
            user=admin_user,
            title="New Website Chat Enquiry",
            message=(
                f"{name} submitted a "
                f"{enquiry.get_enquiry_type_display().lower()} enquiry."
            ),
            notification_type="system",
            link="/admin/support/chatenquiry/",
        )

    return JsonResponse(
        {
            "success": True,
            "message": (
                "Thanks! Your enquiry has been received. "
                "Our team will get back to you shortly."
            ),
            "id": enquiry.id,
        }
    )


# =========================================================
# CHAT FAQ
# =========================================================

@require_GET
def chat_faq(request):

    faq_key = request.GET.get(
        "key",
        "",
    ).strip()

    faq = FAQ_RESPONSES.get(
        faq_key
    )

    if not faq:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Sorry, I couldn't find an answer "
                    "for that question."
                ),
            },
            status=404,
        )

    return JsonResponse(
        {
            "success": True,
            "key": faq_key,
            "question": faq["question"],
            "answer": faq["answer"],
        }
    )


# =========================================================
# STAFF LIVE CHAT DETAIL
# =========================================================

@login_required
@require_GET
def live_chat_detail(
    request,
    conversation_id,
):

    if not request.user.is_staff:

        return JsonResponse(
            {
                "success": False,
                "message": "Staff access required.",
            },
            status=403,
        )

    conversation = get_object_or_404(
        LiveChatConversation.objects.select_related(
            "assigned_to"
        ),
        id=conversation_id,
    )

    messages_list = conversation.messages.all().order_by(
        "created_at"
    )

    return JsonResponse(
        {
            "success": True,

            "conversation": {
                "id": conversation.id,
                "name": conversation.name,
                "email": conversation.email,
                "phone": conversation.phone,
                "status": conversation.status,
                "session_key": conversation.session_key,

                "assigned_to": (
                    conversation.assigned_to.get_full_name()
                    if conversation.assigned_to
                    else ""
                ),

                "created_at": (
                    conversation.created_at.isoformat()
                ),

                "updated_at": (
                    conversation.updated_at.isoformat()
                ),
            },

            "messages": [
                {
                    "id": item.id,
                    "sender_type": item.sender_type,
                    "sender_name": item.sender_name,
                    "message": item.message,
                    "created_at": (
                        item.created_at.isoformat()
                    ),
                }

                for item in messages_list
            ],
        }
    )


# =========================================================
# STAFF TAKEOVER
# =========================================================

@login_required
@require_POST
def live_chat_takeover(
    request,
    conversation_id,
):

    if not request.user.is_staff:

        return JsonResponse(
            {
                "success": False,
                "message": "Staff access required.",
            },
            status=403,
        )

    conversation = get_object_or_404(
        LiveChatConversation,
        id=conversation_id,
    )

    conversation.status = "active"

    conversation.assigned_to = request.user

    conversation.save(
        update_fields=[
            "status",
            "assigned_to",
            "updated_at",
        ]
    )

    LiveChatMessage.objects.create(
        conversation=conversation,
        sender_type="system",
        sender_name="YD Cleaning Support",
        message=(
            f"{request.user.get_full_name() or request.user.username} "
            "has taken over this conversation."
        ),
    )

    return JsonResponse(
        {
            "success": True,
            "status": conversation.status,
            "assigned_to": (
                request.user.get_full_name()
                or request.user.username
            ),
        }
    )


# =========================================================
# STAFF CLOSE CHAT
# =========================================================

@login_required
@require_POST
def live_chat_close(
    request,
    conversation_id,
):

    if not request.user.is_staff:

        return JsonResponse(
            {
                "success": False,
                "message": "Staff access required.",
            },
            status=403,
        )

    conversation = get_object_or_404(
        LiveChatConversation,
        id=conversation_id,
    )

    conversation.status = "closed"

    conversation.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    LiveChatMessage.objects.create(
        conversation=conversation,
        sender_type="system",
        sender_name="YD Cleaning Support",
        message=(
            "This conversation was closed by "
            f"{request.user.get_full_name() or request.user.username}."
        ),
    )

    return JsonResponse(
        {
            "success": True,
            "status": "closed",
        }
    )