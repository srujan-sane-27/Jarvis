import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import List, Dict, Any
from src.config import get_settings
from src.tools.base import BaseTool, require_authorization

logger = logging.getLogger("jarvis.tools.mail")


class MailTool(BaseTool):
    """Handles email reading, search, and secured email dispatch."""

    name = "mail_manager"
    description = "Read unread emails, search inbox, or securely send an email."

    def __init__(self):
        self.settings = get_settings()

    def _decode_header_str(self, header_val: str) -> str:
        """Safely decodes email headers."""
        if not header_val:
            return ""
        decoded_parts = decode_header(header_val)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or "utf-8", errors="replace"))
                except Exception:
                    result.append(part.decode("latin1", errors="replace"))
            else:
                result.append(str(part))
        return " ".join(result)

    async def fetch_unread_emails(self, limit: int = 5) -> str:
        """Fetches recent unread emails using IMAP."""
        if not self.settings.EMAIL_APP_PASSWORD:
            return (
                "Mail access notice: EMAIL_APP_PASSWORD is not configured in .env. "
                "To enable live inbox reading for sanesrujan84@gmail.com, generate a Google App Password "
                "at https://myaccount.google.com/apppasswords and add it to your .env file."
            )

        try:
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(self.settings.EMAIL_IMAP_SERVER, self.settings.EMAIL_IMAP_PORT)
            mail.login(self.settings.EMAIL_USER, self.settings.EMAIL_APP_PASSWORD)
            mail.select("inbox")

            status, response = mail.search(None, "UNSEEN")
            if status != "OK":
                return "Could not retrieve emails from inbox."

            email_ids = response[0].split()
            if not email_ids:
                return f"No unread emails found in {self.settings.EMAIL_USER}'s inbox. All caught up, Boss."

            recent_ids = email_ids[-limit:]
            emails_summary = []

            for eid in reversed(recent_ids):
                res, msg_data = mail.fetch(eid, "(RFC822.HEADER)")
                if res != "OK":
                    continue
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = self._decode_header_str(msg.get("Subject", "No Subject"))
                        sender = self._decode_header_str(msg.get("From", "Unknown Sender"))
                        date_str = msg.get("Date", "")
                        emails_summary.append(f"• From: {sender}\n  Subject: {subject}\n  Date: {date_str}")

            mail.close()
            mail.logout()

            return f"Found {len(emails_summary)} unread email(s) for {self.settings.EMAIL_USER}:\n\n" + "\n\n".join(emails_summary)

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return f"Error connecting to mail server: {str(e)}"

    @require_authorization
    async def send_email(self, recipient: str, subject: str, body: str) -> str:
        """Sends an email via SMTP. High-privilege action requiring voice authorization."""
        if not self.settings.EMAIL_APP_PASSWORD:
            return (
                "Mail dispatch error: EMAIL_APP_PASSWORD not configured in .env. "
                "Please configure an App Password for sanesrujan84@gmail.com to send emails."
            )

        try:
            msg = MIMEMultipart()
            msg["From"] = f"JARVIS <{self.settings.EMAIL_USER}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.settings.EMAIL_SMTP_SERVER, self.settings.EMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.EMAIL_USER, self.settings.EMAIL_APP_PASSWORD)
                server.send_message(msg)

            return f"Email successfully dispatched to '{recipient}' with subject '{subject}'."

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return f"Failed to send email: {str(e)}"


# Global singleton tool instance
mail_tool = MailTool()
