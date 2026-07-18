import requests
import json
import time

def main():
    emails = []
    
    # Using specific mailinator inboxes that we can check publicly
    base_name = f"talentops.test.{int(time.time())}"
    
    for i in range(1, 6):
        email = f"{base_name}.{i}@mailinator.com"
        emails.append({
            "address": email,
            "username": f"{base_name}.{i}",
            "domain": "mailinator.com"
        })
        print(f"Created: {email}")
        
    # Duplicate
    emails.append({
        "address": f"{base_name}.1@mailinator.com",
        "username": f"{base_name}.1",
        "domain": "mailinator.com",
        "note": "duplicate"
    })
    
    # Invalid
    emails.append({
        "address": "invalid-format-email",
        "username": "invalid-format-email",
        "domain": "",
        "note": "invalid"
    })
        
    with open("test_inboxes.json", "w") as f:
        json.dump(emails, f, indent=4)
        
    print("Successfully created test inboxes list.")

if __name__ == "__main__":
    main()
