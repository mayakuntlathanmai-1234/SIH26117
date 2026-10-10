# Sovereign On-Premise Agentic AI Workbench

## SIH Problem Statement: SIH26117
**“Sovereign On-Premise Agentic AI Workbench Using Open-Weight Multimodal LLMs for Confidential Industrial Work.”**

## Problem
Organizations handling confidential industrial documents and imagery cannot rely on cloud-based AI due to data privacy, security risks, and the need for offline capability.

## Solution
This prototype is a 100% local, on-premise AI workbench. It leverages open-weight LLMs (Qwen), local embedding models, and local vector databases to securely analyze documents, generate insights, analyze industrial images, and output structured reports—all without internet access.

## Features
- **Local LLM Inference**: Powered by Qwen via Ollama.
- **Multimodal AI**: Image understanding capabilities using Qwen-VL.
- **Local RAG**: ChromaDB and local sentence-transformers for secure document retrieval.
- **Agentic Workflows**: A Python-based agent that orchestrates tools (search, read, calculate, image analysis).
- **Report Generation**: Automatically creates Word and Excel incident reports.
- **Offline Ready**: Operates completely disconnected from the internet once models and dependencies are installed.

## Architecture
- **Frontend**: React + Vite + Tailwind CSS (Enterprise UI)
- **Backend**: Python 3.11 + FastAPI
- **RAG**: PyPDF + SentenceTransformers + ChromaDB
- **LLM Engine**: Ollama (Qwen2.5 0.5b / LLaVA)

## Technology Stack
- **Languages**: Python, JavaScript
- **Frameworks**: FastAPI, React
- **Libraries**: ChromaDB, pypdf, python-docx, openpyxl, sentence-transformers, tailwindcss, lucide-react

## Setup & Installation

### Prerequisites
1. Python 3.11 or later
2. Node.js and npm
3. [Ollama](https://ollama.com) installed and running locally.

### Models Setup
Run the following commands to pull the necessary models into Ollama:
```bash
ollama pull qwen2.5:0.5b
ollama pull llava
```
*(Note: You can change the models in `backend/config.py` if you prefer larger variants like `qwen2.5:7b`.)*

### Running the Backend
1. Open a terminal in the `backend` directory.
2. Activate the virtual environment:
   ```cmd
   .\venv\Scripts\activate
   ```
3. Install dependencies (if not already done):
   ```cmd
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```cmd
   uvicorn main:app --reload
   ```

### Running the Frontend
1. Open a terminal in the `frontend` directory.
2. Install dependencies:
   ```cmd
   npm install
   ```
3. Start the Vite dev server:
   ```cmd
   npm run dev
   ```

## Demo Workflow
1. Start both servers and open the frontend in your browser.
2. You will see dummy files already in the system (`Maintenance_SOP.pdf`, `Equipment_Manual.pdf`, etc.).
3. You can ask a query like: *"Analyze the equipment failure using the incident report, maintenance SOP and equipment image."*
4. Click "Word Report" or "Excel Data" to generate reports.

## Offline Architecture
All models (LLM, embeddings) and data stores (ChromaDB) are hosted locally. There are no API calls made to OpenAI, Anthropic, or any external service. The UI will indicate "LOCAL MODE / OFFLINE READY".

*Disclaimer: This is a prototype built for the SIH26117 problem statement. The agentic loops and error boundaries are simplified for demonstration purposes.*
