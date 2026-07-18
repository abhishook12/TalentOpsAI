import win32com.client
import sys
import time
from datetime import datetime, timedelta

def verify_outlook(subject_prefix):
    outlook = win32com.client.Dispatch("Outlook.Application")
    ns = outlook.GetNamespace("MAPI")
    
    # Give the bridge some time to process and sync
    time.sleep(10)
    
    sent = ns.GetDefaultFolder(5)  # 5 = Sent Items
    print(f"Checking Sent Items for subject containing: '{subject_prefix}'")
    
    sent_msgs = sent.Items
    sent_msgs.Sort("[SentOn]", True)
    
    found_count = 0
    messages_found = []
    
    for msg in list(sent_msgs)[:50]:
        try:
            if subject_prefix in msg.Subject:
                print(f"[OK] Found in Sent Items!")
                print(f"     Subject: {msg.Subject}")
                print(f"     To: {msg.To}")
                print(f"     CC: {msg.CC}")
                print(f"     BCC: {msg.BCC}")
                print(f"     SentOn: {msg.SentOn}")
                found_count += 1
                messages_found.append({
                    "subject": msg.Subject,
                    "to": msg.To,
                    "cc": msg.CC,
                    "bcc": msg.BCC
                })
        except Exception as e:
            pass
            
    print(f"\nTotal messages found with prefix '{subject_prefix}': {found_count}")
    return messages_found

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prefix = sys.argv[1]
        verify_outlook(prefix)
    else:
        print("Please provide a subject prefix to search for.")
