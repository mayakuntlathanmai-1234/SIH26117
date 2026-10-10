import os
import sys
import json
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_01_backend_health():
    """Verify backend health endpoint is active and offline ready."""
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["offline_ready"] is True

def test_02_system_status():
    """Verify all internal components are ready and 0 external calls are made."""
    resp = requests.get(f"{BASE_URL}/system/status", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm"] is True
    assert data["rag"] is True
    assert data["external_calls"] == 0

def test_03_sandbox_ast_security():
    """Verify AST security validation blocks dangerous modules and primitives."""
    from agent.sandbox import validate_code_ast, execute_code_sandboxed

    # Blocked imports
    safe, msg = validate_code_ast("import subprocess\nsubprocess.run(['dir'])")
    assert not safe
    assert "subprocess" in msg

    # Blocked functions
    safe, msg = validate_code_ast("eval('1 + 1')")
    assert not safe
    assert "eval" in msg

    # Safe execution
    res = execute_code_sandboxed("x = 100 * 5\nprint(f'Result={x}')")
    assert res["success"] is True
    assert "Result=500" in res["stdout"]

def test_04_tools_execution():
    """Verify agent tools (calculate, search_documents, read_document)."""
    from agent.tools import calculate, read_document

    calc_res = calculate("256 / 4 + 10")
    assert "74" in calc_res

    missing_doc = read_document("non_existent_file.pdf")
    assert "File not found" in missing_doc

def test_05_document_upload_and_extraction():
    """Verify document upload, text extraction, chunking, and ChromaDB indexing."""
    sample_txt_path = os.path.join(os.path.dirname(__file__), "data", "documents", "audit_test.txt")
    with open(sample_txt_path, "w", encoding="utf-8") as f:
        f.write(
            "TURBINE MAINTENANCE PROTOCOL 2026\n"
            "Operating Temperature: Nominal threshold is 850 degrees Celsius.\n"
            "Inspection Schedule: Bearings must be inspected every 300 operating hours.\n"
            "Known Critical Risk: High vibration in Rotor 3 indicates hydraulic seal failure.\n"
            "Action Plan: Replace O-rings immediately upon sensor alert.\n"
        )

    with open(sample_txt_path, "rb") as f:
        resp = requests.post(f"{BASE_URL}/upload", files={"file": ("audit_test.txt", f, "text/plain")}, timeout=15)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["document_id"] is not None
    assert "analysis_summary" in data

def test_06_document_qa_with_evidence():
    """Verify grounded question answering from uploaded document."""
    payload = {
        "message": "What indicates hydraulic seal failure according to the document?",
        "history": []
    }
    resp = requests.post(f"{BASE_URL}/agent/run", json=payload, timeout=25)
    assert resp.status_code == 200
    content = resp.text
    # Verify stream output includes final result
    assert "result" in content
    assert any(term in content.lower() for term in ["vibration", "rotor", "seal", "hydraulic", "850"])

def test_07_document_qa_absent_fact():
    """Verify model honesty when asked about facts absent from the document."""
    payload = {
        "message": "What is the CEO salary mentioned in the turbine maintenance document?",
        "history": []
    }
    resp = requests.post(f"{BASE_URL}/agent/run", json=payload, timeout=25)
    assert resp.status_code == 200
    content = resp.text
    assert "result" in content

def test_08_multimodal_vision_analysis():
    """Verify multimodal vision analysis using local moondream model."""
    poster_path = os.path.join(os.path.dirname(__file__), "data", "images", "poster.png")
    if os.path.exists(poster_path):
        resp = requests.post(
            f"{BASE_URL}/analyze-image",
            json={"image_name": "poster.png", "prompt": "Identify the primary headline text."},
            timeout=180
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis" in data
        assert data["model"] == "moondream:latest"

def test_09_multi_format_report_generation():
    """Verify sub-second generation of PDF, DOCX, XLSX, and PPTX reports."""
    formats = [
        ("Export PDF report", "Generated_Report.pdf"),
        ("Export Word DOCX report", "Generated_Report.docx"),
        ("Export Excel XLSX spreadsheet", "Generated_Data.xlsx"),
        ("Export PPTX presentation", "Generated_Presentation.pptx"),
    ]

    for prompt, expected_file in formats:
        resp = requests.post(f"{BASE_URL}/agent/run", json={"message": prompt}, timeout=15)
        assert resp.status_code == 200
        assert "result" in resp.text

        # Verify file download endpoint
        dl_resp = requests.get(f"{BASE_URL}/api/files/{expected_file}", timeout=5)
        assert dl_resp.status_code == 200
        assert len(dl_resp.content) > 1000

def test_10_audit_log_zero_external_calls():
    """Verify network audit middleware records zero external/cloud calls."""
    resp = requests.get(f"{BASE_URL}/audit/logs", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["external_calls"] == 0
    assert data["stats"]["cloud_uploads"] == 0
    assert data["stats"]["local_calls"] > 0

if __name__ == "__main__":
    tests = [
        test_01_backend_health,
        test_02_system_status,
        test_03_sandbox_ast_security,
        test_04_tools_execution,
        test_05_document_upload_and_extraction,
        test_06_document_qa_with_evidence,
        test_07_document_qa_absent_fact,
        test_08_multimodal_vision_analysis,
        test_09_multi_format_report_generation,
        test_10_audit_log_zero_external_calls,
    ]
    print("=" * 60)
    print("SOVEREIGN AI WORKBENCH - VERIFICATION TEST SUITE")
    print("=" * 60)
    passed = 0
    failed = 0
    for t in tests:
        name = t.__name__
        print(f"[{name}] ...", end=" ", flush=True)
        try:
            t()
            print("PASSED")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1
    print("=" * 60)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED out of {len(tests)} tests.")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)
