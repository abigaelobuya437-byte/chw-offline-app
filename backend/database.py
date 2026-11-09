import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).resolve().parent / "records.db"

def get_connection() -> sqlite3.Connection:
    """Create and return a thread-safe sqlite3 connection with dictionary row access."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initialize database tables and indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                local_id TEXT PRIMARY KEY,
                chw_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                village_name TEXT NOT NULL,
                visit_type TEXT NOT NULL,
                vitals_bp TEXT,
                vitals_temp REAL,
                urgency_level TEXT NOT NULL,
                visit_notes TEXT,
                created_at_local TEXT NOT NULL,
                synced_at TEXT NOT NULL,
                sync_status TEXT DEFAULT 'Synced'
            )
        """)
        # Indexes for fast querying and reporting
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_chw ON records (chw_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_urgency ON records (urgency_level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_created ON records (created_at_local)")
        conn.commit()

def save_or_update_record(record_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert or update a record using its local_id.
    This guarantees idempotency when offline queues sync multiple times.
    """
    synced_at = datetime.now(timezone.utc).isoformat()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO records (
                local_id, chw_id, patient_name, village_name, visit_type,
                vitals_bp, vitals_temp, urgency_level, visit_notes,
                created_at_local, synced_at, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Synced')
            ON CONFLICT(local_id) DO UPDATE SET
                chw_id = excluded.chw_id,
                patient_name = excluded.patient_name,
                village_name = excluded.village_name,
                visit_type = excluded.visit_type,
                vitals_bp = excluded.vitals_bp,
                vitals_temp = excluded.vitals_temp,
                urgency_level = excluded.urgency_level,
                visit_notes = excluded.visit_notes,
                created_at_local = excluded.created_at_local,
                synced_at = excluded.synced_at,
                sync_status = 'Synced'
        """, (
            record_data["local_id"],
            record_data["chw_id"],
            record_data["patient_name"],
            record_data["village_name"],
            record_data["visit_type"],
            record_data.get("vitals_bp"),
            record_data.get("vitals_temp"),
            record_data["urgency_level"],
            record_data.get("visit_notes"),
            record_data["created_at_local"],
            synced_at
        ))
        conn.commit()

        cursor.execute("SELECT * FROM records WHERE local_id = ?", (record_data["local_id"],))
        row = cursor.fetchone()
        return dict(row) if row else {}

def get_records(
    chw_id: Optional[str] = None,
    urgency_level: Optional[str] = None,
    village_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Fetch stored patient records with optional filters and pagination."""
    query = "SELECT * FROM records WHERE 1=1"
    params: List[Any] = []

    if chw_id:
        query += " AND chw_id = ?"
        params.append(chw_id)
    if urgency_level:
        query += " AND urgency_level = ?"
        params.append(urgency_level)
    if village_name:
        query += " AND village_name LIKE ?"
        params.append(f"%{village_name}%")

    query += " ORDER BY created_at_local DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_record_by_id(local_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single record by local_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE local_id = ?", (local_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_stats() -> Dict[str, Any]:
    """Aggregate statistics for CHW reporting dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) AS total FROM records")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT urgency_level, COUNT(*) AS count FROM records GROUP BY urgency_level")
        urgency_counts = {row["urgency_level"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT visit_type, COUNT(*) AS count FROM records GROUP BY visit_type")
        visit_type_counts = {row["visit_type"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT village_name, COUNT(*) AS count FROM records GROUP BY village_name ORDER BY count DESC LIMIT 5")
        top_villages = {row["village_name"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_records": total,
            "by_urgency": urgency_counts,
            "by_visit_type": visit_type_counts,
            "top_villages": top_villages
        }
