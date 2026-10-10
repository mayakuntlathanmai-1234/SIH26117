import re
from config import settings


def route_task(prompt: str) -> dict:
    """
    Classify user prompt into one of these task types:

        general_query      – simple factual question, no documents needed
        document_question  – user is asking a question about an uploaded document
        document_analysis  – user wants a full analysis/summary of a document
        code_generation    – user wants Python code written and/or executed
        image_analysis     – user wants an image or photo analyzed

    Then resolves the right model from model_registry.json.
    """
    registry = settings.model_registry

    # Strip frontend annotation "(Focus on documents: ...)" before classifying
    has_focus_doc = bool(re.search(r'\(Focus on documents:.*?\)', prompt, flags=re.IGNORECASE))
    clean = re.sub(r'\(Focus on documents:.*?\)', '', prompt, flags=re.IGNORECASE).strip()
    pl = clean.lower()

    # ── 1. File-generation target (checked first – highest priority) ──────
    target_file = None
    if re.search(r'\b(generate|create|export|make|prepare|convert|turn|extract|save|build|download)\b.*(docx|word|approval.?note)', pl) or "export docx" in pl or "word docx" in pl:
        target_file = "docx"
    elif re.search(r'\b(generate|create|export|make|prepare|convert|turn|extract|save|build|download)\b.*(xlsx|excel|spreadsheet)', pl) or "export xlsx" in pl or "excel xlsx" in pl:
        target_file = "xlsx"
    elif re.search(r'\b(generate|create|export|make|prepare|convert|turn|extract|save|build|download)\b.*(pptx|powerpoint|presentation|ppt|slides?)', pl) or "export pptx" in pl or "pptx presentation" in pl:
        target_file = "pptx"
    elif re.search(r'\b(generate|create|export|make|prepare|convert|turn|extract|save|build|download)\b.*(pdf)', pl) or "export pdf" in pl or "pdf report" in pl:
        target_file = "pdf"

    # ── 2. Task classification ────────────────────────────────────────────
    task_type     = "general_query"
    selected_role = "General"
    reason        = "Simple factual question – answered directly by LLM."

    CODE_WORDS = [
        "code", "python", "script", "function", "class", "loop",
        "algorithm", "program", "debug", "calculate", "compute"
    ]
    IMAGE_WORDS = ["image", "photo", "photograph", "picture", "drawing", "visual", "diagram"]

    FULL_ANALYSIS_WORDS = [
        "analyse", "analyze", "full analysis", "summarize this document",
        "summarise this document", "analyse the document", "analyze the document",
        "analyse the report", "analyze the report", "analyse the given",
        "analyze the given", "give me a summary of", "break down this"
    ]

    # Questions that reference the uploaded document but don't ask for a full analysis
    DOC_QUESTION_WORDS = [
        "what does the document say", "according to the document",
        "based on the document", "in the document", "in the report",
        "in the pdf", "from the document", "from the report",
        "what is the", "how many", "what are the", "who is", "when is",
        "where is", "tell me about", "explain", "describe",
        "what does it say", "find", "list", "show me", "risks", "problems",
        "recommendations", "findings"
    ]

    if any(kw in pl for kw in IMAGE_WORDS):
        task_type     = "image_analysis"
        selected_role = "Vision"
        reason        = "Task explicitly involves visual/image content."

    elif any(kw in pl for kw in CODE_WORDS):
        task_type     = "code_generation"
        selected_role = "Coding"
        reason        = "Task involves writing or executing code."

    elif any(kw in pl for kw in FULL_ANALYSIS_WORDS):
        task_type     = "document_analysis"
        selected_role = "General"
        reason        = "User wants a full document analysis/summary."

    elif any(kw in pl for kw in DOC_QUESTION_WORDS):
        task_type     = "document_question"
        selected_role = "General"
        reason        = "User is asking a specific question – will use RAG to retrieve relevant chunks."

    # If general query but focus doc exists, default to document_question to retain context
    if task_type == "general_query" and has_focus_doc:
        task_type     = "document_question"
        selected_role = "General"
        reason        = "Workspace contains active documents – routing simple/ambiguous query as a document question."

    # If a file target was detected, override task type to keep it consistent
    if target_file:
        task_type = "document_analysis"   # reuse document_analysis branch for file gen
        selected_role = "General"
        reason = f"User wants to generate a {target_file.upper()} file."

    model_config = registry.get(selected_role, {})
    model_name   = model_config.get("model_name", "qwen2:0.5b")

    result = {
        "task_type":     task_type,
        "selected_role": selected_role,
        "model_name":    model_name,
        "reason":        reason,
        "target_file":   target_file
    }
    print(f"[ROUTER] '{clean[:60]}...' -> {task_type} | has_focus_doc={has_focus_doc} | reason={reason}")
    return result
