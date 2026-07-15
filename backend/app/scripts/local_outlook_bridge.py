import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import win32com.client
import pythoncom
import logging
import socket
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local Outlook Bridge")

# Allow CORS so the Vercel frontend or localhost frontend can hit this local server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Recipient(BaseModel):
    recruiter_name: Optional[str] = None
    email: Optional[str] = None

class BulkMailPayload(BaseModel):
    recipients: List[Recipient]
    cc: Optional[str] = ""
    bcc: Optional[str] = ""
    subject: Optional[str] = ""
    body: Optional[str] = ""
    signature: Optional[str] = ""

class SingleMailPayload(BaseModel):
    to: str
    from_email: Optional[str] = None
    subject: Optional[str] = ""
    body: Optional[str] = ""
    cc: Optional[str] = ""
    bcc: Optional[str] = ""

@app.get("/health")
def get_health():
    status = {
        "status": "healthy",
        "outlook_running": False,
        "internet_available": False,
        "mailbox_accessible": False,
        "error": None
    }
    
    # Check internet
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        status["internet_available"] = True
    except Exception as e:
        status["error"] = f"No internet connection: {e}"
        status["status"] = "unhealthy"
        return status
        
    try:
        pythoncom.CoInitialize()
        
        # Check Outlook running
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            status["outlook_running"] = True
        except Exception as e:
            status["error"] = f"Outlook is not running: {e}"
            status["status"] = "unhealthy"
            return status
            
        # Check mailbox accessible
        try:
            ns = outlook.GetNamespace("MAPI")
            inbox = ns.GetDefaultFolder(6) # Inbox
            if inbox:
                status["mailbox_accessible"] = True
        except Exception as e:
            status["error"] = f"Mailbox not accessible: {e}"
            status["status"] = "unhealthy"
            
    except Exception as e:
        status["error"] = str(e)
        status["status"] = "unhealthy"
    finally:
        pythoncom.CoUninitialize()
        
    return status

@app.post("/send-one")
async def send_single_mail(payload: SingleMailPayload):
    try:
        pythoncom.CoInitialize()
        outlook = win32com.client.Dispatch("Outlook.Application")
        
        mail = outlook.CreateItem(0) # 0 = olMailItem
        clean_email = payload.to.strip()
        mail.To = clean_email
        
        if payload.cc:
            mail.CC = payload.cc.strip()
        if payload.bcc:
            mail.BCC = payload.bcc.strip()
            
        mail.Subject = payload.subject or ""
        mail.Body = payload.body or ""
        
        mail.Recipients.ResolveAll()
        
        # Record item count in sent folder before sending to verify
        ns = outlook.GetNamespace("MAPI")
        sent_folder = ns.GetDefaultFolder(5) # Sent items
        items_before = sent_folder.Items.Count
        
        mail.Send()
        
        # Try to verify if it got to the outbox or sent folder
        # For simplicity, we just mark outlook_accepted = True if Send() didn't raise
        
        return {
            "success": True,
            "outlook_accepted": True,
            "sent_folder_updated": None, # Hard to track synchronously as sending is async in Outlook
            "error": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending single mail: {e}")
        return {
            "success": False,
            "outlook_accepted": False,
            "sent_folder_updated": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    finally:
        pythoncom.CoUninitialize()

@app.post("/send-bulk")
async def send_bulk_mail(payload: BulkMailPayload):
    try:
        # Initialize COM library for the thread
        pythoncom.CoInitialize()
        
        # Connect to the running Outlook instance
        outlook = win32com.client.Dispatch("Outlook.Application")
        
        sent_count = 0
        
        # We loop through each recipient and send an individual email
        for rec in payload.recipients:
            if not rec.email:
                continue
                
            try:
                mail = outlook.CreateItem(0) # 0 = olMailItem
                
                # Clean the email
                clean_email = rec.email.strip()
                
                mail.To = clean_email
                
                if payload.cc:
                    mail.CC = payload.cc.strip()
                if payload.bcc:
                    mail.BCC = payload.bcc.strip()
                    
                mail.Subject = payload.subject or ""
                
                # Construct the final body
                final_body = payload.body or ""
                if payload.signature:
                    final_body += f"\n\n{payload.signature}"
                    
                mail.Body = final_body
                
                # Force resolution (sometimes prevents the "does not recognize names" error)
                mail.Recipients.ResolveAll()
                
                mail.Send()
                sent_count += 1
                logger.info(f"Sent email to {clean_email}")
            except Exception as inner_e:
                logger.error(f"Failed to send to {rec.email}: {inner_e}")
                continue

        return {"status": "success", "message": f"Successfully queued {sent_count} emails via Outlook."}

        
    except Exception as e:
        logger.error(f"Error sending mail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    print("="*60)
    print("  LOCAL OUTLOOK BRIDGE IS RUNNING")
    print("  Listening on http://127.0.0.1:1337")
    print("  Keep this terminal open to allow the TalentOpsAI site to send emails.")
    print("="*60)
    uvicorn.run(app, host="127.0.0.1", port=1337)
