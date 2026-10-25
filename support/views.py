from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseForbidden
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
import secrets
import re

from customers.models import Customer
from notifications.models import Notification

from .chat_faq import FAQ_RESPONSES
from .forms import SupportTicketForm, SupportTicketReplyForm
from .models import (
    ChatEnquiry,
    LiveChatConversation,
    LiveChatMessage,
    SupportTicket,
    SupportTicketReply,
)
from .realtime import (
    DASHBOARD_GROUP,
    conversation_summary,
    has_chat_permission,
    queue_dashboard_update,
    send_conversation_event,
)
from .rate_limits import allow_live_chat_action


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


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        SupportTicket.objects.select_related("customer"), id=ticket_id
    )

    if not request.user.is_staff and ticket.customer.user_id != request.user.id:
        return JsonResponse({"success": False, "message": "Access denied."}, status=403)

    return render(
        request,
        "support/ticket_detail.html",
        {
            "ticket": ticket,
            "replies": ticket.replies.select_related("author").all(),
            "reply_form": SupportTicketReplyForm(),
            "is_staff_view": request.user.is_staff,
        },
    )


@login_required
@require_POST
def ticket_reply(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    if request.user.is_staff or ticket.customer.user_id != request.user.id:
        return JsonResponse({"success": False, "message": "Access denied."}, status=403)
    if ticket.status == "closed":
        messages.error(request, "Closed tickets cannot receive new replies.")
        return redirect("ticket_detail", ticket_id=ticket.id)

    form = SupportTicketReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.ticket = ticket
        reply.author = request.user
        reply.save()
        ticket.status = "open"
        ticket.save(update_fields=["status", "updated_at"])
        for staff_user in User.objects.filter(is_staff=True):
            Notification.objects.create(
                user=staff_user,
                title="Customer Replied to Support Ticket",
                message=f"{ticket.customer.full_name} replied to: {ticket.subject}",
                notification_type="system",
                link=f"/portal/support/{ticket.id}/",
            )
        messages.success(request, "Your reply was sent to support.")
    else:
        messages.error(request, "Please enter a valid reply.")
    return redirect("ticket_detail", ticket_id=ticket.id)


@login_required
@require_POST
def ticket_update(request, ticket_id):
    if not request.user.is_staff:
        return JsonResponse({"success": False, "message": "Staff access required."}, status=403)

    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    allowed_statuses = {choice[0] for choice in SupportTicket.STATUS_CHOICES}
    allowed_priorities = {choice[0] for choice in SupportTicket.PRIORITY_CHOICES}
    status = request.POST.get("status", ticket.status)
    priority = request.POST.get("priority", ticket.priority)
    if status not in allowed_statuses or priority not in allowed_priorities:
        messages.error(request, "Invalid ticket status or priority.")
        return redirect("ticket_detail", ticket_id=ticket.id)

    ticket.status = status
    ticket.priority = priority
    ticket.save(update_fields=["status", "priority", "updated_at"])

    Notification.objects.create(
        user=ticket.customer.user,
        title="Support Ticket Updated",
        message=(
            f"Your ticket '{ticket.subject}' is now "
            f"{ticket.get_status_display().lower()} with "
            f"{ticket.get_priority_display().lower()} priority."
        ),
        notification_type="system",
        link=f"/portal/support/{ticket.id}/",
    )

    reply_form = SupportTicketReplyForm(request.POST)
    if reply_form.is_valid() and reply_form.cleaned_data["message"]:
        reply = reply_form.save(commit=False)
        reply.ticket = ticket
        reply.author = request.user
        reply.save()
        Notification.objects.create(
            user=ticket.customer.user,
            title="Support Ticket Updated",
            message=f"Support replied to: {ticket.subject}",
            notification_type="system",
            link=f"/portal/support/{ticket.id}/",
        )

    messages.success(request, "Support ticket updated successfully.")
    return redirect("ticket_detail", ticket_id=ticket.id)

# =========================================================
# SUPPORT DASHBOARD
# =========================================================

@login_required
def support_dashboard(request):

    if not has_chat_permission(request.user, "view"):
        return HttpResponseForbidden("Support chat access required.")

    if not request.user.is_staff:
        return JsonResponse(
            {"success": False, "message": "Staff access required."},
            status=403,
        )

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
    assignable_chat_staff = [
        user
        for user in User.objects.filter(is_active=True, is_staff=True).order_by(
            "first_name", "last_name", "username"
        )
        if has_chat_permission(user, "view")
        and has_chat_permission(user, "change")
    ]

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
            "can_change_live_chats": has_chat_permission(
                request.user,
                "change",
            ),
            "assignable_chat_staff": assignable_chat_staff,
        },
    )

# =========================================================
# LIVE CHAT COUNTS
# =========================================================

@login_required
@require_GET
def live_chat_counts(request):

    if not has_chat_permission(request.user, "view"):
        return JsonResponse(
            {"success": False, "message": "Staff access required."},
            status=403,
        )

    waiting_chats = LiveChatConversation.objects.filter(
        status="waiting"
    ).count()

    active_chats = LiveChatConversation.objects.filter(
        status="active"
    ).count()

    closed_chats = LiveChatConversation.objects.filter(status="closed").count()
    total_chats = LiveChatConversation.objects.count()

    return JsonResponse(
        {
            "success": True,

            "total_chats": total_chats,

            "waiting_chats": waiting_chats,

            "active_chats": active_chats,
            "closed_chats": closed_chats,
            "total_live_chats": total_chats,
        }
    )


# =========================================================
# WEBSITE CHAT ENQUIRY
# =========================================================

@csrf_protect
@require_POST
def submit_chat_enquiry(request):
    client = request.META.get("REMOTE_ADDR", "unknown")
    if not allow_live_chat_action(f"ip:{client}", "chat-enquiry", 5):
        return JsonResponse(
            {"success": False, "message": "Too many requests. Please try again later."},
            status=429,
        )

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

    if (
        len(name) > 150
        or len(phone) > 30
        or len(email) > 254
        or len(service) > 150
        or len(suburb) > 100
        or len(message) > 3000
    ):
        return JsonResponse(
            {"success": False, "message": "One or more fields exceed the allowed length."},
            status=400,
        )
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse(
                {"success": False, "message": "Please provide a valid email address."},
                status=400,
            )
    if phone and not re.fullmatch(r"[0-9+(). -]{1,30}", phone):
        return JsonResponse(
            {"success": False, "message": "Please provide a valid phone number."},
            status=400,
        )
    parsed_preferred_date = parse_date(preferred_date) if preferred_date else None
    if preferred_date and parsed_preferred_date is None:
        return JsonResponse(
            {"success": False, "message": "Please provide a valid preferred date."},
            status=400,
        )

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
        preferred_date=parsed_preferred_date,
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

@require_GET
def live_chat_session_token(request):
    client = request.META.get("REMOTE_ADDR", "unknown")
    if not allow_live_chat_action(f"ip:{client}", "session-token", 40):
        return JsonResponse(
            {"success": False, "message": "Please wait before reconnecting."},
            status=429,
        )
    session_key = request.session.get("live_chat_session_key")
    if not session_key:
        session_key = secrets.token_urlsafe(32)
        request.session["live_chat_session_key"] = session_key
    token = signing.dumps(
        {"session_key": session_key},
        salt="support.live-chat.session",
    )
    return JsonResponse({"success": True, "session_token": token})


@login_required
@require_GET
def live_chat_list(request):
    if not has_chat_permission(request.user, "view"):
        return JsonResponse(
            {"success": False, "message": "Support chat access required."},
            status=403,
        )
    if not allow_live_chat_action(
        f"staff:{request.user.pk}",
        "staff-read",
        240,
    ):
        return JsonResponse(
            {"success": False, "message": "Please wait before refreshing chat data."},
            status=429,
        )

    conversations = LiveChatConversation.objects.select_related("assigned_to")
    status_filter = request.GET.get("status", "all").strip().lower()
    if status_filter in {"waiting", "active", "closed"}:
        conversations = conversations.filter(status=status_filter)
    elif status_filter not in {"all", "archived"}:
        return JsonResponse(
            {"success": False, "message": "Invalid status filter."},
            status=400,
        )
    if status_filter == "archived":
        conversations = conversations.filter(status="closed")

    assignment_filter = request.GET.get("assigned", "all").strip().lower()
    if assignment_filter == "mine":
        conversations = conversations.filter(assigned_to=request.user)
    elif assignment_filter == "unassigned":
        conversations = conversations.filter(assigned_to__isnull=True)
    elif assignment_filter == "assigned":
        conversations = conversations.filter(assigned_to__isnull=False)
    elif assignment_filter != "all":
        return JsonResponse(
            {"success": False, "message": "Invalid assignment filter."},
            status=400,
        )

    search = request.GET.get("q", "").strip()[:100]
    if search:
        conversations = conversations.filter(name__icontains=search)
    rows = list(conversations.order_by("-updated_at", "-pk")[:200])
    return JsonResponse(
        {
            "success": True,
            "conversations": [
                summary
                for conversation in rows
                if (summary := conversation_summary(conversation.pk))
            ],
            "has_more": conversations.count() > len(rows),
            "counts": {
                "waiting": LiveChatConversation.objects.filter(status="waiting").count(),
                "active": LiveChatConversation.objects.filter(status="active").count(),
                "closed": LiveChatConversation.objects.filter(status="closed").count(),
                "total": LiveChatConversation.objects.count(),
            },
        }
    )


@login_required
@require_GET
def live_chat_detail(
    request,
    conversation_id,
):

    if not has_chat_permission(request.user, "view"):

        return JsonResponse(
            {
                "success": False,
                "message": "Staff access required.",
            },
            status=403,
        )
    if not allow_live_chat_action(
        f"staff:{request.user.pk}",
        "staff-read",
        240,
    ):
        return JsonResponse(
            {"success": False, "message": "Please wait before refreshing chat data."},
            status=429,
        )

    conversation = get_object_or_404(
        LiveChatConversation.objects.select_related(
            "assigned_to"
        ),
        id=conversation_id,
    )

    after_id = request.GET.get("after_id")
    if after_id:
        try:
            after_id = int(after_id)
            if after_id < 0:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "message": "Invalid message cursor."},
                status=400,
            )
        messages_list = conversation.messages.filter(pk__gt=after_id).order_by("pk")[:500]
        has_more = conversation.messages.filter(pk__gt=after_id).count() > 500
    else:
        latest_messages = list(conversation.messages.order_by("-pk")[:500])
        messages_list = reversed(latest_messages)
        has_more = conversation.messages.count() > 500

    return JsonResponse(
        {
            "success": True,

            "conversation": {
                "id": conversation.id,
                "name": conversation.name,
                "email": conversation.email,
                "phone": conversation.phone,
                "status": conversation.status,
                "assigned_to": (
                    conversation.assigned_to.get_full_name()
                    if conversation.assigned_to
                    else ""
                ),
                "assigned_to_id": conversation.assigned_to_id,

                "created_at": (
                    conversation.created_at.isoformat()
                ),

                "updated_at": (
                    conversation.updated_at.isoformat()
                ),
                "closed_at": (
                    conversation.closed_at.isoformat()
                    if conversation.closed_at
                    else None
                ),
                "legal_hold": conversation.legal_hold,
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
            "has_more": has_more,
        }
    )


# =========================================================
# STAFF TAKEOVER
# =========================================================

@login_required
@csrf_protect
@require_POST
def live_chat_takeover(
    request,
    conversation_id,
):

    if not has_chat_permission(request.user, "change"):

        return JsonResponse(
            {
                "success": False,
                "message": "Staff access required.",
            },
            status=403,
        )
    if not allow_live_chat_action(
        f"staff:{request.user.pk}",
        "staff-mutate",
        30,
    ):
        return JsonResponse(
            {"success": False, "message": "Please wait before changing this conversation."},
            status=429,
        )

    with transaction.atomic():
        conversation = LiveChatConversation.objects.select_for_update().get(
            id=conversation_id
        )

        if conversation.status == "closed":
            return JsonResponse(
                {"success": False, "message": "Closed conversations cannot be taken over."},
                status=409,
            )
        if conversation.status == "active" and conversation.assigned_to_id == request.user.id:
            return JsonResponse(
                {
                    "success": True,
                    "status": conversation.status,
                    "assigned_to": request.user.get_full_name() or request.user.username,
                }
            )
        if conversation.status == "active" and conversation.assigned_to_id:
            assignee = conversation.assigned_to
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "This conversation is already assigned to "
                        f"{assignee.get_full_name() or assignee.username}."
                    ),
                    "assigned_to": assignee.get_full_name() or assignee.username,
                },
                status=409,
            )

        conversation.status = "active"
        conversation.mode = "human"
        conversation.assigned_to = request.user
        conversation.save(
            update_fields=["status", "mode", "assigned_to", "updated_at"]
        )
        system_message = LiveChatMessage.objects.create(
            conversation=conversation,
            sender_type="system",
            sender_name="YD Cleaning Support",
            message=(
                f"{request.user.get_full_name() or request.user.username} "
                "has taken over this conversation."
            ),
        )
        from dashboard.models import ActivityLog

        ActivityLog.objects.create(
            user=request.user,
            action_type="system",
            title="Live Chat Taken Over",
            description=f"Conversation #{conversation.pk} assigned to staff.",
        )
        queue_dashboard_update(conversation.id, "conversation.assigned")

    send_conversation_event(
        conversation.id,
        {
            "type": "chat_system",
            "message": (
                f"{request.user.get_full_name() or request.user.username} "
                "has taken over this conversation."
            ),
            "message_id": system_message.pk,
            "status": "active",
            "assigned_to_id": request.user.pk,
            "assigned_to": request.user.get_full_name() or request.user.username,
        },
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


@login_required
@csrf_protect
@require_POST
def live_chat_assign(request, conversation_id):
    if not has_chat_permission(request.user, "change"):
        return JsonResponse(
            {"success": False, "message": "Staff access required."},
            status=403,
        )
    if not allow_live_chat_action(
        f"staff:{request.user.pk}",
        "staff-mutate",
        30,
    ):
        return JsonResponse(
            {"success": False, "message": "Please wait before changing this conversation."},
            status=429,
        )

    raw_staff_user_id = request.POST.get("staff_user_id", "").strip()
    try:
        staff_user_id = int(raw_staff_user_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "Choose a valid staff member."},
            status=400,
        )
    raw_expected_assignee_id = request.POST.get(
        "expected_assigned_to_id",
        "",
    ).strip()
    try:
        expected_assignee_id = (
            int(raw_expected_assignee_id)
            if raw_expected_assignee_id
            else None
        )
    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "The current assignment is invalid."},
            status=400,
        )

    assignee = User.objects.filter(
        pk=staff_user_id,
        is_active=True,
        is_staff=True,
    ).first()
    if (
        assignee is None
        or not has_chat_permission(assignee, "view")
        or not has_chat_permission(assignee, "change")
    ):
        return JsonResponse(
            {"success": False, "message": "That staff member cannot be assigned live chats."},
            status=400,
        )

    with transaction.atomic():
        conversation = get_object_or_404(
            LiveChatConversation.objects.select_for_update(),
            pk=conversation_id,
        )
        if conversation.status == "closed":
            return JsonResponse(
                {"success": False, "message": "Closed conversations cannot be assigned."},
                status=409,
            )
        if conversation.assigned_to_id != expected_assignee_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "The assignment changed. Refresh the conversation and try again.",
                },
                status=409,
            )
        if conversation.assigned_to_id == assignee.pk:
            return JsonResponse(
                {
                    "success": True,
                    "status": conversation.status,
                    "assigned_to": assignee.get_full_name() or assignee.username,
                    "assigned_to_id": assignee.pk,
                }
            )

        previous_assignee = conversation.assigned_to
        assignee_name = assignee.get_full_name() or assignee.username
        if previous_assignee:
            previous_assignee_name = (
                previous_assignee.get_full_name() or previous_assignee.username
            )
            assignment_message = (
                f"This conversation was reassigned from {previous_assignee_name} "
                f"to {assignee_name} by "
                f"{request.user.get_full_name() or request.user.username}."
            )
            activity_title = "Live Chat Reassigned"
        else:
            assignment_message = (
                f"{assignee_name} was assigned to this conversation by "
                f"{request.user.get_full_name() or request.user.username}."
            )
            activity_title = "Live Chat Assigned"

        conversation.status = "active"
        conversation.mode = "human"
        conversation.assigned_to = assignee
        conversation.save(
            update_fields=["status", "mode", "assigned_to", "updated_at"]
        )
        system_message = LiveChatMessage.objects.create(
            conversation=conversation,
            sender_type="system",
            sender_name="YD Cleaning Support",
            message=assignment_message,
        )
        from dashboard.models import ActivityLog

        ActivityLog.objects.create(
            user=request.user,
            action_type="system",
            title=activity_title,
            description=(
                f"Conversation #{conversation.pk}: {assignment_message}"
            ),
        )
        queue_dashboard_update(conversation.id, "conversation.assigned")

    send_conversation_event(
        conversation.id,
        {
            "type": "chat_system",
            "message": assignment_message,
            "message_id": system_message.pk,
            "status": "active",
            "assigned_to_id": assignee.pk,
            "assigned_to": assignee.get_full_name() or assignee.username,
        },
    )
    return JsonResponse(
        {
            "success": True,
            "status": conversation.status,
            "assigned_to": assignee.get_full_name() or assignee.username,
            "assigned_to_id": assignee.pk,
        }
    )


# =========================================================
# STAFF CLOSE CHAT
# =========================================================

@login_required
@csrf_protect
@require_POST
def live_chat_close(
    request,
    conversation_id,
):

    if not has_chat_permission(request.user, "change"):

        return JsonResponse(
            {
                "success": False,
                "message": "Staff access required.",
            },
            status=403,
        )
    if not allow_live_chat_action(
        f"staff:{request.user.pk}",
        "staff-mutate",
        30,
    ):
        return JsonResponse(
            {"success": False, "message": "Please wait before changing this conversation."},
            status=429,
        )

    conversation = get_object_or_404(
        LiveChatConversation,
        id=conversation_id,
    )

    with transaction.atomic():
        conversation = LiveChatConversation.objects.select_for_update().get(
            id=conversation_id
        )

        if conversation.status == "closed":
            return JsonResponse({"success": True, "status": "closed"})

        conversation.status = "closed"
        conversation.mode = "closed"
        conversation.closed_at = timezone.now()
        conversation.save(
            update_fields=["status", "mode", "closed_at", "updated_at"]
        )
        close_message = (
            "This conversation was closed by "
            f"{request.user.get_full_name() or request.user.username}."
        )
        system_message = LiveChatMessage.objects.create(
            conversation=conversation,
            sender_type="system",
            sender_name="YD Cleaning Support",
            message=close_message,
        )
        from dashboard.models import ActivityLog

        ActivityLog.objects.create(
            user=request.user,
            action_type="system",
            title="Live Chat Closed",
            description=f"Conversation #{conversation.pk} closed by staff.",
        )
        queue_dashboard_update(conversation.id, "conversation.closed")

    send_conversation_event(
        conversation.id,
        {
            "type": "chat_system",
            "message": close_message,
            "message_id": system_message.pk,
            "status": "closed",
        },
    )

    return JsonResponse(
        {
            "success": True,
            "status": "closed",
        }
    )