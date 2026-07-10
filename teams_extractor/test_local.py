import os, json, time
from PIL import Image
from google import genai
from google.genai import types

with open('api_keys.txt') as f:
    api_keys = [line.strip() for line in f if line.strip()]

img_path = 'test_crop.png' if os.path.exists('test_crop.png') else 'debug_region2.png'
img = Image.open(img_path)
print(f'Testing with image: {img_path} ({img.size})')

prompt = """You are an expert data extraction AI analyzing a continuous vertical scroll of a chat interface.
Return a valid JSON list of objects. Each object should have the following keys:
"name", "title", "company", "location", "linkedin", "notes", "contacts", "is_continuation_from_above"
The "contacts" field should be a list of objects with "type" and "value".
"type" should be one of: "Work Email", "Personal Email", "Phone".
If a person has multiple emails or phones, include all of them in the "contacts" list.
Extract any available title, location, linkedin URL, or notes (e.g. if an email association is uncertain). If not present, leave as an empty string.

CRITICALLY IMPORTANT: The names appearing in small text at the very top of each message block are the SENDERS/RECRUITERS (e.g., 'Shruti Tiwari', 'Gaurav Ojha', 'Chauhan', 'Sharma', 'chitransh tiwari', 'Yatin Rawat'). DO NOT extract the sender's name. 

You MUST extract the candidate information (Name, Email, Phone, Company) located INSIDE the actual message content. 
EXTREME ACCURACY REQUIRED: DO NOT SKIP ANY CANDIDATES. You must extract EVERY SINGLE candidate contact block that is visible in the image. If you see an email address or a phone number, you MUST extract it and the associated candidate name. Missing a candidate is an absolute failure.

IMPORTANT: The image is a segment of a continuous scroll. If the very FIRST contact info shown at the top of the screen is missing its Name/Company header because the header was scrolled off-screen (e.g. it just shows a phone number or email belonging to the person from the previous screen), set "is_continuation_from_above": true for that object. Otherwise, false.
Only output the raw JSON array.
"""

success = False
for key_idx, key in enumerate(api_keys):
    try:
        print(f'Attempting extraction with Key {key_idx+1} using gemini-2.0-flash...')
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt, img],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
            )
        )
        data = json.loads(response.text)
        print(f'SUCCESS! Extracted {len(data)} contacts using Key {key_idx+1}.')
        for idx, c in enumerate(data[:3]):
            print(f'  Contact {idx+1}: {c.get("name", "Unknown")} - {len(c.get("contacts", []))} phone/emails')
        success = True
        break
    except Exception as e:
        err_str = str(e).lower()
        if '429' in err_str or 'quota' in err_str or 'exhausted' in err_str or '404' in err_str or 'not found' in err_str:
            print(f'Key {key_idx+1} busy/unsupported ({type(e).__name__}), trying next...')
            time.sleep(0.5)
        else:
            print(f'Unexpected error on Key {key_idx+1}: {e}')
            break

if not success:
    print('ALL KEYS EXHAUSTED OR FAILED!')
