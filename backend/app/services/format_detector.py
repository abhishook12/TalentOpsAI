import pandas as pd

def detect_format(df: pd.DataFrame) -> dict:
    headers = [str(h).lower().strip() for h in df.columns]
    
    # 1. Wide Multi-Column
    # Check if there are multiple emails or phones
    email_cols = sum(1 for h in headers if 'email' in h or 'e-mail' in h)
    phone_cols = sum(1 for h in headers if 'phone' in h or 'mobile' in h or 'cell' in h)
    
    if email_cols > 1 or phone_cols > 1:
        return {"detected_format": "wide_multi_column", "confidence": 90}
        
    # 2. Vertical Multi-Value
    # Typical columns: Name, Company, Field Type, Field Value
    has_type = any('type' in h for h in headers)
    has_value = any('value' in h for h in headers)
    
    if has_type and has_value:
        name_col = next((c for c in df.columns if 'name' in c.lower()), None)
        if name_col and df[name_col].duplicated().any():
            return {"detected_format": "vertical_multi_value", "confidence": 95}
            
    # 3. Company First
    if len(headers) >= 2 and 'company' in headers[0] and 'name' in headers[1]:
        return {"detected_format": "company_first", "confidence": 85}
        
    # 4. LinkedIn Text
    # Usually 1 column, many rows, text like "2nd degree connection"
    if len(headers) == 1 or len(df.columns) == 1:
        sample = df.head(20).to_string()
        if "degree connection" in sample or "Message" in sample or "Follow" in sample:
            return {"detected_format": "linkedin_text", "confidence": 98}

    # 5. Standard Row
    # Need to have at least a name and email or phone
    if any('name' in h for h in headers) and (any('email' in h for h in headers) or any('phone' in h for h in headers)):
        return {"detected_format": "standard_row", "confidence": 80}
        
    # 6. Company Block
    # Check if company name repeats but people change.
    # Actually, hard to detect purely from headers.
    
    # Default to unknown
    return {"detected_format": "unknown_mixed", "confidence": 50}
