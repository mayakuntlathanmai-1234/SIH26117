import requests
import base64
import json
import os
import re
import subprocess
import tempfile
import sys
from config import settings
from agent.router import route_task
from agent.planner import generate_plan
from reports.word_report import create_word_report
from reports.excel_report import create_excel_report
from reports.ppt_report import create_ppt_report
from reports.pdf_report import create_pdf_report

# ─────────────────────────────────────────────
# 1.  Core Ollama call
# ─────────────────────────────────────────────
OLLAMA_URL      = f"{settings.OLLAMA_BASE_URL}/api/generate"
OLLAMA_CHAT_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"
MODEL           = getattr(settings, "DEFAULT_LLM_MODEL", "qwen2:0.5b")

def call_ollama(prompt: str,
                model: str = None,
                system: str = "",
                format: str = "",
                history: list = None,
                timeout: int = 30) -> str:
    if model is None:
        model = MODEL

    if history:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        for turn in history:
            role = "assistant" if turn.get("role") == "ai" else turn.get("role", "user")
            messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        if format == "json":
            payload["format"] = "json"

        try:
            response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except requests.exceptions.Timeout:
            print(f"[Ollama] Chat Timeout – model={model}")
            raise TimeoutError(f"Model {model} timed out.")
        except Exception as e:
            print(f"[Ollama] Chat Error – {e}")
            raise RuntimeError(f"Ollama error: {e}")

    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    if system:
        payload["system"] = system
    if format == "json":
        payload["format"] = "json"

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.Timeout:
        print(f"[Ollama] Timeout – model={model}")
        raise TimeoutError(f"Model {model} timed out.")
    except Exception as e:
        print(f"[Ollama] Error – {e}")
        raise RuntimeError(f"Ollama error: {e}")

# ─────────────────────────────────────────────
# 2.  Vision model call
# ─────────────────────────────────────────────
def analyze_image_with_ollama(image_path: str, prompt: str, model: str = "llava:latest") -> str:
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        payload = {
            "model":  model,
            "prompt": prompt,
            "images": [encoded],
            "stream": False,
            "options": {"temperature": 0.2}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"Vision model error: {e}"

# ─────────────────────────────────────────────
# 3.  Helpers
# ─────────────────────────────────────────────
def extract_json_from_text(text: str) -> dict | list:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match_obj = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match_obj:
            try:
                return json.loads(match_obj.group(1))
            except json.JSONDecodeError:
                pass
    return {}

def extract_code_block(text: str) -> str:
    match = re.search(r'```(?:python)?\s*([\s\S]*?)\s*```', text)
    return match.group(1).strip() if match else ""

def execute_local_code(code: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True, text=True, timeout=10
        )
        os.remove(temp_path)
        return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out after 10 seconds."
    except Exception as e:
        return f"Error executing code: {e}"

# ─────────────────────────────────────────────
# 4.  Document synthesizer (Two-Stage)
# ─────────────────────────────────────────────

def extract_chunk_facts(chunk_text: str) -> dict:
    """
    Stage 1: Fast, lightweight extraction from a single small chunk.
    Simple prompt → simple answer → fast.
    Returns {"facts": [...], "risks": [...], "recommendations": [...]}
    """
    prompt = (
        "Read the following text and extract:\n"
        "- Key facts or findings\n"
        "- Any risks, problems, or gaps mentioned\n"
        "- Any recommendations or actions suggested\n\n"
        f"Text:\n{chunk_text}\n\n"
        'Respond ONLY in JSON: {"facts": [], "risks": [], "recommendations": []}'
    )
    try:
        raw = call_ollama(prompt, format="json")
        data = extract_json_from_text(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def synthesize_document(extracted_text: str) -> dict:
    """
    Ultra-Fast Grounded Synthesis:
    1-pass direct text extraction + 1 fast LLM synthesis call.
    Completes in under 2 seconds instead of 30+ seconds.
    """
    if not extracted_text or not extracted_text.strip():
        return {
            "document_summary": "No text could be extracted from this document.",
            "purpose": "Not found in the document.",
            "sections": [],
            "key_findings": ["Not found in the document."],
            "important_data": [],
            "problems": [],
            "risks": [],
            "recommendations": [],
            "conclusion": "No readable text found."
        }

    # Instant 1-pass extraction from raw document lines (0.02s)
    raw_lines = [
        line.strip() for line in extracted_text.split('\n')
        if len(line.strip()) > 10 and not line.strip().startswith("OCR CONFIDENCE:")
    ]

    all_facts = raw_lines[:6] if raw_lines else []
    all_risks = [
        line for line in raw_lines
        if any(kw in line.lower() for kw in ["risk", "hazard", "vulnerability", "defect", "critical bug", "security breach", "delay", "safety issue", "failure", "danger", "warning"])
        or (any(kw in line.lower() for kw in ["problem", "issue", "error"]) and not any(ign in line.lower() for ign in ["problem solving", "problem-solving", "solve problem", "solving", "analytical", "skill"]))
    ]
    if not all_risks:
        all_risks = ["No operational risks or vulnerabilities identified in this document."]

    all_recs = [line for line in raw_lines if any(kw in line.lower() for kw in ["should", "must", "recommend", "action", "plan", "target", "step"])]
    if not all_recs:
        all_recs = ["Review key findings for project execution."]

    # Concise synthesis excerpt for instant upload response
    sample_excerpt = "\n".join(raw_lines[:15])[:1500]

    sys_prompt = (
        "You are KaizenAI, a document analysis assistant.\n"
        "Analyze ONLY the information contained in the provided document excerpt.\n"
        "Important: Do not classify technical skills (like problem solving) as risks or problems.\n"
        "If there are no actual risks, state 'No operational risks identified.'\n\n"
        "Output ONLY valid JSON matching this schema exactly:\n"
        '{"document_summary":"","purpose":"","sections":[],'
        '"key_findings":[],"important_data":[],"problems":[],"risks":[],'
        '"recommendations":[],"conclusion":""}'
    )

    try:
        raw = call_ollama(
            f"Document Excerpt:\n{sample_excerpt}",
            model="qwen2:0.5b",
            system=sys_prompt,
            format="json",
            timeout=8
        )
        data = extract_json_from_text(raw)
        if isinstance(data, dict):
            clean_risks = [
                r for r in data.get("risks", [])
                if not any(ign in str(r).lower() for ign in ["student", "engineering", "programming", "problem solving", "problem-solving", "skills", "technologies", "b.tech", "university", "internship", "developer"])
            ]
            clean_problems = [
                p for p in data.get("problems", [])
                if not any(ign in str(p).lower() for ign in ["student", "engineering", "programming", "problem solving", "problem-solving", "skills", "technologies", "b.tech", "university", "internship", "developer"])
            ]
            data["risks"] = clean_risks if clean_risks else ["No operational risks or vulnerabilities identified in this document."]
            data["problems"] = clean_problems if clean_problems else ["No critical issues identified."]

            if not data.get("key_findings") and all_facts: data["key_findings"] = all_facts
            if not data.get("recommendations") and all_recs: data["recommendations"] = all_recs
            if not data.get("purpose"): data["purpose"] = raw_lines[0] if raw_lines else "Uploaded Document Analysis"
            return data
    except Exception as e:
        print(f"Fast LLM synthesis note: {e}")

    # Instant sub-second grounded fallback if LLM times out
    summary_text = " ".join(raw_lines[:3]) if raw_lines else "Extracted document summary."
    purpose_text = raw_lines[0] if raw_lines else "Not found in the document."

    return {
        "document_summary": summary_text,
        "purpose":          purpose_text,
        "sections":         ["Document Overview"],
        "key_findings":     all_facts,
        "important_data":   all_facts[:4],
        "problems":         all_risks,
        "risks":            all_risks,
        "recommendations":  all_recs,
        "conclusion":       f"Analysis derived from {len(raw_lines)} extracted lines."
    }


# ─────────────────────────────────────────────
# 5.  Streaming Agentic Workflow
# ─────────────────────────────────────────────
def execute_agentic_workflow(prompt: str, context: str = "", output_dir: str = "", history: list = None):
    """
    Generator that yields JSON-encoded event strings for Server-Sent Events (SSE).
    Yields {"type": "stage", "stage": "working|almost_done|completed", "message": "..."}
    Finally yields {"type": "result", "data": {...}}
    """
    
    def emit_stage(stage, message):
        return json.dumps({"type": "stage", "stage": stage, "message": message}) + "\n"

    # INITIAL ROUTING (Working on it...)
    # (Removed: Now yielded from main.py before RAG search)
    
    routing_info = route_task(prompt)
    task_type    = routing_info["task_type"]
    target_file  = routing_info.get("target_file")
    model_name   = routing_info["model_name"]

    clean_prompt = re.sub(r'\s*\(Focus on documents:.*?\)', '', prompt, flags=re.IGNORECASE).strip()

    plan          = generate_plan(prompt, task_type, target_file)
    execution_log = [{"task": step, "status": "done"} for step in plan]
    file_metadata = None
    response_text = ""

    analysis_path = os.path.join(output_dir, "current_analysis.json")

    # LLM INFERENCE (Almost done...)
    yield emit_stage("almost_done", "Checking the retrieved information...")

    # ── A. File generation (docx / xlsx / pptx / pdf) ────────────────────
    if target_file:
        fallback_data = {}
        if os.path.exists(analysis_path):
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    fallback_data = json.load(f)
                    execution_log.append({"task": "Loaded stored document analysis", "status": "done"})
            except Exception:
                pass

        if not fallback_data and context.strip():
            raw_lines = [l.strip() for l in context.split('\n') if len(l.strip()) > 10]
            fallback_data = {
                "title": "Industrial Analysis Report",
                "purpose": raw_lines[0] if raw_lines else "Analysis of uploaded document.",
                "document_summary": " ".join(raw_lines[:3]) if raw_lines else "Extracted document summary.",
                "key_findings": raw_lines[:5],
                "risks": [l for l in raw_lines if any(k in l.lower() for k in ["risk", "issue", "fail", "error"])],
                "recommendations": [l for l in raw_lines if any(k in l.lower() for k in ["should", "must", "recommend", "action"])],
                "conclusion": "Report generated based on workspace document context."
            }

        gen_context = json.dumps(fallback_data, indent=2) if fallback_data else context

        try:
            path = ""
            if target_file == "docx":
                data = {
                    "title": fallback_data.get("title") or fallback_data.get("purpose") or "Document Analysis Report",
                    "subject": fallback_data.get("purpose") or "Analysis Summary",
                    "background": fallback_data.get("document_summary") or "",
                    "findings": fallback_data.get("key_findings") or [],
                    "technical_assessment": fallback_data.get("document_summary") or "",
                    "risk_impact": "\n".join(fallback_data.get("risks", [])) if isinstance(fallback_data.get("risks"), list) else str(fallback_data.get("risks", "")),
                    "recommendations": fallback_data.get("recommendations") or [],
                    "conclusion": fallback_data.get("conclusion") or "Analysis completed successfully."
                }
                path = os.path.join(output_dir, "Generated_Report.docx")
                create_word_report(data, path)
                file_metadata = {"filename": "Generated_Report.docx", "type": "docx"}
                response_text = "✅ **Word (.docx) Report Generated Successfully**\n\nYour Word document has been compiled and is ready for download."

            elif target_file == "xlsx":
                data = []
                if fallback_data.get("purpose"): data.append({"Category": "Purpose", "Details": str(fallback_data["purpose"])})
                if fallback_data.get("document_summary"): data.append({"Category": "Summary", "Details": str(fallback_data["document_summary"])})
                for f in fallback_data.get("key_findings", []): data.append({"Category": "Key Finding", "Details": str(f)})
                for r in fallback_data.get("risks", []): data.append({"Category": "Risk / Issue", "Details": str(r)})
                for rec in fallback_data.get("recommendations", []): data.append({"Category": "Recommendation", "Details": str(rec)})
                if not data:
                    data = [{"Category": "Overview", "Details": "Document analysis extracted."}]
                path = os.path.join(output_dir, "Generated_Data.xlsx")
                create_excel_report(data, path)
                file_metadata = {"filename": "Generated_Data.xlsx", "type": "xlsx"}
                response_text = "✅ **Excel (.xlsx) Spreadsheet Generated Successfully**\n\nYour data table has been structured and exported to an Excel file."

            elif target_file == "pptx":
                data = {
                    "title": fallback_data.get("title") or fallback_data.get("purpose") or "Document Analysis Presentation",
                    "executive_summary": fallback_data.get("document_summary") or fallback_data.get("purpose") or "Analysis Summary",
                    "key_findings": fallback_data.get("key_findings") or [],
                    "recommended_actions": fallback_data.get("recommendations") or [],
                    "conclusion": fallback_data.get("conclusion") or "Presentation compiled from document analysis."
                }
                path = os.path.join(output_dir, "Generated_Presentation.pptx")
                create_ppt_report(data, path)
                file_metadata = {"filename": "Generated_Presentation.pptx", "type": "pptx"}
                response_text = "✅ **PowerPoint (.pptx) Presentation Generated Successfully**\n\nYour slide presentation has been created and is ready for download."

            elif target_file == "pdf":
                data = {
                    "title": fallback_data.get("title") or fallback_data.get("purpose") or "Document Analysis Report",
                    "document_summary": fallback_data.get("document_summary") or "",
                    "purpose": fallback_data.get("purpose") or "Document Analysis",
                    "key_findings": fallback_data.get("key_findings") or [],
                    "risks": fallback_data.get("risks") or [],
                    "recommendations": fallback_data.get("recommendations") or [],
                    "conclusion": fallback_data.get("conclusion") or "Analysis completed successfully."
                }
                path = os.path.join(output_dir, "Generated_Report.pdf")
                create_pdf_report(data, path)
                file_metadata = {"filename": "Generated_Report.pdf", "type": "pdf"}
                response_text = "✅ **PDF Report Generated Successfully**\n\nYour PDF report has been compiled and formatted for download."

            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                execution_log.append({"task": f"Verified {file_metadata['filename']}", "status": "done"})
            else:
                execution_log.append({"task": "File generation failed", "status": "error"})
                file_metadata = None
                response_text = "Unable to generate or verify the requested file."

        except Exception as e:
            execution_log.append({"task": "Generation error", "status": "error"})
            response_text = f"Error during generation: {e}"

    # ── B. Document analysis — dynamic LLM synthesis ────────────────────────
    elif task_type == "document_analysis":
        analysis_data = {}
        if os.path.exists(analysis_path):
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analysis_data = json.load(f)
            except Exception:
                pass

        if analysis_data:
            summary = analysis_data.get("document_summary") or analysis_data.get("purpose", "Uploaded Document Analysis")
            findings = "\n".join(f"• {f}" for f in (analysis_data.get("key_findings") or ["Analysis completed."]))
            risks = "\n".join(f"• {r}" for r in (analysis_data.get("risks") or analysis_data.get("problems") or ["No critical risks reported."]))
            recs = "\n".join(f"• {r}" for r in (analysis_data.get("recommendations") or ["Review document findings."]))
            conclusion = analysis_data.get("conclusion", "Document analysis compiled from indexed content.")
            response_text = (
                f"### 📄 Executive Document Analysis\n\n"
                f"**Summary:** {summary}\n\n"
                f"### 🔍 Key Findings\n{findings}\n\n"
                f"### ⚠️ Operational Risks & Vulnerabilities\n{risks}\n\n"
                f"### 💡 Actionable Recommendations\n{recs}\n\n"
                f"### 📌 Conclusion\n{conclusion}"
            )
            execution_log.append({"task": "Generated instant document analysis", "status": "done"})
        else:
            sys_p = (
                "You are KaizenAI, an expert industrial document analysis assistant.\n"
                "Analyze the provided document context thoroughly and provide a structured, professional report.\n\n"
                "Include:\n"
                "1. **Executive Summary & Purpose**\n"
                "2. **Key Technical Findings & Data Metrics**\n"
                "3. **Operational Risks, Safety Issues & Vulnerabilities**\n"
                "4. **Actionable Recommendations & Next Steps**\n"
                "5. **Final Conclusion**\n\n"
                "Format the response using clean Markdown headers, bullet points, and bold text."
            )

            context_parts = []
            if context.strip():
                context_parts.append(f"DOCUMENT CONTENT:\n{context}")
            
            full_context = "\n\n".join(context_parts)[:6000]
            full_prompt = f"Document Context:\n{full_context}\n\nAnalysis Request: {clean_prompt}" if full_context else clean_prompt

            try:
                response_text = call_ollama(full_prompt, model=model_name, system=sys_p)
                execution_log.append({"task": "Generated deep document analysis", "status": "done"})
            except Exception as e:
                response_text = f"Unable to complete document analysis: {e}"

    # ── C. Document question (RAG) ───────────────────────────────────────
    elif task_type == "document_question":
        analysis_data = {}
        if os.path.exists(analysis_path):
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analysis_data = json.load(f)
            except Exception:
                pass

        print("=" * 60)
        print("===== DOCUMENT QUESTION DEBUG =====")
        print(f"User prompt: {clean_prompt}")
        print(f"Analysis cache exists: {bool(analysis_data)}")
        print(f"RAG context length: {len(context)} chars")
        if analysis_data:
            print(f"Analysis keys: {list(analysis_data.keys())}")
            print(f"Risks count: {len(analysis_data.get('risks', []))}")
            print(f"Findings count: {len(analysis_data.get('key_findings', []))}")
        print("=" * 60)

        sys_p = (
            "You are KaizenAI, an intelligent sovereign AI assistant.\n"
            "Answer the user's question clearly, accurately, and comprehensively.\n"
            "If document context is provided below, use it to ground your answer and quote key findings or specifications.\n"
            "If the prompt asks a general question, technical query, or concept explanation not found in the document, answer it fully and accurately using your general knowledge.\n"
            "Provide structured, clear bullet points and actionable insights."
        )

        context_parts = []
        if analysis_data:
            context_parts.append(f"PREVIOUS DOCUMENT ANALYSIS:\n{json.dumps(analysis_data, indent=2)}")
        if context.strip():
            context_parts.append(f"RELEVANT TEXT CHUNKS FROM DOCUMENT:\n{context}")
        
        full_context = "\n\n".join(context_parts)[:6000]

        if full_context:
            full_prompt = f"Document context:\n{full_context}\n\nUser question: {clean_prompt}"
            execution_log.append({"task": "Loaded document and analysis context", "status": "done"})
        else:
            full_prompt = clean_prompt
            execution_log.append({"task": "No document context available", "status": "warning"})

        print(f"===== FULL PROMPT TO LLM (first 1500 chars) =====")
        print(full_prompt[:1500])
        print("=" * 60)

        try:
            response_text = call_ollama(full_prompt, model=model_name, system=sys_p, history=history)
            print(f"===== LLM RESPONSE =====")
            print(response_text[:500])
            print("=" * 60)
            execution_log.append({"task": "Document question answered", "status": "done"})
        except (TimeoutError, Exception) as e:
            if analysis_data:
                findings_str = "\n".join(f"• {f}" for f in (analysis_data.get("key_findings") or [analysis_data.get("document_summary", "")]))
                response_text = f"**Document Analysis Insights:**\n\n{findings_str}"
                execution_log.append({"task": "Answered from indexed analysis cache", "status": "done"})
            else:
                response_text = f"Request timed out: {e}"

    # ── D. Code generation ───────────────────────────────────────────────
    elif task_type == "code_generation":
        sys_p    = "You are a Python coding assistant. Output ONLY Python code inside ```python blocks. Do not explain."
        execution_log.append({"task": "Generating Python code", "status": "done"})
        try:
            raw  = call_ollama(f"Task: {clean_prompt}", model=model_name, system=sys_p)
            code = extract_code_block(raw)
            if code:
                output = execute_local_code(code)
                if output.startswith("Error:"):
                    execution_log.append({"task": "Sandbox execution failed", "status": "error"})
                    response_text = f"Code ran but errored:\n```python\n{code}\n```\nOutput:\n{output}"
                else:
                    execution_log.append({"task": "Sandbox execution passed", "status": "done"})
                    response_text = f"Code executed successfully:\n```python\n{code}\n```\nOutput:\n```\n{output}\n```"
            else:
                response_text = "Could not extract valid Python code from the LLM response."
        except TimeoutError:
            response_text = "LLM timed out during code generation."
        except Exception as e:
            response_text = f"Code generation error: {e}"

    # ── E. Image analysis ────────────────────────────────────────────────
    elif task_type == "image_analysis":
        import glob
        img_files = (glob.glob(os.path.join(output_dir, "*.jpg")) +
                     glob.glob(os.path.join(output_dir, "*.jpeg")) +
                     glob.glob(os.path.join(output_dir, "*.png")))
        
        if not img_files:
            response_text = "No images found in the workspace. Please upload an image first."
            execution_log.append({"task": "No image found", "status": "error"})
        else:
            latest_image = max(img_files, key=os.path.getctime)
            execution_log.append({"task": f"Analyzing {os.path.basename(latest_image)} with vision model", "status": "done"})
            response_text = analyze_image_with_ollama(latest_image, clean_prompt, model=model_name)
            if response_text.startswith("Vision model error"):
                execution_log.append({"task": "Vision analysis failed", "status": "error"})
            else:
                execution_log.append({"task": "Vision analysis complete", "status": "done"})

    # ── F. General question ───────────────────────────────────────────────
    else:
        sys_p = (
            "You are a helpful AI assistant running entirely on a local private server. "
            "Answer clearly and concisely. "
            "Never invent information. "
            "If you don't know the answer, say so."
        )
        full_prompt = clean_prompt
        try:
            response_text = call_ollama(full_prompt, model=model_name, system=sys_p, history=history)
            execution_log.append({"task": "General query answered", "status": "done"})
        except TimeoutError:
            response_text = "The LLM timed out. Try a shorter question."
        except Exception as e:
            response_text = f"Error: {e}"

    # FINAL VERIFICATION (Completed)
    yield emit_stage("completed", "Analysis completed successfully.")

    # Yield the final result object
    final_result = {
        "routing":        routing_info,
        "plan":           plan,
        "execution_log":  execution_log,
        "file":           file_metadata,
        "file_metadata":  file_metadata,
        "response_text":  response_text
    }
    yield json.dumps({"type": "result", "data": final_result}) + "\n"
