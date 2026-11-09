from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import (
    init_db,
    save_or_update_record,
    get_records,
    get_record_by_id,
    get_stats
)
from models import (
    PatientRecordSchema,
    PatientRecordResponse,
    BatchSyncRequest,
    BatchSyncResponse,
    StatsResponse
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite database tables & indexes exist
    init_db()
    yield
    # Shutdown: clean up if needed

app = FastAPI(
    title="CHW Offline Records API",
    description="Backend synchronization and records management API for Community Health Workers",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local testing from any origin or port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify backend availability."""
    return {"status": "ok", "service": "CHW Offline Records API"}

@app.post(
    "/api/records",
    response_model=PatientRecordResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Records"]
)
def create_or_sync_record(record: PatientRecordSchema):
    """
    Save or sync a single patient record from a CHW device.
    Uses local_id for idempotent upserts.
    """
    try:
        saved = save_or_update_record(record.model_dump())
        return saved
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save record: {str(e)}"
        )

@app.post(
    "/api/records/batch",
    response_model=BatchSyncResponse,
    tags=["Sync"]
)
def batch_sync_records(batch: BatchSyncRequest):
    """
    Sync multiple offline patient records in a single payload.
    Ideal for when a CHW re-connects after an extended offline period.
    """
    synced_count = 0
    errors = []

    for item in batch.records:
        try:
            save_or_update_record(item.model_dump())
            synced_count += 1
        except Exception as e:
            errors.append(f"Record {item.local_id}: {str(e)}")

    return BatchSyncResponse(
        success=len(errors) == 0,
        synced_count=synced_count,
        message=f"Synced {synced_count} of {len(batch.records)} record(s)." + (f" Errors: {', '.join(errors)}" if errors else "")
    )

@app.get(
    "/api/records",
    response_model=List[PatientRecordResponse],
    tags=["Records"]
)
def list_records(
    chw_id: Optional[str] = Query(None, description="Filter by CHW ID"),
    urgency_level: Optional[str] = Query(None, description="Filter by urgency: Routine, Urgent, Emergency"),
    village_name: Optional[str] = Query(None, description="Filter by village name (partial match)"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """List stored records with optional filtering and pagination."""
    return get_records(
        chw_id=chw_id,
        urgency_level=urgency_level,
        village_name=village_name,
        limit=limit,
        offset=offset
    )

@app.get(
    "/api/records/{local_id}",
    response_model=PatientRecordResponse,
    tags=["Records"]
)
def get_record(local_id: str):
    """Retrieve a single patient record by its local_id."""
    record = get_record_by_id(local_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{local_id}' not found."
        )
    return record

@app.get(
    "/api/stats",
    response_model=StatsResponse,
    tags=["Analytics"]
)
def get_records_stats():
    """Summary analytics across visits, urgency levels, and villages."""
    return get_stats()

# Mount the frontend directory to serve the offline web app directly
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists() and (frontend_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    app_dir = str(Path(__file__).resolve().parent)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=app_dir)

