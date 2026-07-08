import uuid

def process_and_merge_contact(existing_records, contact_data, message_id):
    """
    Deduplicates and merges extracted contact data entirely in memory.
    Returns (status, merged_record) where status is 'NEW', 'DUPLICATE', or 'EMPTY'.
    """
    if not contact_data["primary_email"] and not contact_data["primary_phone"] and not contact_data["linkedin"]:
        return "EMPTY", None
        
    is_duplicate = False
    merged_rec = None
    
    for i, ext_rec in enumerate(existing_records):
        if (contact_data["primary_email"] and ext_rec.get("primary_email") == contact_data["primary_email"]) or \
           (contact_data["primary_phone"] and ext_rec.get("primary_phone") == contact_data["primary_phone"]) or \
           (contact_data["linkedin"] and ext_rec.get("linkedin") == contact_data["linkedin"]):
            is_duplicate = True
            
            # Merge fields
            if contact_data["primary_name"] and not ext_rec.get("primary_name"):
                ext_rec["primary_name"] = contact_data["primary_name"]
            if contact_data["title"] and not ext_rec.get("title"):
                ext_rec["title"] = contact_data["title"]
                
            # Append source message
            sources = ext_rec.get("source_message_ids", "").split(";")
            if message_id not in sources:
                sources.append(message_id)
            ext_rec["source_message_ids"] = ";".join([s for s in sources if s])
            
            ext_rec["duplicate_status"] = "Merged"
            merged_rec = ext_rec
            existing_records[i] = ext_rec
            break
            
    if not is_duplicate:
        contact_data["contact_id"] = str(uuid.uuid4())[:8]
        contact_data["source_message_ids"] = message_id
        contact_data["duplicate_status"] = "Unique"
        contact_data["confidence_score"] = "High" if contact_data["primary_email"] else "Medium"
        existing_records.append(contact_data)
        merged_rec = contact_data
        
    return "DUPLICATE" if is_duplicate else "NEW", merged_rec
