import time
import requests
import win32com.client
import pythoncom
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("OutlookBridge")

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

def main():
    parser = argparse.ArgumentParser(description="TalentOps AI - Local Outlook Bridge")
    parser.add_argument("--api-url", default="https://talentops-api-0qtm.onrender.com", help="The backend API URL")
    args = parser.parse_args()

    base_url = args.api_url.rstrip("/")
    logger.info(f"Starting Local Outlook Bridge against {base_url}")

    # Initialize COM for the main thread
    pythoncom.CoInitialize()

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        logger.info("Successfully connected to local Outlook application.")
    except Exception as e:
        logger.error(f"Failed to connect to Outlook: {e}")
        logger.error("Please ensure Microsoft Outlook is installed and configured on this machine.")
        return

    last_heartbeat = 0
    heartbeat_interval = 5

    while True:
        try:
            # 1. Heartbeat
            current_time = time.time()
            if current_time - last_heartbeat >= heartbeat_interval:
                try:
                    res = requests.post(f"{base_url}/api/bridge/heartbeat", timeout=15)
                    if res.status_code == 200:
                        last_heartbeat = current_time
                    else:
                        logger.warning(f"Heartbeat failed with status: {res.status_code}")
                except Exception as e:
                    logger.warning(f"Heartbeat network error: {e}")

            # 2. Fetch Tasks
            try:
                res = requests.get(f"{base_url}/api/bridge/tasks", timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    tasks = data.get("tasks", [])
                    if tasks:
                        logger.info(f"Received {len(tasks)} tasks to send.")
                        results = []
                        for task in tasks:
                            logger.info(f"Sending to {task.get('to_email')}...")
                            success, error = send_email_via_outlook(task, outlook)
                            res_obj = {
                                "log_id": task["log_id"],
                                "success": success
                            }
                            if error is not None:
                                res_obj["error"] = error
                            results.append(res_obj)
                            # Small delay between emails
                            time.sleep(1.5)
                        
                        # 3. Post Results
                        try:
                            post_res = requests.post(f"{base_url}/api/bridge/results", json={"results": results}, timeout=15)
                            if post_res.status_code == 200:
                                logger.info(f"Successfully reported results for {len(tasks)} tasks.")
                            else:
                                logger.error(f"Failed to report results: HTTP {post_res.status_code} - {post_res.text}")
                        except Exception as e:
                            logger.error(f"Network error reporting results: {e}")
                else:
                    logger.warning(f"Failed to fetch tasks: HTTP {res.status_code}")
            except Exception as e:
                logger.warning(f"Network error fetching tasks: {e}")

            # Sleep before next poll
            time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Shutting down Local Outlook Bridge.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
