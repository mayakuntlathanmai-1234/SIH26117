# SIH26117 Requirement Mapping

| Requirement | Implementation Component | Demo Evidence | Status |
|---|---|---|---|
| 1. On-Premise AI | Local Ollama, FastAPI | System starts disconnected | Partially Implemented (Missing router) |
| 2. Air-Gapped Operation | Offline dependencies | Disconnect test | Implemented |
| 3. Multiple Open-Weight Models | Model Registry (Qwen, Coding, Vision) | UI shows selected model | Missing |
| 4. Model Auto-Selection | Task Classifier / Router | Logs & UI indicate routing | Missing |
| 5. Extensible Model Registry | `model_registry.json` | Registry loaded on startup | Missing |
| 6. Real Agentic Behavior | Plan -> Tool Select -> Exec | UI Agent steps | Partially Implemented (Stub) |
| 7. Local Tools | Tool logic for read, write, etc. | Tool execution logs | Partially Implemented (Stub) |
| 8. Local Document Processing | `pypdf` for text, `pytesseract` for OCR | Docs uploaded/indexed | Partially Implemented (No OCR) |
| 9. OCR | `pytesseract` pipeline | Scanned PDF read | Missing |
| 10. Multimodal AI | Qwen-VL integration | Image analysis endpoint | Partially Implemented (Stub) |
| 11. Handwritten Notes | OCR with confidence | Confidence warning displayed | Missing |
| 12. Engineering Drawings | Vision model prompt tuning | Warning for qualified engineer | Missing |
| 13. Local RAG | ChromaDB + SentenceTransformers | Source citations | Implemented |
| 14. Organizational Knowledge | Upload endpoint & indexing | Docs list in UI | Implemented |
| 15. Grounded Answers | Citation from ChromaDB | Source links in UI | Partially Implemented (Stub) |
| 16. Calculations | `calculate` tool via python | Calculation output | Partially Implemented (Basic eval) |
| 17. Code Generation | Coding model route | Generated code | Missing |
| 18. Sandboxed Execution | Subprocess with timeout/isolation | `execute_code` tool | Missing |
| 19. Word Output | `python-docx` integration | Downloadable `.docx` | Partially Implemented (Stub) |
| 20. Excel Output | `openpyxl` integration | Downloadable `.xlsx` | Partially Implemented (Stub) |
| 21. PowerPoint Output | `python-pptx` integration | Downloadable `.pptx` | Missing |
| 22. Sovereignty Dashboard | Frontend UI panel | Local mode indicators | Partially Implemented |
| 23. Network Audit | Audit logger middleware | Audit logs in UI | Missing |
