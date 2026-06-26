import os
import json
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv('C:/TalentOpsAI/backend/.env')
keys = [k.strip() for k in os.environ.get('TAVILY_API_KEYS', '').split(',') if k.strip()]
client = TavilyClient(api_key=keys[0])
res = client.search(query='Recruiter OR "Talent Acquisition" at "nCino" LinkedIn', search_depth="advanced")
print(json.dumps(res, indent=2))
