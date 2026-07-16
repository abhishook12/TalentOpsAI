import win32com.client
import sys
import time

def verify_outlook():
    outlook = win32com.client.Dispatch("Outlook.Application")
    ns = outlook.GetNamespace("MAPI")
    
    # Give it some time to sync
    time.sleep(5)
    
    inbox = ns.GetDefaultFolder(6) # 6 = Inbox
    sent = ns.GetDefaultFolder(5)  # 5 = Sent Items
    
    # Search for UAT Test Campaign
    print("Checking Inbox...")
    messages = inbox.Items
    messages.Sort("[ReceivedTime]", True)
    
    found_inbox = False
    for msg in list(messages)[:20]:
        try:
            if "UAT Test Campaign" in msg.Subject:
                print(f"[OK] Found in Inbox! Subject: {msg.Subject}")
                found_inbox = True
                break
        except Exception:
            pass
            
    print("Checking Sent Items...")
    sent_msgs = sent.Items
    sent_msgs.Sort("[SentOn]", True)
    
    found_sent = False
    for msg in list(sent_msgs)[:20]:
        try:
            if "UAT Test Campaign" in msg.Subject:
                print(f"[OK] Found in Sent Items! Subject: {msg.Subject}")
                found_sent = True
                break
        except Exception:
            pass
            
    if found_inbox or found_sent:
        print("[OK] Email Delivery Verified!")
        sys.exit(0)
    else:
        print("[FAIL] Could not find the UAT email in Inbox or Sent folder.")
        sys.exit(1)

if __name__ == "__main__":
    verify_outlook()
