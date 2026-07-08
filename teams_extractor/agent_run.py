import time
from automation import TeamsExtractor
from deduplicator import process_message
import parser
import exporter

def run_agent_extraction(target_text=None, max_scrolls=20):
    print("Agent: You have 5 seconds to open and focus your Microsoft Teams window...")
    for i in range(5, 0, -1):
        print(f"Agent: Starting in {i}...")
        time.sleep(1)
        
    print("Agent: Connecting to Teams...")
    extractor = TeamsExtractor()
    if not extractor.connect():
        print("Agent: Error - Could not find Microsoft Teams window on your screen. Make sure it's open!")
        return

    print("Agent: Connected! Starting aggressive extraction...")
    
    for i in range(max_scrolls):
        print(f"Agent: Scrolling and extracting batch {i+1}...")
        visible_msgs = extractor.extract_visible_text()
        
        found_target = False
        saved_count = 0
        
        for msg in visible_msgs:
            if target_text and target_text.lower() in msg["text"].lower():
                found_target = True

            # Basic check to avoid duplicates in raw message db
            existing = extractor.db.query(extractor.crud.models.RawMessage).filter_by(
                raw_text=msg["text"], timestamp=msg["timestamp"]
            ).first()
            
            if not existing:
                raw_msg = extractor.crud.create_raw_message(extractor.db, msg["text"], msg["sender"], msg["timestamp"])
                extracted_data = parser.extract_entities(msg["text"])
                process_message(extractor.db, raw_msg, extracted_data)
                saved_count += 1
                
        print(f"Agent: Found {saved_count} new messages.")
        
        if found_target:
            print(f"Agent: Target text '{target_text}' found! Stopping extraction.")
            break
            
        extractor.scroll_up()
        time.sleep(0.3)
        
    extractor.db.close()
    
    print("Agent: Extraction complete. Exporting to Excel...")
    path = exporter.export_contacts_to_excel()
    print(f"Agent: Done! Data exported to {path}")

if __name__ == "__main__":
    import sys
    target = None
    limit = 15
    
    if len(sys.argv) > 1:
        # If the first argument is a number, treat it as the limit. Otherwise, it's the target text.
        try:
            limit = int(sys.argv[1])
        except ValueError:
            target = sys.argv[1]
            limit = 500
    
    if target:
        print(f"Agent: Will run until the text '{target}' is found.")
    else:
        print(f"Agent: Will run for a fixed {limit} scrolls.")
        
    run_agent_extraction(target_text=target, max_scrolls=limit)
