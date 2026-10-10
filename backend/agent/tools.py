import os
from rag.vector_store import VectorStore
from agent.sandbox import execute_code_sandboxed

# Initialize singleton vector store for tools
_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

def search_documents(query: str, n_results: int = 3) -> str:
    """Searches the local knowledge base for relevant documents."""
    vs = get_vector_store()
    results = vs.search(query, n_results=n_results)
    
    if not results:
        return "No sufficient evidence was found in the local knowledge base."
        
    formatted = "EVIDENCE:\n\n"
    for idx, res in enumerate(results):
        source = res['metadata'].get('source', 'Unknown')
        page = res['metadata'].get('page', 'Unknown')
        text = res['text']
        formatted += f"{source} (Page {page}):\n{text}\n\n"
        
    return formatted

def read_document(path: str) -> str:
    """Reads the raw text of a document from the data directory."""
    if not os.path.exists(path):
        return f"File not found: {path}"
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def calculate(expression: str) -> str:
    """Safely calculates a mathematical expression using Python evaluation."""
    try:
        # Wrap expression in a print statement and run in sandbox
        code = f"result = {expression}\nprint(result)"
        res = execute_code_sandboxed(code)
        if res["success"]:
            return res["stdout"].strip()
        else:
            return f"Error in calculation: {res['stderr']}"
    except Exception as e:
        return f"Error in calculation logic: {str(e)}"

def execute_code(code: str) -> dict:
    """Executes arbitrary python code in the sandbox."""
    return execute_code_sandboxed(code)
