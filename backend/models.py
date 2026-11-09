from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PatientRecordSchema(BaseModel):
    local_id: str = Field(..., description="Unique client-generated UUID for offline deduplication")
    chw_id: str = Field(..., min_length=1, description="Community Health Worker identifier")
    patient_name: str = Field(..., min_length=2, description="Full name of patient")
    village_name: str = Field(..., min_length=1, description="Village or community name")
    visit_type: str = Field(..., description="Category of visit: Maternal, Child, General")
    vitals_bp: Optional[str] = Field(None, description="Blood pressure measurement in SYS/DIA format")
    vitals_temp: Optional[float] = Field(None, ge=35.0, le=43.0, description="Temperature in degrees Celsius")
    urgency_level: str = Field(..., description="Triage status: Routine, Urgent, Emergency")
    visit_notes: Optional[str] = Field(None, description="Clinical notes or recommendations")
    created_at_local: str = Field(..., description="ISO 8601 timestamp recorded on the client device")
    sync_status: Optional[str] = Field("Pending", description="Sync status on the client")

class PatientRecordResponse(BaseModel):
    local_id: str
    chw_id: str
    patient_name: str
    village_name: str
    visit_type: str
    vitals_bp: Optional[str] = None
    vitals_temp: Optional[float] = None
    urgency_level: str
    visit_notes: Optional[str] = None
    created_at_local: str
    synced_at: str
    sync_status: str

class BatchSyncRequest(BaseModel):
    records: List[PatientRecordSchema]

class BatchSyncResponse(BaseModel):
    success: bool
    synced_count: int
    message: str

class StatsResponse(BaseModel):
    total_records: int
    by_urgency: Dict[str, int]
    by_visit_type: Dict[str, int]
    top_villages: Dict[str, int]
