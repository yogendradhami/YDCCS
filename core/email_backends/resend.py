import resend

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    """
    Django email backend using the Resend API.

    This allows existing Django email functionality such as:
        send_mail()
        EmailMessage()
        EmailMultiAlternatives()

    to continue working without changing each caller.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)

        self.api_key = getattr(settings, "RESEND_API_KEY", "")

        if self.api_key:
            resend.api_key = self.api_key

    def send_messages(self, email_messages):
        """
        Send a list of Django EmailMessage objects through Resend.
        """

        if not email_messages:
            return 0

        if not self.api_key:
            if self.fail_silently:
                return 0

            raise ValueError(
                "RESEND_API_KEY is not configured."
            )

        sent_count = 0

        for message in email_messages:
            try:
                if self._send(message):
                    sent_count += 1

            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count

    def _send(self, message):
        """
        Convert a Django EmailMessage into a Resend API request.
        """

        recipients = list(message.to or [])

        if not recipients:
            return False

        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": recipients,
            "subject": message.subject,
        }

        # Django EmailMessage stores the normal text body here.
        body = message.body or ""

        # Handle HTML messages created using:
        #
        # send_mail(..., html_message=...)
        #
        # or EmailMultiAlternatives.
        alternatives = getattr(message, "alternatives", [])

        html_body = None

        for alternative in alternatives:
            if not alternative:
                continue

            try:
                content, mimetype = alternative
            except (TypeError, ValueError):
                continue

            if mimetype == "text/html":
                html_body = content
                break

        if html_body:
            payload["html"] = html_body
            payload["text"] = body
        else:
            payload["text"] = body

        # CC
        cc = list(getattr(message, "cc", []) or [])
        if cc:
            payload["cc"] = cc

        # BCC
        bcc = list(getattr(message, "bcc", []) or [])
        if bcc:
            payload["bcc"] = bcc

        # Reply-To
        reply_to = list(getattr(message, "reply_to", []) or [])
        if reply_to:
            payload["reply_to"] = reply_to

        # Attachments
        attachments = getattr(message, "attachments", []) or []

        if attachments:
            resend_attachments = []

            for attachment in attachments:
                if len(attachment) != 3:
                    continue

                filename, content, mimetype = attachment

                resend_attachments.append(
                    {
                        "filename": filename,
                        "content": content,
                    }
                )

            if resend_attachments:
                payload["attachments"] = resend_attachments

        response = resend.Emails.send(payload)

        return bool(response)
