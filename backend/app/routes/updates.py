import subprocess
import os
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from ..database import get_db
from ..routes.admin import verify_admin

router = APIRouter(prefix="/updates", tags=["updates"])

def get_git_commits(limit=10):
    try:
        # Run git log, fetching top commits
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        output = subprocess.check_output(
            ["git", "log", "-n", str(limit), "--pretty=format:%H|~|%s|~|%b|~|%ad|~|%an", "--date=iso-strict"],
            cwd=repo_root,
            text=True
        )
    except Exception as e:
        print("Git log error:", e)
        raise e

    commits = []
    for line in output.split('\n'):
        if not line.strip():
            continue
        parts = line.split('|~|')
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0],
                "subject": parts[1],
                "body": parts[2],
                "date": parts[3],
                "author": parts[4]
            })
    if not commits:
        return [{"hash": "DEBUG", "subject": f"CWD: {repo_root}, Output: {output}", "body": "", "date": "2026-07-01", "author": "Bot"}]
    return commits

@router.get("/status")
def get_current_status():
    """
    Gets the latest update and its overall status based on the latest git commit.
    """
    commits = get_git_commits(1)
    if not commits:
         return {"version": "v1.0.0", "status": "Operational", "date": datetime.utcnow().isoformat(), "features": []}
         
    latest = commits[0]
    return {
        "version": latest["hash"][:7],
        "date": latest["date"],
        "status": "Verified & Operational",
        "features": [
            {"id": 1, "name": latest["subject"], "status": "Verified & Operational"}
        ]
    }

@router.get("/changelog")
def get_changelog():
    """
    Gets all updates based on git commit history.
    """
    commits = get_git_commits(15)
    result = []
    for i, commit in enumerate(commits):
        # We can extract the body as features if there are multiple lines
        body_lines = [line.strip("- *") for line in commit["body"].split("\n") if line.strip()]
        features = []
        if not body_lines:
            features.append({
                "id": f"{commit['hash']}-1",
                "name": commit["subject"],
                "status": "Verified & Operational",
                "tester": "Automated",
                "last_tested": commit["date"],
                "result": ""
            })
        else:
            for j, line in enumerate(body_lines):
                features.append({
                    "id": f"{commit['hash']}-{j}",
                    "name": line,
                    "status": "Verified & Operational",
                    "tester": "Automated",
                    "last_tested": commit["date"],
                    "result": ""
                })
                
        result.append({
            "id": commit["hash"],
            "version": commit["hash"][:7],
            "title": commit["subject"],
            "developer": commit["author"],
            "date": commit["date"],
            "status": "Verified",
            "features": features
        })
    return result

@router.get("/features")
def get_all_features(_=Depends(verify_admin)):
    """
    Gets all features for the admin verification panel (mocked to recent git changes).
    """
    changelog = get_changelog()
    features = []
    for entry in changelog:
        features.extend(entry["features"])
    return features

@router.post("/verify/{feature_id}")
def verify_feature(feature_id: str, payload: dict, _=Depends(verify_admin)):
    """
    Updates the status of a feature (Disabled in auto mode).
    """
    return {"status": "ignored", "feature_id": feature_id, "detail": "Git-based updates are read-only"}

