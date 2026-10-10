import subprocess
import os
import tempfile
import sys
import ast

FORBIDDEN_MODULES = {"subprocess", "shutil", "socket", "http", "urllib", "requests", "ctypes", "multiprocessing"}
FORBIDDEN_FUNCTIONS = {"eval", "exec", "__import__", "compile"}

def validate_code_ast(code: str) -> tuple[bool, str]:
    """Inspects code syntax tree to disallow unsafe module imports or execution primitives."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in code: {e}"
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] in FORBIDDEN_MODULES:
                    return False, f"Security Violation: Import of restricted module '{alias.name}' is blocked."
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] in FORBIDDEN_MODULES:
                return False, f"Security Violation: Import from restricted module '{node.module}' is blocked."
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_FUNCTIONS:
                return False, f"Security Violation: Function call '{node.func.id}' is blocked."
            elif isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen", "spawn", "remove", "rmdir"}:
                if isinstance(node.func.value, ast.Name) and node.func.value.id in {"os", "sys"}:
                    return False, f"Security Violation: Call '{node.func.value.id}.{node.func.attr}' is blocked."
                    
    return True, ""

def execute_code_sandboxed(code: str, timeout: int = 10) -> dict:
    """
    Executes Python code in a temporary directory with AST safety checks and timeout.
    """
    is_safe, error_msg = validate_code_ast(code)
    if not is_safe:
        return {
            "success": False,
            "stdout": "",
            "stderr": error_msg,
            "timeout": False
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the code to a file in the temp directory
        script_path = os.path.join(temp_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        try:
            process = subprocess.Popen(
                [sys.executable, "script.py"],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "timeout": False
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return {
                "success": False,
                "stdout": stdout,
                "stderr": "Execution timed out.",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "timeout": False
            }
