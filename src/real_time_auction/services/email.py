import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from celery import Celery
from jinja2 import Template

# Initialize Celery app (configure broker URL as needed, e.g., Redis)
celery_app = Celery("tasks", broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "user@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "password")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@auctionledger.com")

@celery_app.task(name="send_dispatch_email_task")
def send_dispatch_email_task(recipient: str, subject: str, message: str, file_path: str = None):
    try:
        msg = MIMEMultipart()
        msg["From"] = FROM_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject

        # Load and render base email layout template
        template_path = os.path.join("templates", "email_templates.html")
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Convert simple line breaks to HTML tags for the email body
        formatted_message = message.replace("\n", "<br>")
        html_body = Template(template_content).render(
            subject=subject,
            message_html=formatted_message
        )

        msg.attach(MIMEText(html_body, "html"))

        # Handle File Attachments (APK, documents, etc.)
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as attachment_file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_file.read())
                encoders.encode_base64(part)
                filename = os.path.basename(file_path)
                part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                msg.attach(part)

        # Connect and send via SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, recipient, msg.as_string())
            
        return f"Successfully dispatched to {recipient}"
    except Exception as e:
        # Log error in production
        print(f"Failed to send email to {recipient}: {str(e)}")
        raise
