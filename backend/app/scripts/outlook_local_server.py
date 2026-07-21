import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import win32com.client
import pythoncom
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OutlookLocalServer")

app = FastAPI(title="Local Outlook Bridge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_outlook_namespace():
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        return outlook.GetNamespace("MAPI")
    except Exception as e:
        logger.error(f"Failed to connect to Outlook: {e}")
        raise HTTPException(status_code=500, detail="Cannot connect to Outlook. Ensure it is running.")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Outlook Local Server"}

@app.get("/api/folders")
def get_folders():
    namespace = get_outlook_namespace()
    # 5 = Sent Items, 6 = Inbox
    # Let's return Sent Items explicitly since that's mostly what they want for "Reuse"
    try:
        sent_folder = namespace.GetDefaultFolder(5)
        return [
            {"id": "5", "name": sent_folder.Name, "count": sent_folder.Items.Count},
            {"id": "6", "name": namespace.GetDefaultFolder(6).Name, "count": namespace.GetDefaultFolder(6).Items.Count}
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/emails")
def get_emails(
    folder_id: str = "5", 
    limit: int = 50, 
    offset: int = 0,
    search: Optional[str] = None
):
    namespace = get_outlook_namespace()
    try:
        folder = namespace.GetDefaultFolder(int(folder_id))
        items = folder.Items
        # Sort by ReceivedTime descending
        items.Sort("[ReceivedTime]", True)
        
        results = []
        count = 0
        skipped = 0
        
        # Iterating over COM items is slow, so we implement simple offset/limit
        for i in range(1, items.Count + 1):
            if count >= limit:
                break
                
            try:
                item = items.Item(i)
                # Only process Mail items (Class 43)
                if item.Class != 43:
                    continue
                    
                # Search filter
                if search:
                    search_lower = search.lower()
                    if not (search_lower in (item.Subject or "").lower() or search_lower in (item.To or "").lower()):
                        continue
                        
                if skipped < offset:
                    skipped += 1
                    continue
                    
                results.append({
                    "id": item.EntryID,
                    "subject": item.Subject,
                    "to": item.To,
                    "from": item.SenderName if hasattr(item, "SenderName") else "",
                    "date": str(item.ReceivedTime) if hasattr(item, "ReceivedTime") else "",
                    "snippet": item.Body[:150] + "..." if item.Body else ""
                })
                count += 1
            except Exception:
                # Some items might be inaccessible or throw errors
                continue
                
        return {"emails": results, "total": items.Count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/emails/{email_id}")
def get_email_details(email_id: str):
    namespace = get_outlook_namespace()
    try:
        # Get item by EntryID
        item = namespace.GetItemFromID(email_id)
        if item.Class != 43:
            raise HTTPException(status_code=400, detail="Item is not an email")
            
        return {
            "id": item.EntryID,
            "subject": item.Subject,
            "to": item.To,
            "from": item.SenderName if hasattr(item, "SenderName") else "",
            "date": str(item.ReceivedTime) if hasattr(item, "ReceivedTime") else "",
            "html_body": item.HTMLBody,
            "text_body": item.Body
        }
    except Exception as e:
        logger.error(f"Failed to fetch email {email_id}: {e}")
        raise HTTPException(status_code=404, detail="Email not found or inaccessible")

if __name__ == "__main__":
    logger.info("Starting Outlook Local Server on port 8080...")
    uvicorn.run(app, host="127.0.0.1", port=8080)
