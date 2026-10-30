"""
app.py — NeuroNest IVN Analyzer FastAPI Backend

Endpoints:
  POST /api/upload_report      Upload a PDF → extract + AI analyze in background
  GET  /api/reports             List all processed reports
  GET  /api/reports/{report_id} Fetch full report with AI insights
  GET  /api/health              Health check
"""

import os
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import shutil
from contextlib import asynccontextmanager

from PDF_extraction import IVNReportParser
from database import insert_report, get_report, get_all_reports
from ai_analyzer import analyze_full_report
from chatbot import ask_ivn_copilot
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("  NeuroNest IVN Backend Starting...")
    print("=" * 50)
    # Milvus setup can be enabled here when the server is running:
    # from database import setup_milvus
    # setup_milvus()
    yield
    print("NeuroNest IVN Backend shutting down.")


app = FastAPI(
    title="NeuroNest IVN Analyzer",
    description="Agentic AI-powered IVN Test Report Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Allow CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static report images (extracted waveforms, pie charts)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Background Processing Pipeline
# ---------------------------------------------------------------------------

# Global dictionary to track task status
processing_status = {}

def process_report_task(file_path: str, task_id: str):
    """
    Background task: PDF → Extract → AI Analyze → Store in MongoDB.
    """
    processing_status[task_id] = {"status": "extracting", "message": "Extracting text and waveforms from PDF..."}
    print(f"\n[Pipeline] Starting processing: {file_path}")

    # Phase 1: Extract
    print("[Pipeline] Phase 1: PDF Extraction...")
    parser = IVNReportParser(file_path, output_dir="static/reports")
    report_data = parser.parse_report()

    tc_count = len(report_data.get("test_cases", []))
    print(f"[Pipeline] Extracted {tc_count} test cases.")

    # Phase 3: AI Analysis
    processing_status[task_id] = {"status": "analyzing", "message": f"AI analyzing {tc_count} test cases (90/10 filter)..."}
    print("[Pipeline] Phase 3: AI Analysis (90/10 filter)...")
    try:
        enriched_data = analyze_full_report(report_data)
    except Exception as e:
        print(f"[Pipeline] AI Analysis failed: {e}")
        enriched_data = report_data
        enriched_data["analysis_summary"] = {
            "total_test_cases": tc_count,
            "ai_analyzed": 0,
            "error": str(e),
        }

    # Phase 2: Store
    processing_status[task_id] = {"status": "saving", "message": "Saving insights to database..."}
    print("[Pipeline] Phase 2: Storing in MongoDB (or local fallback)...")
    try:
        report_id = insert_report(enriched_data)
        print(f"[Pipeline] Complete! Report {report_id} stored with AI insights.")
        processing_status[task_id] = {"status": "complete", "report_id": report_id, "message": "Analysis complete!"}
    except Exception as e:
        print(f"[Pipeline] Storage failed: {e}")
        processing_status[task_id] = {"status": "error", "message": f"Failed to save data: {e}"}


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def get_status():
    """Return the global processing status dict."""
    return processing_status


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "NeuroNest IVN Analyzer"}


@app.post("/api/upload_report")
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a PDF test report for processing.

    The file is saved and processing happens asynchronously in the background.
    Returns 202 Accepted immediately.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(
            {"error": "Only PDF files are accepted."},
            status_code=400,
        )

    os.makedirs("input_documents", exist_ok=True)
    file_path = os.path.join("input_documents", file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"[Upload] Received: {file.filename} ({file_size_mb:.1f} MB)")

    import uuid
    task_id = str(uuid.uuid4())
    processing_status[task_id] = {"status": "queued", "message": "Queued for processing..."}

    # Queue background task for scalable processing
    background_tasks.add_task(process_report_task, file_path, task_id)

    return JSONResponse(
        {
            "status": "Accepted",
            "message": f"Report '{file.filename}' is being processed.",
            "file": file.filename,
            "size_mb": round(file_size_mb, 2),
            "task_id": task_id
        },
        status_code=202,
    )


@app.get("/api/reports")
async def list_reports():
    """
    List all processed reports (metadata + analysis summary only).

    Returns a lightweight list for the frontend's report selector.
    """
    try:
        reports = get_all_reports()
        return {
            "total": len(reports),
            "reports": reports,
        }
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to fetch reports: {str(e)}"},
            status_code=500,
        )


@app.get("/api/reports/{report_id}")
async def get_report_endpoint(report_id: str):
    """
    Fetch a full report by its report number.

    Returns complete data: metadata, test cases, measurements, AI analysis.
    """
    data = get_report(report_id)
    if data:
        return data
    return JSONResponse({"error": "Report not found"}, status_code=404)


# ---------------------------------------------------------------------------
# Chatbot Copilot API
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    report_id: Optional[str] = None


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Interactive Automotive IVN AI Copilot Endpoint.
    Answers general automotive IVN queries, ISO standards questions,
    and report-specific failure root causes.
    """
    report_context = None
    if req.report_id:
        report_context = get_report(req.report_id)

    result = ask_ivn_copilot(
        message=req.message,
        history=req.history,
        report_context=report_context,
    )
    return result


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
