def generate_plan(prompt: str, task_type: str, target_file: str = None) -> list[str]:
    """
    Generates a structured plan of steps based on the user request.
    For this prototype, we use heuristic-based plan templates.
    """
    prompt_lower = prompt.lower()
    
    plan = ["Analyze user request"]
    
    if task_type == "document_analysis":
        if "image" in prompt_lower or "photograph" in prompt_lower:
            plan.extend([
                "Search local knowledge base for relevant SOPs/Manuals",
                "Extract evidence from documents",
                "Analyze equipment image using Vision model",
                "Cross-reference visual findings with document evidence"
            ])
        else:
            plan.extend([
                "Search local knowledge base for relevant documents",
                "Extract text and reasoning"
            ])
    elif task_type == "code_generation":
        plan.extend([
            "Generate python code using Coding model",
            "Execute code in secure sandbox",
            "Verify code execution results"
        ])
    elif task_type == "image_analysis":
        plan.extend([
            "Analyze image using Vision model",
            "Format visual observations"
        ])
    else:
        plan.extend(["Generate response using General model"])
        
    if target_file == "docx":
        plan.extend(["Generate structured analysis", "Generate DOCX report", "Verify DOCX file"])
    elif target_file == "xlsx":
        plan.extend(["Generate structured analysis", "Generate XLSX summary", "Verify XLSX file"])
    elif target_file == "pptx":
        plan.extend(["Generate structured analysis", "Generate PPTX presentation", "Verify PPTX file"])
    else:
        plan.append("Generate final response")
        
    return plan
