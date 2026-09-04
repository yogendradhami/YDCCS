from django.db import models
from django.contrib.auth.models import User


from customers.models import Customer


class SupportTicket(models.Model):

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="support_tickets"
    )

    subject = models.CharField(max_length=255)

    message = models.TextField()

    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject


class SupportTicketReply(models.Model):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_ticket_replies",
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply to ticket #{self.ticket_id}"


class ChatEnquiry(models.Model):

    ENQUIRY_TYPE_CHOICES = [
        ("quote", "Get a Quote"),
        ("booking", "Book a Cleaning"),
        ("service", "Service Question"),
        ("general", "General Question"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("resolved", "Resolved"),
    ]

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    enquiry_type = models.CharField(
        max_length=20,
        choices=ENQUIRY_TYPE_CHOICES,
        default="general",
    )
    service = models.CharField(max_length=150, blank=True)
    suburb = models.CharField(max_length=100, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chat Enquiry"
        verbose_name_plural = "Chat Enquiries"

    def __str__(self):
        return f"{self.name} - {self.get_enquiry_type_display()}"


class ChatConversation(models.Model):

    STATUS_CHOICES = [
        ("bot", "Bot Handling"),
        ("waiting", "Waiting for Staff"),
        ("active", "Live With Staff"),
        ("closed", "Closed"),
    ]

    name = models.CharField(max_length=150, blank=True)

    email = models.EmailField(blank=True)

    phone = models.CharField(max_length=30, blank=True)

    session_key = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="bot",
        db_index=True,
    )

    assigned_staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_chat_conversations",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Chat Conversation"
        verbose_name_plural = "Chat Conversations"

    def __str__(self):
        if self.name:
            return f"{self.name} - Chat #{self.id}"

        return f"Chat #{self.id}"


class ChatMessage(models.Model):

    SENDER_CHOICES = [
        ("customer", "Customer"),
        ("bot", "Automatic Assistant"),
        ("staff", "Staff"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender_type = models.CharField(
        max_length=20,
        choices=SENDER_CHOICES,
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_chat_messages",
    )

    message = models.TextField()

    is_automatic = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_sender_type_display()} - Chat #{self.conversation_id}"


class LiveChatConversation(models.Model):

    STATUS_CHOICES = [
        ("waiting", "Waiting"),
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    session_key = models.CharField(
        max_length=100,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="waiting",
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="live_chat_conversations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"


class LiveChatMessage(models.Model):

    SENDER_CHOICES = [
        ("customer", "Customer"),
        ("staff", "Staff"),
        ("bot", "Automatic Assistant"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(
        LiveChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender_type = models.CharField(
        max_length=20,
        choices=SENDER_CHOICES,
    )

    sender_name = models.CharField(
        max_length=150,
        blank=True,
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender_type}: {self.message[:50]}"