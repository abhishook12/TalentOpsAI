#!/usr/bin/env python
from __future__ import annotations

import os
import json
import time
import random
import requests
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv('C:/TalentOpsAI/backend/.env')

BASE_URL = "http://localhost:8000"

def get_tavily_clients():
    keys = [k.strip() for k in os.environ.get('TAVILY_API_KEYS', '').split(',') if k.strip()]
    if not keys:
        return []
    return [TavilyClient(api_key=k) for k in keys]

import google.generativeai as genai
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def verify_profile_with_llm(name, title, content, target_company):
    prompt = f"""
    You are a strict data verification AI. 
    A recruiter profile was found in a search result for the company: "{target_company}".
    
    Name: {name}
    Title: {title}
    Snippet: {content}
    
    Task 1: Does this person CURRENTLY work at {target_company} as their primary/active job?
    (If their title says a different company, and the snippet only mentions {target_company} as past experience or a liked post, the answer is NO. They MUST currently work there).
    
    Task 2: Is this person located in North America (US/Canada)? 
    (If the location says India, UK, Philippines, etc., the answer is NO. If it is ambiguous, say YES but flag needsReview).
    
    Return a JSON object with:
    "isValid": boolean (true ONLY if they currently work at the target company AND are in North America)
    "needsReview": boolean (true if you are unsure or the text is ambiguous)
    "reason": string (a short 1-sentence explanation of your decision)
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Verification Error: {e}")
        return {"isValid": True, "needsReview": True, "reason": "LLM Verification Failed."}

def is_duplicate(name, company):
    try:
        res = requests.get(f"{BASE_URL}/recruiters/", params={"search": name, "company": company, "limit": 1})
        if res.status_code == 200:
            data = res.json()
            results = data if isinstance(data, list) else data.get("results", [])
            if len(results) > 0:
                return True
    except Exception as e:
        print(f"Error checking duplicate: {e}")
    return False

def add_and_enhance_recruiter(name, title, company, location=None, needs_review=False, review_reason=None):
    print(f"Adding new recruiter: {name} at {company}...")
    try:
        company_id = None
        res_c = requests.get(f"{BASE_URL}/companies/", params={"search": company, "limit": 1})
        if res_c.status_code == 200:
            c_data = res_c.json()
            if len(c_data) > 0:
                company_id = c_data[0].get("company_id")
        
        payload = {
            "recruiter_name": name,
            "email": f"tavily_discovery_{random.randint(100000,999999)}@missing.local",
            "specialization": title,
            "company_id": company_id,
            "location": location,
            "needs_review": needs_review,
            "review_reason": review_reason
        }
        res = requests.post(f"{BASE_URL}/recruiters/", json=payload)
        if res.status_code == 201:
            recruiter = res.json()
            r_id = recruiter.get("recruiter_id")
            print(f"Added successfully with ID {r_id}. Now enhancing...")
            
            res_e = requests.post(f"{BASE_URL}/recruiters/{r_id}/enhance", timeout=45)
            if res_e.status_code == 200:
                e_data = res_e.json()
                print(f"Enhanced {name} successfully! Email: {e_data.get('email')} | Phone: {e_data.get('phone')}")
            else:
                print(f"Enhance failed: {res_e.status_code}")
        else:
            print(f"Failed to add recruiter: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Error adding/enhancing: {e}")

def run_discovery():
    print("Starting Discovery Worker...")
    clients = get_tavily_clients()
    if not clients:
        print("No Tavily API keys found!")
        return

    current_client_idx = 0
    client = clients[current_client_idx]
    
    try:
        with open("target_companies.json", "r") as f:
            companies = json.load(f)
    except FileNotFoundError:
        print("target_companies.json not found!")
        return

    for i, company in enumerate(companies):
        print(f"\n--- Discovering recruiters at {company} ({i+1}/{len(companies)}) ---")
        query = f"\"Recruiter\" OR \"Talent Acquisition\" at \"{company}\" LinkedIn"
        
        retry_search = True
        while retry_search:
            try:
                response = client.search(query=query, search_depth="advanced")
                results = response.get("results", [])
                print(f"Found {len(results)} potential profiles from search.")
                
                for res in results:
                    title = res.get("title", "")
                    content = res.get("content", "")
                    
                    parts = title.split("-")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        job_title = parts[1].strip()
                        
                        if "linkedin" in name.lower():
                            continue
                            
                        # Strict junk name filtering
                        junk_keywords = ["meet", "our", "team", "careers", "jobs", "hiring", "opportunities"]
                        if any(junk in name.lower() for junk in junk_keywords):
                            print(f"Skipping junk profile: {name}")
                            continue
                            
                        # Name validation: MUST be a human, NOT a company
                        company_suffixes = ['inc', 'llc', 'ltd', 'global', 'services', 'talent', 'solutions', 'group', 'brands', 'technologies', 'consulting', 'partners']
                        if any(suffix in name.lower() for suffix in company_suffixes):
                            print(f"Skipping {name}: Looks like a company name, not a human.")
                            continue

                        # LLM Verification
                        print(f"Asking Gemini to verify {name}...")
                        llm_result = verify_profile_with_llm(name, title, content, company)
                        if not llm_result.get("isValid"):
                            print(f"LLM Rejected {name}: {llm_result.get('reason')}")
                            continue
                        
                        print(f"LLM Approved {name}: {llm_result.get('reason')}")

                        location = None # Let LLM fallback handle it or backend state extractor
                        if len(name.split()) >= 2 and all(part.isalpha() or '-' in part or '.' in part for part in name.split()):
                            if is_duplicate(name, company):
                                print(f"Skipping duplicate: {name}")
                                continue
                            
                            add_and_enhance_recruiter(name, job_title, company, location, llm_result.get("needsReview", False), llm_result.get("reason", ""))
                            time.sleep(5) 
                    else:
                        print(f"Could not parse title: {title}")
                retry_search = False # Success, break out of retry loop
                        
            except Exception as e:
                print(f"Error searching {company}: {e}")
                if "exceeds your plan" in str(e).lower() or "limit" in str(e).lower():
                    print(f"API key {current_client_idx + 1} exhausted!")
                    current_client_idx += 1
                    if current_client_idx >= len(clients):
                        print("ALL Tavily credits exhausted! Exiting.")
                        # Trigger Windows OS Popup Notification
                        os.system('powershell -Command "[System.Reflection.Assembly]::LoadWithPartialName(\'System.Windows.Forms\'); [System.Windows.Forms.MessageBox]::Show(\'ALL Tavily API Credits Exhausted! Please add a new key.\', \'TalentOps AI Alert\')"')
                        return # Hard exit
                    client = clients[current_client_idx]
                    print(f"Switching to API key {current_client_idx + 1} and retrying {company}...")
                else:
                    retry_search = False # Other error, skip company
            
        print("Cooling down before next company...")
        time.sleep(10)

if __name__ == "__main__":
    run_discovery()
