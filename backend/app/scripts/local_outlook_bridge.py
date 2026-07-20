import time
import requests
import win32com.client
import pythoncom
import logging
import argparse
import sys
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("OutlookBridge")

BRIDGE_VERSION = "2.0.0"

class BridgeState:
    def __init__(self):
        self.uptime_start = time.time()
        self.consecutive_errors = 0
        self.last_heartbeat = 0
        self.auth_token = None

def get_auth_token(base_url, email, password):
    logger.info(f"Authenticating as {email}...")
    try:
        # Check standard auth routes in case there is a prefix
        res = requests.post(f"{base_url}/auth/login", json={"email": email, "password": password}, timeout=10)
        if res.status_code == 404:
            res = requests.post(f"{base_url}/api/v1/auth/login", json={"email": email, "password": password}, timeout=10)
            
        if res.status_code == 200:
            token = res.json().get("token")
            logger.info("Authentication successful.")
            return token
        else:
            logger.error(f"Authentication failed: HTTP {res.status_code} - {res.text}")
            return None
    except Exception as e:
        logger.error(f"Authentication network error: {e}")
        return None

def get_auth_token_bypass(base_url):
    logger.info(f"Authenticating via dev bypass...")
    try:
        res = requests.post(f"{base_url}/api/bridge/auth-bypass", timeout=10)
        if res.status_code == 200:
            token = res.json().get("token")
            logger.info("Dev authentication successful.")
            return token
        else:
            logger.error(f"Dev authentication failed: HTTP {res.status_code} - {res.text}")
            return None
    except Exception as e:
        logger.error(f"Authentication network error: {e}")
        return None

def send_email_via_outlook(task, outlook):
    """Sends a single email using the provided Outlook application instance."""
    try:
        mail = outlook.CreateItem(0) # 0 = olMailItem
        mail.To = task.get("to_email", "")
        mail.Subject = task.get("subject", "")
        mail.HTMLBody = task.get("html_body", "")
        mail.Send()
        return True, None
    except Exception as e:
        return False, str(e)

def post_results(base_url, token, results):
    """Report a chunk of send results back to the backend."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        post_res = requests.post(f"{base_url}/api/bridge/results", json={"results": results}, headers=headers, timeout=15)
        
        # Try without /api if 404
        if post_res.status_code == 404:
            post_res = requests.post(f"{base_url}/bridge/results", json={"results": results}, headers=headers, timeout=15)
            
        if post_res.status_code == 200:
            logger.info(f"Reported results for {len(results)} email(s).")
            return True
        else:
            logger.error(f"Failed to report results: HTTP {post_res.status_code} - {post_res.text}")
            return False
    except Exception as e:
        logger.error(f"Network error reporting results: {e}")
        return False

def run_inner_loop(base_url, token, state):
    # Initialize COM for the main thread
    pythoncom.CoInitialize()

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        logger.info("Successfully connected to local Outlook application.")
    except Exception as e:
        logger.error(f"Failed to connect to Outlook: {e}")
        logger.error("Please ensure Microsoft Outlook is installed and configured on this machine.")
        # Return False to trigger supervisor retry logic with backoff
        return False

    heartbeat_interval = 5
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        # 1. Heartbeat
        current_time = time.time()
        if current_time - state.last_heartbeat >= heartbeat_interval:
            try:
                payload = {
                    "uptime_seconds": int(current_time - state.uptime_start),
                    "consecutive_errors": state.consecutive_errors,
                    "version": BRIDGE_VERSION,
                    "diagnostics_json": json.dumps({"status": "running"})
                }
                res = requests.post(f"{base_url}/api/bridge/heartbeat", json=payload, headers=headers, timeout=15)
                if res.status_code == 404:
                    res = requests.post(f"{base_url}/bridge/heartbeat", json=payload, headers=headers, timeout=15)
                    
                if res.status_code == 200:
                    state.last_heartbeat = current_time
                elif res.status_code in [401, 403]:
                    logger.error("Authentication expired or invalid. Exiting to re-authenticate.")
                    return "REAUTH"
                else:
                    logger.warning(f"Heartbeat failed with status: {res.status_code}")
            except Exception as e:
                logger.warning(f"Heartbeat network error: {e}")

        # 2. Fetch Tasks
        full_batch = False
        try:
            res = requests.get(f"{base_url}/api/bridge/tasks", headers=headers, timeout=15)
            if res.status_code == 404:
                res = requests.get(f"{base_url}/bridge/tasks", headers=headers, timeout=15)
                
            if res.status_code == 200:
                data = res.json()
                tasks = data.get("tasks", [])
                full_batch = len(tasks) >= 25
                if tasks:
                    logger.info(f"Received {len(tasks)} tasks to send.")
                    results = []
                    for task in tasks:
                        logger.info(f"Sending to {task.get('to_email')}...")
                        success, error = send_email_via_outlook(task, outlook)
                        
                        if not success:
                            state.consecutive_errors += 1
                            logger.error(f"Failed to send email via Outlook: {error}")
                            # If we hit RPC errors or server unavailable, the COM object is dead
                            if "RPC server is unavailable" in error or "disconnected" in error.lower() or state.consecutive_errors >= 3:
                                logger.error("Detected critical COM failure or too many consecutive errors. Restarting COM bridge...")
                                return "RESTART_COM"
                        else:
                            state.consecutive_errors = 0
                            
                        res_obj = {
                            "log_id": task["log_id"],
                            "success": success
                        }
                        if error is not None:
                            res_obj["error"] = error
                        results.append(res_obj)

                        if len(results) >= 5:
                            post_results(base_url, token, results)
                            results = []

                        time.sleep(0.25)

                    if results:
                        post_results(base_url, token, results)
            elif res.status_code in [401, 403]:
                logger.error("Authentication expired or invalid. Exiting to re-authenticate.")
                return "REAUTH"
            else:
                logger.warning(f"Failed to fetch tasks: HTTP {res.status_code}")
        except Exception as e:
            logger.warning(f"Network error fetching tasks: {e}")

        if not full_batch:
            time.sleep(2)

def main():
    parser = argparse.ArgumentParser(description="TalentOps AI - Local Outlook Bridge")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="The backend API URL")
    parser.add_argument("--email", required=False, help="User email to authenticate")
    parser.add_argument("--password", required=False, help="User password to authenticate")
    args = parser.parse_args()

    base_url = args.api_url.rstrip("/")
    logger.info(f"Starting Local Outlook Bridge v{BRIDGE_VERSION} against {base_url}")

    state = BridgeState()

    # Supervisor Loop
    while True:
        try:
            if not state.auth_token:
                if args.email and args.password:
                    state.auth_token = get_auth_token(base_url, args.email, args.password)
                else:
                    state.auth_token = get_auth_token_bypass(base_url)
                    
                if not state.auth_token:
                    logger.error("Could not obtain auth token. Retrying in 10 seconds...")
                    time.sleep(10)
                    continue

            logger.info("Initializing Bridge Runner...")
            status = run_inner_loop(base_url, state.auth_token, state)

            if status == "REAUTH":
                state.auth_token = None
                time.sleep(2)
            elif status == "RESTART_COM":
                logger.info("Cooling down for 5 seconds before COM restart...")
                time.sleep(5)
            else:
                # E.g. COM dispatch failed on startup
                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Shutting down Local Outlook Bridge gracefully.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Supervisor caught unexpected error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
