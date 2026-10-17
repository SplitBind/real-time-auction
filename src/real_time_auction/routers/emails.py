import shutil
import os
from typing import List
from fastapi import APIRouter, Request, Form, File, UploadFile, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from email_service import send_dispatch_email_task

router = APIRouter(prefix="/api/v1/emails", tags=["Emails"])
templates = Jinja2Templates(directory="templates")

TEMP_UPLOAD_DIR = "temp_attachments"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

# Admin page view with users list injection
@router.get("/dispatch", response_class=HTMLResponse)
async def email_dispatch_view(request: Request):
    # Fetch your application users from DB here (Mocked for illustration)
    mock_users = [
        {"id": 1, "email": "collector1@example.com"},
        {"id": 2, "email": "bidder_pro@example.com"},
        {"id": 3, "email": "whale_bidder@example.com"}
    ]
    
    return templates.TemplateResponse("admin/email_dispatch.html", {
        "request": request,
        "all_users": mock_users
    })

# POST handler for multi-recipient dispatch with optional file attachment
@router.post("/send")
async def send_bulk_emails(
    recipient_emails: List[str] = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    attachment: UploadFile = File(None)
):
    file_path = None
    
    # Save uploaded file temporarily if provided (APK, documents, etc.)
    if attachment and attachment.filename:
        file_path = os.path.join(TEMP_UPLOAD_DIR, attachment.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(attachment.file, buffer)

    # Queue asynchronous tasks via Celery for each selected user
    for recipient in recipient_emails:
        send_dispatch_email_task.delay(
            recipient=recipient,
            subject=subject,
            message=message,
            file_path=file_path
        )

    return RedirectResponse(url="/api/v1/emails/dispatch?success=true", status_code=303)
