import os
from google import genai
from google.genai import types
from PIL import Image
import json

api_key = 'AQ.Ab8RN6JeAR1jCZaGpC-HcXZBHrtG-TK0oZQL6aQCMMm3vuyHYQ'
client = genai.Client(api_key=api_key)

img_path = r'C:\Users\User\.gemini\antigravity\brain\aa33a98d-e5ca-49c3-8921-4c2f1f8f6cb8\media__1783439939372.png'
img = Image.open(img_path)

prompt = """You are an expert data extraction AI. Extract the contact information from this screenshot of a chat interface.
Return a valid JSON list of objects. Each object should have the following keys:
"name", "email", "phone", "company", "source", "linkedin"
If a field is missing, set its value to null.
Only output the raw JSON array.
"""

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt, img],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
        )
    )
    print('RAW RESPONSE:')
    print(response.text)
except Exception as e:
    print('ERROR:', e)
