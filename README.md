# Community Health Worker (CHW) Offline Web Application

A lightweight, offline-first clinical records system for Community Health Workers operating in low-connectivity or remote environments.

---

## Architecture Overview

```
chw-offline-app/
├── backend/
│   ├── database.py       # SQLite connection, schema initialization, and queries
│   ├── main.py           # FastAPI application, REST endpoints, CORS, static hosting
│   ├── models.py         # Pydantic data validation schemas
│   ├── records.db        # SQLite database (auto-created on startup)
│   └── requirements.txt  # Python backend dependencies
└── frontend/
    ├── app.js            # Client UI logic, network detection, form handling & sync
    ├── db.js             # IndexedDB wrapper (local browser storage)
    ├── index.html        # Modern accessible UI & form inputs
    └── style.css         # Responsive healthcare styles & mobile-friendly design
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Run the Backend Server
From the project root:
```bash
python backend/main.py
```
Or with Uvicorn directly:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Access Points

- **Web App (Frontend)**: [http://localhost:8000](http://localhost:8000)
- **Interactive API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative API Documentation (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **API Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check endpoint |
| `POST` | `/api/records` | Idempotent upsert of a single patient visit record |
| `POST` | `/api/records/batch` | Bulk sync multiple offline records in one payload |
| `GET` | `/api/records` | List records (filterable by `chw_id`, `urgency_level`, `village_name`) |
| `GET` | `/api/records/{local_id}` | Retrieve a specific record by its client UUID |
| `GET` | `/api/stats` | Aggregated metrics for health coordinator dashboard |

---

## Offline Synchronization Flow

1. **Patient Encounter**: The health worker fills out the visit form. Even with no internet connection, the entry is saved instantly to the device's local **IndexedDB** database with status `"Pending"`.
2. **Offline Resilience**: The worker can record multiple visits throughout the day without internet access.
3. **Queue Sync**: When connectivity is restored, clicking **"Sync Queue"** sends pending records to `/api/records`. Once confirmed by the server, their status updates to `"Synced"` in IndexedDB.
