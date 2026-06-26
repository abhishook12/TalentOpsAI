# TalentOps LinkedIn Recruiter Scraper

Standalone Chrome extension for scraping the currently open LinkedIn profile and sending the payload to a TalentOps backend endpoint.

## File structure

```text
linkedin-recruiter-extension/
├── manifest.json
├── background.js
├── content.js
├── popup.html
├── popup.css
├── popup.js
└── README.md
```

## Payload shape

```json
{
  "recruiter_name": "Jane Doe",
  "title": "Senior Technical Recruiter",
  "location": "Austin, Texas, United States",
  "company_name": "Acme Staffing",
  "linkedin_url": "https://www.linkedin.com/in/example/",
  "source": "linkedin_chrome_extension",
  "scraped_at": "2026-06-22T10:11:12.000Z"
}
```

## Load locally

1. Open `chrome://extensions`
2. Turn on **Developer mode**
3. Click **Load unpacked**
4. Select `C:\TalentOpsAI\linkedin-recruiter-extension`

## Usage

1. Open a LinkedIn profile page.
2. Click the extension icon.
3. Set your API URL, for example `http://localhost:8000/recruiters/extension`
4. Save settings.
5. Click **Scrape current profile** to preview the JSON.
6. Click **Send to backend** to POST the JSON.

## Notes

- The extension is fully isolated from `frontend/` and `backend/`.
- It uses Manifest V3 with a background service worker.
- If your API expects authentication, paste a bearer token into the popup.
- If your backend expects a slightly different schema, only update this extension folder.
