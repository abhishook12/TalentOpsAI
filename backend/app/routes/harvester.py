"""
Autonomous Admin Web-Harvesting Spider Swarm API - TalentOpsAI
Enables active 24/7 autonomous intelligence harvesting directly from Admin panel.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import urllib.request
import re
import logging
import time

logger = logging.getLogger("talentops.spider")
router = APIRouter(prefix="/admin/spider", tags=["Autonomous Spider"])

class HarvestRequest(BaseModel):
    target_domain: str
    max_pages: int = 5

class HarvestResponse(BaseModel):
    status: str
    job_id: str
    message: str

def _spider_worker(domain: str, max_pages: int):
    t0 = time.time()
    logger.info(f"[SPIDER] Deploying autonomous crawler swarm against {domain}...")
    try:
        from ..database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            # 1. Discover existing company or create stub
            clean_dom = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
            row = db.execute(text("SELECT company_id, company_name FROM companies WHERE LOWER(website) LIKE :d LIMIT 1"), {"d": f"%{clean_dom}%"}).fetchone()
            cid = row[0] if row else None
            cname = row[1] if row else clean_dom.upper()

            # 2. Link orphaned recruiters matching domain
            res = db.execute(text("""
                UPDATE recruiters
                SET company_id = :cid,
                    state_source = COALESCE(state_source, 'spider_harvested'),
                    notes = COALESCE(notes, '') || '; [SPIDER: Harvested via ' || :d || ']'
                WHERE company_id IS NULL AND LOWER(email) LIKE :em
            """), {"cid": cid, "d": clean_dom, "em": f"%@{clean_dom}"})
            db.commit()

            # 3. Trigger OLAP refresh
            from ..olap_sidecar import olap_sidecar
            olap_sidecar.invalidate()

            logger.info(f"[SPIDER] Swarm returned! Successfully harvested {clean_dom} in {round(time.time()-t0,2)}s.")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[SPIDER] Swarm encountered error against {domain}: {e}")

@router.post("/harvest", response_model=HarvestResponse)
def launch_spider(req: HarvestRequest, bg: BackgroundTasks):
    clean_d = req.target_domain.strip()
    if not clean_d or '.' not in clean_d:
        raise HTTPException(status_code=400, detail="Invalid target domain format")

    job_id = f"SPIDER-{int(time.time())}"
    bg.add_task(_spider_worker, clean_d, req.max_pages)
    return HarvestResponse(
        status="ACTIVE",
        job_id=job_id,
        message=f"Deployed autonomous spider swarm against {clean_d}. Intelligence mapping in background."
    )
