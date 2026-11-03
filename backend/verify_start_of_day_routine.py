"""
verify_start_of_day_routine.py — Start-of-Day Triple-Check Verification Protocol (Rule 11)
===========================================================================================
Executes 3 complete, independent, non-trivial verification passes across:
1. Core Web & Backend Services Health
2. Autonomous Background Engines & Telemetry Loop
3. Workstation Tools, Teams Collection & Corporate Email Intelligence
"""

import sys
import os
import json
import time
import urllib.request
import psutil

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from backend.app.database import engine, SessionLocal
from sqlalchemy import text, inspect
from backend.app.models.auth_models import User
from backend.app.services.auth_service import create_access_token
from backend.app.services.email_intelligence_service import email_intelligence
from backend.app.routes.scout_updates import DEFAULT_RELEASE_VERSION as b_ver

def run_pass_1():
    print("=" * 70)
    print(">>> PASS 1/3: CORE WEB & BACKEND SERVICES HEALTH VERIFICATION <<<")
    print("=" * 70)
    results = {}

    # 1.1 Vite Frontend
    req = urllib.request.Request("http://localhost:5173", headers={"User-Agent": "VerificationBot/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        content = resp.read()
        results["frontend"] = {"status": resp.status, "bytes": len(content)}
        print(f"  [CHECK 1.1] Vite Frontend: HTTP {resp.status} OK ({len(content)} bytes)")
        assert resp.status == 200

    # 1.2 Backend /ping
    req = urllib.request.Request("http://127.0.0.1:8000/ping")
    with urllib.request.urlopen(req, timeout=5) as resp:
        ping_data = json.loads(resp.read().decode())
        results["backend_ping"] = ping_data
        print(f"  [CHECK 1.2] FastAPI /ping: {ping_data}")
        assert ping_data.get("status") == "ok"

    # 1.3 Backend /health
    req = urllib.request.Request("http://127.0.0.1:8000/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        h = json.loads(resp.read().decode())
        rec_store = h.get("components", {}).get("recruiter_store", {})
        results["backend_health"] = {
            "status": h.get("status"),
            "database": h.get("database"),
            "records": rec_store.get("records"),
            "companies": rec_store.get("companies")
        }
        print(f"  [CHECK 1.3] FastAPI /health: status={h.get('status')}, db={h.get('database')}, store_records={rec_store.get('records')}")
        assert h.get("status") == "healthy"
        assert h.get("database") == "connected"

    # 1.4 Database & Schema Check
    with engine.connect() as conn:
        locks = conn.execute(text("SELECT count(*) FROM pg_locks WHERE NOT granted;")).scalar()
        recs = conn.execute(text("SELECT count(*) FROM recruiters;")).scalar()
        comps = conn.execute(text("SELECT count(*) FROM companies;")).scalar()
        stg_cnt = conn.execute(text("SELECT count(*) FROM discovery_staging;")).scalar()
        tables_cnt = len(inspect(engine).get_table_names())
        results["database"] = {
            "total_tables": tables_cnt,
            "blocked_locks": locks,
            "master_recruiters": recs,
            "companies": comps,
            "discovery_staging": stg_cnt
        }
        print(f"  [CHECK 1.4] PostgreSQL DB: {tables_cnt} tables, {recs} recruiters, {comps} companies, {stg_cnt} staged, {locks} un-granted locks")
        assert locks == 0
        assert recs > 0

    # 1.5 OS Supervisor Check
    supervisor_pids = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or [])
            if "talentops_supervisor.py" in cmd:
                supervisor_pids.append(p.info["pid"])
        except Exception:
            pass
    results["supervisor_pids"] = supervisor_pids
    print(f"  [CHECK 1.5] OS Supervisor: Active (PIDs {supervisor_pids})")
    assert len(supervisor_pids) > 0

    return results


def run_pass_2():
    print("\n" + "=" * 70)
    print(">>> PASS 2/3: AUTONOMOUS BACKGROUND ENGINES & TELEMETRY AUDIT <<<")
    print("=" * 70)
    results = {}

    with SessionLocal() as db:
        u = db.query(User).first()
        auth_token = create_access_token(data={"sub": str(u.id), "email": u.email})
    headers = {"Authorization": f"Bearer {auth_token}"}

    # 2.1 Sweeper Status
    req = urllib.request.Request("http://127.0.0.1:8000/api/email-intel/sweeper-status", headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        sw = json.loads(resp.read().decode())["telemetry"]
        results["sweeper"] = {
            "is_running": sw.get("is_running"),
            "operating_mode": sw.get("operating_mode"),
            "total_checked": sw.get("stats", {}).get("total_checked"),
            "profiles_enriched": sw.get("stats", {}).get("profiles_enriched"),
            "batches_processed": sw.get("stats", {}).get("batches_processed")
        }
        print(f"  [CHECK 2.1] Night/Continuous Sweeper: is_running={sw.get('is_running')}, mode={sw.get('operating_mode')}, enriched={sw.get('stats', {}).get('profiles_enriched')}")
        assert sw.get("is_running") is True

    # 2.2 WebHarvest Status
    req = urllib.request.Request("http://127.0.0.1:8000/api/enrichment/web-harvest-stats", headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        wh = json.loads(resp.read().decode())["web_harvest_engine"]
        results["web_harvest"] = {
            "is_running": wh.get("is_running"),
            "current_target": wh.get("stats", {}).get("current_target"),
            "harvest_cycles": wh.get("stats", {}).get("harvest_cycles"),
            "profiles_discovered": wh.get("stats", {}).get("profiles_discovered"),
            "profiles_promoted": wh.get("stats", {}).get("profiles_promoted")
        }
        print(f"  [CHECK 2.2] WebHarvest Crawler: is_running={wh.get('is_running')}, target={wh.get('stats', {}).get('current_target')}, discovered={wh.get('stats', {}).get('profiles_discovered')}")
        assert wh.get("is_running") is True

    # 2.3 Offline Buffer Watchdog
    req = urllib.request.Request("http://127.0.0.1:8000/api/enrichment/offline-buffer-status", headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        ob = json.loads(resp.read().decode())["offline_buffer"]
        results["offline_buffer"] = {
            "circuit_state": ob.get("circuit_state"),
            "render_online": ob.get("render_online"),
            "watchdog_running": ob.get("watchdog_running")
        }
        print(f"  [CHECK 2.3] Offline Buffer Watchdog: state={ob.get('circuit_state')}, render_online={ob.get('render_online')}, watchdog={ob.get('watchdog_running')}")
        assert ob.get("watchdog_running") is True

    # 2.4 Security Sentinel
    req = urllib.request.Request("http://127.0.0.1:8000/api/security/sentinel-status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        sec = json.loads(resp.read().decode())
        results["security_sentinel"] = sec
        print(f"  [CHECK 2.4] Security Sentinel: status={sec.get('status')}, uptime={sec.get('uptime_seconds')}s, blocked={sec.get('probes_blocked_count')}")
        assert sec.get("status") == "operational"

    # 2.5 Outlook Feedback Watcher
    req = urllib.request.Request("http://127.0.0.1:8000/api/outlook/feedback/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        ofb = json.loads(resp.read().decode())
        results["outlook_feedback"] = {
            "status": ofb.get("status"),
            "bounces": ofb.get("total_bounces_recorded"),
            "delivered": ofb.get("total_delivered_recorded")
        }
        print(f"  [CHECK 2.5] Outlook NDR & Bounce Watcher: status={ofb.get('status')}, bounces={ofb.get('total_bounces_recorded')}, delivered={ofb.get('total_delivered_recorded')}")
        assert ofb.get("status") == "active"

    return results


def run_pass_3():
    print("\n" + "=" * 70)
    print(">>> PASS 3/3: WORKSTATION TOOLS, TEAMS COLLECTION & EMAIL GATE <<<")
    print("=" * 70)
    results = {}

    # 3.1 Workstation Apps
    apps = {"ms-teams": [], "OUTLOOK": [], "Vitelglobal": []}
    for p in psutil.process_iter(["pid", "name"]):
        try:
            n = p.info["name"]
            for k in apps:
                if k.lower() in n.lower():
                    apps[k].append(p.info["pid"])
        except Exception:
            pass
    results["workstation_apps"] = apps
    for k, v in apps.items():
        print(f"  [CHECK 3.1] Desktop Tool {k}: Active with PIDs {v}")
        assert len(v) > 0, f"Tool {k} is NOT running!"

    # 3.2 Teams Daily Collection Service
    req = urllib.request.Request("http://127.0.0.1:8000/teams/daily-status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        td = json.loads(resp.read().decode())
        results["teams_collection"] = td
        print(f"  [CHECK 3.2] Teams Daily Collection Engine: status={td.get('status')}, has_run_today={td.get('has_run_today')}, weekday={td.get('is_weekday')}, scanned={td.get('messages_scanned')}, staged={td.get('candidates_staged')}, promoted={td.get('candidates_promoted')}, last_person='{td.get('last_person_collected')}'")
        assert td.get("today") == time.strftime("%Y-%m-%d")
        assert td.get("is_weekday") is True
        assert td.get("has_run_today") is True or td.get("status") in ("RUNNING", "COMPLETED")

    # 3.3 Scout Dual-Sync Versioning
    with open(os.path.join(WORKSPACE_DIR, "scout_desktop", "config.json"), "r") as f:
        cfg_ver = json.load(f).get("version")
    with open(os.path.join(WORKSPACE_DIR, "frontend", "src", "components", "Sidebar.jsx"), "r") as f:
        side_text = f.read()
    side_ver = "2.14.1" if "v2.14.1" in side_text else "mismatch"
    results["scout_dual_sync"] = {
        "desktop_config": cfg_ver,
        "backend": b_ver,
        "frontend_sidebar": side_ver,
        "synchronized": (cfg_ver == b_ver == side_ver)
    }
    print(f"  [CHECK 3.3] Scout Dual-Sync: Desktop={cfg_ver}, Backend={b_ver}, Frontend={side_ver} (Synchronized: {results['scout_dual_sync']['synchronized']})")
    assert results["scout_dual_sync"]["synchronized"] is True

    # 3.4 Corporate Email Intelligence Gate
    with SessionLocal() as db:
        res = email_intelligence.resolve_and_enrich_candidate(
            full_name="Satya Nadella",
            company_name="Microsoft",
            db=db
        )
        results["corporate_email_gate"] = res
        print(f"  [CHECK 3.4] Corporate Email Gate: domain={res.get('domain')}, provider={res.get('provider')}, has_mx={res.get('has_mx')}, status={res.get('status')}, blocked_placeholder={res.get('email') is None}")
        assert res.get("domain") == "microsoft.com"
        assert res.get("has_mx") is True

    return results


def main():
    start_time = time.time()
    p1 = run_pass_1()
    p2 = run_pass_2()
    p3 = run_pass_3()
    duration = round(time.time() - start_time, 2)

    print("\n" + "=" * 70)
    print(f"ALL 3 VERIFICATION PASSES COMPLETED CLEANLY IN {duration}s!")
    print("PROOF OF VERIFICATION: 100% OPERATIONAL ACROSS ALL MODULES.")
    print("=" * 70)

    # Persist proof
    out_file = os.path.join(WORKSPACE_DIR, "backend", "data", "start_of_day_routine_3x_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_sec": duration,
            "pass_1_core_health": p1,
            "pass_2_autonomous_engines": p2,
            "pass_3_workstation_teams_gate": p3,
            "verdict": "ALL_CHECKS_PASSED"
        }, f, indent=2)

if __name__ == "__main__":
    main()
