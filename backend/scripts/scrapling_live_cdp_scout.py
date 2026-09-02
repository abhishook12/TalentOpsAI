"""
Scrapling Live Chrome CDP Scout — Zero-Cost Authenticated Profiler.

Connects directly to your running Google Chrome browser via Chrome DevTools Protocol (CDP)
on port 9222, reusing your logged-in LinkedIn session for 100% authwall-free scraping.
"""

import argparse, json, asyncio, os, sys
from scrapling.core.ai import ScraplingMCPServer

async def run_cdp_scout(target_urls, cdp_port=9222):
    server = ScraplingMCPServer()
    cdp_url = f"http://localhost:{cdp_port}"
    print(f"Connecting Scrapling to live Chrome browser on {cdp_url}...")
    
    try:
        sess = await server.open_session(session_type="dynamic", cdp_url=cdp_url)
        print(f"[SUCCESS] Connected to live Chrome! Session ID: {sess.session_id}")
    except Exception as e:
        print(f"[ERROR] Could not connect to Chrome on {cdp_url}.")
        print("To enable CDP, launch Chrome with: chrome.exe --remote-debugging-port=9222")
        return

    for url in target_urls:
        print(f"\nScraping live profile: {url}...")
        try:
            res = await server.session_fetch(session_id=sess.session_id, url=url)
            print(f"Status: {res.status} | URL: {res.url}")
            print("Extracted content snippet:")
            for chunk in res.content[:2]:
                print(chunk+100] + "...")
        except Exception as se:
            print(f"Fetch error on {url}: {se}")

    await server.close_session(session_id=sess.session_id)
    print("\nLive CPP session closed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrapling Live Chrome CPP Scout")
    parser.add_argument("--url", type=str, help="Single profile URL to scrape")
    parser.add_argument("--file", type=str, help="File with URLs to scrape")
    parser.add_argument("--port", type=int, default=9222, help="Chrome CPP port (default: 9222)")
    args = parser.parse_args()

    urls = [args.url] if args.url else []
    if args.file and os.path.exists(args.file):
        with open(args.file, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    if not urls:
        urls = ["https://quotes.toscrape.com"]

    asyncio.run(run_cdp_scout(urls, args.port))
