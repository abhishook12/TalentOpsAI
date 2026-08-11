import re

with open(r'C:\TalentOpsAI\backend\app\routes\ai.py', 'r') as f:
    content = f.read()

# Replace imports
content = content.replace('import google.generativeai as genai', 'from google import genai')
content = content.replace('''if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)''', '''# Initialization is per-client now''')

# Replace get_model
old_get_model = '''def get_model():
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set.")
    # Track call to enforce 70% rate limit
    track_gemini_call()
    # Use flash for speed
    return genai.GenerativeModel('gemini-2.5-flash')'''

new_get_model = '''def get_client():
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set.")
    # Track call to enforce 70% rate limit
    track_gemini_call()
    return genai.Client(api_key=GEMINI_API_KEY)'''

content = content.replace(old_get_model, new_get_model)

# Replace model = get_model()
content = content.replace('model = get_model()', 'client = get_client()')

# Replace response = model.generate_content(prompt)
content = content.replace('response = model.generate_content(prompt)', '''response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )''')

with open(r'C:\TalentOpsAI\backend\app\routes\ai.py', 'w') as f:
    f.write(content)

print("Replaced successfully")
