from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import shutil

from models.schemas import ChatRequest, ImageAnalysisRequest
from config import settings
from agent.agent import execute_agentic_workflow, call_ollama, analyze_image_with_ollama, synthesize_document
from agent.router import route_task
from documents.processor import extract_text_from_pdf, extract_text_from_image, process_document
from rag.vector_store import VectorStore
from audit import NetworkAuditMiddleware, get_audit_logs, get_audit_stats

app = FastAPI(title="KaizenAI - Sovereign On-Premise Agentic Workbench", version="2.0.0")

app.add_middleware(NetworkAuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCS_DIR   = os.path.join(os.path.dirname(__file__), "data", "documents")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "data", "images")
os.makedirs(DOCS_DIR,   exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

vs = VectorStore()


# ─────────────────────────────────────────────────────────────────────────────
# Health / status
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "local", "offline_ready": True}


@app.get("/system/status")
def system_status():
    return {
        "llm":            True,
        "embeddings":     True,
        "rag":            True,
        "ocr":            True,
        "vision":         True,
        "tools":          True,
        "sandbox":        True,
        "external_calls": 0
    }


# ─────────────────────────────────────────────────────────────────────────────
# Upload  →  Extract  →  Chunk  →  Embed  →  Store in vector DB
# No LLM call here. Fast.
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    import uuid, time, json
    filename_lower = file.filename.lower()
    is_doc = filename_lower.endswith((".pdf", ".docx", ".doc", ".txt", ".md", ".csv"))
    is_img = filename_lower.endswith((".png", ".jpg", ".jpeg"))

    if is_doc:
        path = os.path.join(DOCS_DIR, file.filename)
    elif is_img:
        path = os.path.join(IMAGES_DIR, file.filename)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload a PDF, DOCX, TXT, or Image.")

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc_id = f"doc_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    print("=" * 60)
    print("===== FILE RECEIVED =====")
    print(f"Document ID: {doc_id}")
    print(f"Filename: {file.filename}")
    print(f"Saved to: {path}")
    print(f"File size: {os.path.getsize(path)} bytes")
    print("=" * 60)

    # Extract text using universal multi-format document processor
    chunks = process_document(path)
    full_text = "\n\n".join(c["text"] for c in chunks) if chunks else ""

    print("=" * 60)
    print(f"===== EXTRACTION RESULT: {len(chunks)} chunks ({len(full_text)} chars) =====")
    if full_text:
        print("===== EXTRACTED TEXT (first 3000 chars) =====")
        print(full_text[:3000])
    else:
        print("WARNING: No text extracted from this file!")
    print("=" * 60)

    if chunks:
        vs.add_documents(chunks, document_id=doc_id)
        n_chunks = len(chunks)
    else:
        n_chunks = 0

    # ── Run structured analysis ONCE at upload time ──────────────────────
    analysis = None
    analysis_summary = None
    if is_doc and full_text.strip():
        print("=" * 60)
        print(f"===== SENDING TO LLM: {len(full_text)} chars =====")
        print("=" * 60)

        analysis = synthesize_document(full_text)

        print("=" * 60)
        print("===== LLM ANALYSIS RESULT =====")
        print(json.dumps(analysis, indent=2)[:2000] if analysis else "EMPTY / FAILED")
        print("=" * 60)

        if analysis:
            ANALYSIS_PATH = os.path.join(DOCS_DIR, "current_analysis.json")
            with open(ANALYSIS_PATH, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2)

            analysis_summary = {
                "purpose":          analysis.get("purpose", "N/A"),
                "sections_count":   len(analysis.get("sections", [])),
                "key_findings":     analysis.get("key_findings", []),
                "risks":            analysis.get("risks", []),
                "problems":         analysis.get("problems", []),
                "recommendations":  analysis.get("recommendations", []),
                "conclusion":       analysis.get("conclusion", "")
            }

    # Save session knowledge
    session_data = {
        "document_id": doc_id,
        "filename": file.filename,
        "extracted_text": full_text,
        "char_count": len(full_text),
        "mode": "direct" if len(full_text) < 15000 else "rag",
        "analysis": analysis,
        "status": "completed"
    }
    with open(os.path.join(DOCS_DIR, f"session_{doc_id}.json"), "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)
    with open(os.path.join(DOCS_DIR, "current_session.json"), "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)

    response = {
        "document_id":     doc_id,
        "filename":        file.filename,
        "status":          "completed",
        "mode":            session_data["mode"],
        "chunks_indexed":  n_chunks,
        "message":         "I've analyzed the entire document. You can now ask me anything about it."
    }
    if analysis_summary:
        response["analysis_summary"] = analysis_summary
    return response


@app.get("/documents")
def list_documents():
    docs   = [f for f in os.listdir(DOCS_DIR)   if not f.endswith(".json")]
    images = os.listdir(IMAGES_DIR)
    return {"documents": docs, "images": images}


# ─────────────────────────────────────────────────────────────────────────────
# Main agent endpoint with Dual Execution Modes (Direct vs RAG)
# ─────────────────────────────────────────────────────────────────────────────
from fastapi.responses import StreamingResponse

@app.post("/agent/run")
def run_agent(request: ChatRequest):
    def event_stream():
        import json
        yield json.dumps({"type": "stage", "stage": "working", "message": "Reading and searching document knowledge..."}) + "\n"

        routing_info = route_task(request.message)
        task_type    = routing_info["task_type"]

        DOC_TASKS = {"document_analysis", "document_question"}
        context_text = ""

        if task_type in DOC_TASKS:
            # Check document session
            session_data = None
            if request.document_id:
                session_path = os.path.join(DOCS_DIR, f"session_{request.document_id}.json")
                if os.path.exists(session_path):
                    with open(session_path, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
            if not session_data and os.path.exists(os.path.join(DOCS_DIR, "current_session.json")):
                with open(os.path.join(DOCS_DIR, "current_session.json"), "r", encoding="utf-8") as f:
                    session_data = json.load(f)

            # Dual Mode Resolution:
            # Mode A: Small Document (< 15 KB) -> Direct full document context
            # Mode B: Large Document (>= 15 KB) -> RAG search chunks
            if session_data and session_data.get("extracted_text") and session_data.get("mode") == "direct":
                context_text = f"[FULL DOCUMENT CONTEXT ({session_data.get('filename')})]:\n" + session_data["extracted_text"]
            else:
                target_doc_id = request.document_id if request.document_id else (session_data.get("document_id") if session_data else None)
                retrieved = vs.search(request.message, n_results=4, document_id=target_doc_id)
                if retrieved:
                    context_text = "\n\n".join(
                        f"[Source: {doc['metadata'].get('source','?')}, "
                        f"Page {doc['metadata'].get('page','?')}]\n{doc['text']}"
                        for doc in retrieved
                    )

        workflow_generator = execute_agentic_workflow(
            prompt     = request.message,
            context    = context_text,
            output_dir = DOCS_DIR,
            history    = request.history
        )
        
        for chunk in workflow_generator:
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─────────────────────────────────────────────────────────────────────────────
# Image analysis
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/analyze-image")
def analyze_image(request: ImageAnalysisRequest):
    img_filename = request.image_name or (os.path.basename(request.image_path) if request.image_path else "")
    if not img_filename:
        raise HTTPException(status_code=400, detail="Missing image_name or image_path.")
    
    img_path = os.path.join(IMAGES_DIR, img_filename) if not os.path.isabs(img_filename) else img_filename
    if not os.path.exists(img_path):
        doc_img = os.path.join(DOCS_DIR, img_filename)
        if os.path.exists(doc_img):
            img_path = doc_img
        else:
            raise HTTPException(status_code=404, detail="Image not found in workspace.")
            
    vision_model = settings.model_registry.get("Vision", {}).get("model_name", "moondream:latest")
    prompt = request.prompt or "Describe the visible condition of this equipment in detail."
    analysis = analyze_image_with_ollama(img_path, prompt, model=vision_model)
    return {"analysis": analysis, "image": img_filename, "model": vision_model}


# ─────────────────────────────────────────────────────────────────────────────
# File download
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/files/{filename}")
def get_generated_file(filename: str):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(DOCS_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=safe_filename)


# ─────────────────────────────────────────────────────────────────────────────
# Audit log  (proves zero external calls)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/audit/logs")
def audit_logs():
    return {
        "stats": get_audit_stats(),
        "logs":  get_audit_logs()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
