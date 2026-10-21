"""
backend/app/routes/harness.py — Multi-Platform Automation Harness API Router
============================================================================

Exposes lightweight REST endpoints and a compact visual interface to manage
locally connected apps (Teams, Outlook, Vitel, TalentOps Web Site) and upcoming integrations.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import sys
import os

# Ensure workspace root is in sys.path
sys.path.insert(0, r"C:\TalentOpsAI")

from harness.hub import harness_hub

router = APIRouter(tags=["Platform Automation Harness"])


class CandidateFlowRequest(BaseModel):
    canonical_name: str = Field(..., description="Full candidate name")
    title: Optional[str] = "Professional"
    company_name: Optional[str] = "Organization"
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    targets: Optional[List[str]] = ["teams", "outlook", "vitel"]


class AppActionRequest(BaseModel):
    action: str = Field(..., description="Action name (e.g., bring_to_front, open_chat, create_email)")
    payload: Optional[Dict[str, Any]] = None


class RegisterUpcomingRequest(BaseModel):
    key: str = Field(..., description="Unique key identifier, e.g. 'whatsapp'")
    name: str = Field(..., description="Display name, e.g. 'WhatsApp Business'")
    category: str = Field("Messaging", description="Category")
    description: Optional[str] = ""
    status: Optional[str] = "planned"


@router.get("/status")
def get_harness_status():
    """Returns the live status matrix of all connected local apps and upcoming integrations."""
    return harness_hub.get_status_matrix()


@router.post("/dispatch")
def dispatch_candidate_flow(req: CandidateFlowRequest):
    """Triggers an end-to-end multi-platform outreach workflow across Teams, Outlook, and Vitel."""
    candidate_dict = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    result = harness_hub.dispatch_candidate_flow(candidate_dict, targets=req.targets)
    return result


@router.post("/app/{app_name}/action")
def execute_app_action(app_name: str, req: AppActionRequest):
    """Executes a targeted action on a specific connected platform."""
    connector = harness_hub.get_connector(app_name)
    if not connector:
        raise HTTPException(status_code=404, detail=f"No connector registered for '{app_name}'")
    
    result = connector.execute_action(req.action, req.payload)
    return result


@router.post("/upcoming/register")
def register_upcoming_app(req: RegisterUpcomingRequest):
    """Registers a new upcoming application on the harness roadmap."""
    metadata = {
        "name": req.name,
        "category": req.category,
        "status": req.status,
        "description": req.description,
    }
    harness_hub.register_upcoming_app(req.key, metadata)
    return {"success": True, "registered": req.key, "metadata": metadata}


@router.get("/ui", response_class=HTMLResponse)
def get_harness_mini_ui():
    """
    Renders a compact, sleek, self-contained mini-dashboard for controlling
    all connected platforms, viewing live process telemetry, and triggering workflows.
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TalentOps Harness Controller</title>
    <style>
        :root {
            --bg: #0b0f19;
            --surface: #131b2e;
            --surface-hover: #1b2640;
            --border: #233150;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.25);
            --green: #10b981;
            --green-glow: rgba(16, 185, 129, 0.2);
            --amber: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: var(--bg); color: var(--text-main); padding: 24px; display: flex; justify-content: center; }
        .harness-card { width: 100%; max-width: 840px; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); overflow: hidden; }
        .harness-header { padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); }
        .title-group { display: flex; align-items: center; gap: 12px; }
        .logo-pill { background: var(--accent); color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 11px; letter-spacing: 0.5px; }
        .title-group h1 { font-size: 17px; font-weight: 600; }
        .status-badge { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--green); font-weight: 500; }
        .pulse-dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%; box-shadow: 0 0 10px var(--green); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
        
        .grid-container { padding: 20px 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }
        .app-box { background: rgba(0,0,0,0.25); border: 1px solid var(--border); border-radius: 10px; padding: 14px; transition: all 0.2s; position: relative; }
        .app-box:hover { border-color: var(--accent); transform: translateY(-2px); }
        .app-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
        .app-icon { font-size: 22px; }
        .pill-active { background: var(--green-glow); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.4); font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 12px; }
        .pill-planned { background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 12px; }
        .app-title { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
        .app-desc { font-size: 11px; color: var(--text-muted); line-height: 1.4; margin-bottom: 10px; }
        .app-btn { width: 100%; background: var(--surface-hover); border: 1px solid var(--border); color: var(--text-main); padding: 6px 10px; border-radius: 6px; font-size: 11px; cursor: pointer; font-weight: 500; transition: background 0.15s; }
        .app-btn:hover { background: var(--accent); color: white; border-color: var(--accent); }

        .workflow-section { padding: 0 24px 24px; }
        .section-title { font-size: 13px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
        .flow-box { background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
        .flow-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 14px; }
        .btn-dispatch { background: #2563eb; color: white; border: none; padding: 9px 18px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; transition: background 0.2s; box-shadow: 0 4px 12px var(--accent-glow); }
        .btn-dispatch:hover { background: #1d4ed8; }
        .results-pre { margin-top: 12px; background: #080c14; border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: monospace; font-size: 11px; color: #a5b4fc; max-height: 140px; overflow-y: auto; display: none; }
    </style>
</head>
<body>
    <div class="harness-card">
        <div class="harness-header">
            <div class="title-group">
                <span class="logo-pill">HARNESS</span>
                <h1>TalentOps Unified Platform Controller</h1>
            </div>
            <div class="status-badge">
                <span class="pulse-dot"></span>
                <span>Active & Synced</span>
            </div>
        </div>

        <div class="grid-container" id="appGrid">
            <!-- Dynamically populated -->
        </div>

        <div class="workflow-section">
            <div class="section-title">One-Click Multi-App Flow Dispatcher</div>
            <div class="flow-box">
                <div class="flow-desc">Executes correlated candidate outreach simultaneously across <b>Web Site</b> &rarr; <b>Teams Card</b> &rarr; <b>Outlook Draft</b> &rarr; <b>Vitel SMS</b>.</div>
                <button class="btn-dispatch" onclick="triggerFlow()">⚡ Test Candidate Outreach Flow</button>
                <pre class="results-pre" id="flowResult"></pre>
            </div>
        </div>
    </div>

    <script>
        async function loadStatus() {
            try {
                const res = await fetch('/harness/status');
                const data = await res.json();
                renderApps(data);
            } catch (e) {
                console.error(e);
            }
        }

        function renderApps(data) {
            const grid = document.getElementById('appGrid');
            grid.innerHTML = '';
            
            const icons = {
                teams: '💬',
                outlook: '✉️',
                vitel: '📞',
                site: '🌐',
                whatsapp: '📱',
                ringcentral: '☎️',
                slack: '👥'
            };

            // Connected Apps
            for (const [key, app] of Object.entries(data.apps)) {
                const isRunning = app.is_running;
                const box = document.createElement('div');
                box.className = 'app-box';
                box.innerHTML = `
                    <div class="app-top">
                        <span class="app-icon">${icons[key] || '📦'}</span>
                        <span class="${isRunning ? 'pill-active' : 'pill-planned'}">${isRunning ? 'CONNECTED' : 'STANDBY'}</span>
                    </div>
                    <div class="app-title">${app.display_name}</div>
                    <div class="app-desc">${app.active_account ? 'User: ' + app.active_account : (app.version_type || 'Local Service')}</div>
                    <button class="app-btn" onclick="focusApp('${key}')">Focus Window</button>
                `;
                grid.appendChild(box);
            }

            // Upcoming Apps
            for (const [key, app] of Object.entries(data.upcoming)) {
                const box = document.createElement('div');
                box.className = 'app-box';
                box.style.opacity = '0.75';
                box.innerHTML = `
                    <div class="app-top">
                        <span class="app-icon">${icons[key] || '🔌'}</span>
                        <span class="pill-planned">UPCOMING</span>
                    </div>
                    <div class="app-title">${app.name}</div>
                    <div class="app-desc">${app.description || app.category}</div>
                    <button class="app-btn" style="cursor:not-allowed;" disabled>Plugin Ready</button>
                `;
                grid.appendChild(box);
            }
        }

        async function focusApp(appName) {
            await fetch('/harness/app/' + appName + '/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'bring_to_front'})
            });
        }

        async function triggerFlow() {
            const resPre = document.getElementById('flowResult');
            resPre.style.display = 'block';
            resPre.innerText = 'Dispatching correlated workflow across all platforms...';

            const testCandidate = {
                canonical_name: 'Alex Johnson',
                title: 'Principal Software Architect',
                company_name: 'Microsoft',
                email: 'alex.johnson@microsoft.com',
                phone: '+14155552671',
                targets: ['teams', 'outlook', 'vitel']
            };

            const res = await fetch('/harness/dispatch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(testCandidate)
            });
            const data = await res.json();
            resPre.innerText = JSON.stringify(data, null, 2);
        }

        loadStatus();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
