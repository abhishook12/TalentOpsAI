from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
import json
import pandas as pd
import io
import math
from datetime import datetime

from app.database import get_db
from app.models.models import SmartImportJob, SmartImportRow, Recruiter, ActionLog
from app.services.import_service import detect_smart_columns, validate_and_save_rows, process_commit, generate_excel_from_rows
from app.services.format_detector import detect_format
from app.services.job_tracker import serialize_smart_job

router = APIRouter(prefix="/import", tags=["import"])

@router.post("/parse")
async def parse_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    try:
        contents = await file.read()
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(io.BytesIO(contents), dtype=str, keep_default_na=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="File is empty")
        
    # Trim to 100k rows max to prevent OOM
    if len(df) > 100000:
        df = df.head(100000)

    # 1. Smart Mapping
    headers = list(df.columns)
    sample_data = df.head(5).to_dict(orient="records")
    mapping_suggestions = detect_smart_columns(headers, sample_data)
    
    # 2. Format Detection
    format_info = detect_format(df)
    
    # Create Job
    job_id = str(uuid.uuid4())
    job = SmartImportJob(
        job_id=job_id,
        filename=file.filename,
        status="mapping",
        current_step="Analyzing file structure",
        progress_percent=12,
        file_size_bytes=len(contents),
        total_rows=len(df),
        processed_rows=0,
        user_email=request.headers.get("X-User-Email", "System"),
        detected_format=format_info["detected_format"],
        format_confidence=format_info["confidence"]
    )
    db.add(job)
    
    # Store Raw Rows directly for validation step later
    # We serialize the dataframe to JSON rows
    records = df.to_dict(orient="records")
    db_rows = []
    for i, r in enumerate(records):
        db_rows.append({
            "job_id": job_id,
            "original_row_index": i,
            "raw_json": json.dumps(r, default=str),
            "status": "Raw"
        })
    
    db.bulk_insert_mappings(SmartImportRow, db_rows)
    db.commit()
    
    return {
        "job_id": job_id,
        "total_rows": len(df),
        "headers": headers,
        "mapping_suggestions": mapping_suggestions,
        "sample_data": sample_data,
        "detected_format": format_info["detected_format"],
        "format_confidence": format_info["confidence"]
    }

@router.post("/validate/{job_id}")
async def validate_mapping(job_id: str, payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    
    column_mapping = payload.get("mapping", {})
    override_format = payload.get("format")
    
    job.column_mapping = json.dumps(column_mapping)
    if override_format:
        job.detected_format = override_format
    job.status = "validating"
    job.current_step = "Validating rows"
    job.progress_percent = 35
    db.commit()
    
    # Background Validation
    background_tasks.add_task(validate_and_save_rows, job_id, column_mapping)
    
    return {"message": "Validation started", "job_id": job_id}

@router.get("/preview/{job_id}")
def get_preview(job_id: str, page: int = 1, limit: int = 50, filter_status: str = None, db: Session = Depends(get_db)):
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    
    q = db.query(SmartImportRow).filter(SmartImportRow.job_id == job_id)
    if filter_status:
        q = q.filter(SmartImportRow.status == filter_status)
        
    total = q.count()
    rows = q.order_by(SmartImportRow.original_row_index).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "job": serialize_smart_job(job),
        "rows": [{
            "row_id": r.row_id,
            "index": r.original_row_index,
            "name": r.recruiter_name,
            "email": r.email,
            "phone": r.phone,
            "company": r.company_name,
            "state": r.state,
            "location": r.location,
            "status": r.status,
            "issues": json.loads(r.validation_issues) if r.validation_issues else []
        } for r in rows],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": math.ceil(total / limit) if limit else 1
        }
    }

@router.post("/commit/{job_id}")
async def commit_import(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = "importing"
    job.current_step = "Importing validated rows"
    job.progress_percent = max(job.progress_percent or 0, 80)
    db.commit()
    
    # Background Commit
    background_tasks.add_task(process_commit, job_id)
    return {"message": "Commit started", "job_id": job_id}

@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    jobs = db.query(SmartImportJob).order_by(desc(SmartImportJob.started_at)).limit(50).all()
    return [serialize_smart_job(j) for j in jobs]


@router.get("/jobs/active")
def get_active_jobs(db: Session = Depends(get_db)):
    jobs = (
        db.query(SmartImportJob)
        .filter(SmartImportJob.status.in_(["mapping", "validating", "preview_ready", "importing"]))
        .order_by(SmartImportJob.started_at.desc())
        .limit(5)
        .all()
    )
    return [serialize_smart_job(j) for j in jobs]


@router.get("/jobs/{job_id}/status")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_smart_job(job)

@router.get("/{job_id}/rejected")
def download_rejected(job_id: str, db: Session = Depends(get_db)):
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    
    rows = db.query(SmartImportRow).filter(
        SmartImportRow.job_id == job_id,
        SmartImportRow.status.in_(["Error", "Duplicate", "Failed"])
    ).all()
    
    file_bytes = generate_excel_from_rows(rows)
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=rejected_rows_{job_id}.xlsx"}
    )
