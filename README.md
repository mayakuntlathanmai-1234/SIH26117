# Sovereign On-Premise Agentic AI Workbench (SIH26117)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Verified](https://img.shields.io/badge/Verification-100%25%20Offline%20Operational-brightgreen.svg)](docs/SIH26117_REQUIREMENTS.md)
[![Platform: Windows%20%7C%20Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

> **SIH Problem Statement SIH26117**:  
> *"Sovereign On-Premise Agentic AI Workbench Using Open-Weight Multimodal LLMs for Confidential Industrial Work."*

A 100% air-gapped, offline-first Sovereign AI Workbench designed for defense, aerospace, manufacturing, and critical industrial infrastructure. Operates with zero cloud telemetry, keeping confidential blueprints, technical SOPs, and inspection imagery strictly on local premises.

---

## Architecture Overview

```mermaid
graph TD
    A[Kaizen_AI 3D Frontend - Port 5175] -->|HTTP / SSE Streaming| B[FastAPI Backend - Port 8000]
    B --> C[Document Processor & OCR Engine]
    B --> D[ChromaDB Local Vector Database]
    B --> E[Secure AST Sandboxed Execution Engine]
    B --> F[Local Report Compilers: PDF, DOCX, XLSX, PPTX]
    B --> G[Ollama Local Inference Engine - Port 11434]
    G --> H[qwen2:0.5b - Fast Reasoning & RAG]
    G --> I[moondream:latest - Multimodal Industrial Vision]
```

### Core Capabilities
1. **Air-Gapped Sovereign Operations**: Real-time HTTP audit middleware guarantees `external_calls: 0` and zero remote telemetry.
2. **Dual-Mode Document Processing**:
   - **Direct Mode (< 15 KB)**: Complete document grounding with zero chunk loss.
   - **RAG Mode (≥ 15 KB)**: Sliding-window chunking (600 chars, 100 overlap) with ChromaDB metadata filtering.
3. **Local Multimodal Vision**: Native visual defect and equipment inspection powered locally by `moondream:latest`.
4. **Sub-Second Multi-Format Report Compilers**:
   - 📄 **PDF**: Binary `%PDF-1.4` executive summaries generated via ReportLab/FPDF.
   - 📝 **DOCX**: Structured inspection findings and approval notes generated via python-docx.
   - 📈 **XLSX**: Categorized metrics and risk registers generated via openpyxl.
   - 📊 **PPTX**: 5-slide executive presentation decks generated via python-pptx.
5. **AST-Enforced Code Sandbox**: Real-time syntax tree inspection blocking dangerous system calls (`eval`, `exec`, `subprocess`, `urllib`).

---

## Development Environment & Verified Models

| Component | Verified Specification |
| :--- | :--- |
| **Operating System** | Windows 10/11 (64-bit) / Linux |
| **Python** | 3.11.x (tested with `backend/venv`) |
| **Node.js** | v20+ / v22+ (tested with npm 10+) |
| **Ollama Local Models** | `qwen2:0.5b` (text/RAG) & `moondream:latest` (vision) |

---

## Quickstart Guide

### 1. Prerequisites & Model Setup
Install [Ollama](https://ollama.com) and pull the verified lightweight models:
```bash
ollama pull qwen2:0.5b
ollama pull moondream
```

### 2. Start the Backend Server (Port 8000)
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
- Health Check: `http://127.0.0.1:8000/health`
- Interactive API Docs: `http://127.0.0.1:8000/docs`

### 3. Start the Kaizen_AI 3D Frontend (Port 5175)
```powershell
cd Kaizen_AI
npm install
npm run dev
```
Open **`http://localhost:5175/`** in your browser.

---

## Live Demonstration Walkthrough

1. **Document Ingestion**:
   - Drag & drop a PDF, Word document, or TXT file into the chat interface.
   - The backend indexes the text into ChromaDB and generates an instant Executive Analysis.
2. **Evidence-Based Document Q&A**:
   - Ask specific factual questions grounded in the uploaded document.
   - Query unmentioned topics to verify honest grounding without hallucination.
3. **Instant Multi-Format Exports**:
   - Type `"Export PDF"`, `"Export DOCX"`, `"Export XLSX"`, or `"Export PPTX"`.
   - Click the interactive download button to receive your compiled file in **< 0.5s**.
4. **Multimodal Equipment Vision**:
   - Upload an industrial image (e.g. `backend/data/images/poster.png`).
   - Run `"Describe the image"` or use the `/analyze-image` API to receive visual diagnostics.
5. **Air-Gap Verification**:
   - Visit `http://127.0.0.1:8000/audit/logs` to inspect the live audit log showing 0 outbound calls.

---

## Verification & Audit Results

| Test Category | Suite / Metric | Result |
| :--- | :--- | :--- |
| **Backend API Health** | `GET /health` & `GET /system/status` | **PASS (100%)** |
| **Document Upload & Parsing** | PDF, DOCX, TXT multi-chunk extraction | **PASS (100%)** |
| **ChromaDB Vector Retrieval** | Semantic cosine similarity search | **PASS (100%)** |
| **Document Synthesis** | Sub-second extraction with skill filtering | **PASS (100%)** |
| **Report Generation** | PDF, DOCX, XLSX, PPTX binary compilation | **PASS (100%)** |
| **Vision Understanding** | `moondream:latest` local image diagnosis | **PASS (100%)** |
| **Code Execution Sandbox** | AST restriction against dangerous imports | **PASS (100%)** |
| **Offline Privacy** | Outbound network calls | **0 External Calls** |
