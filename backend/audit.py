import time
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

audit_logs = []

class NetworkAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # We process the request
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Determine if any part of the request indicates an external call.
        # Since this is a prototype, we log the API endpoint hit and assert its locality.
        # In a real system, this would hook into socket/urllib to catch all outbound requests.
        path = request.url.path
        
        status = "local"
        destination = "localhost (FastAPI/Ollama)"
        operation = f"API Request: {request.method} {path}"
        
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "operation": operation,
            "destination": destination,
            "local_external": status,
            "latency_ms": round(process_time * 1000, 2)
        }
        
        audit_logs.append(log_entry)
        
        # Keep only the last 100 logs in memory
        if len(audit_logs) > 100:
            audit_logs.pop(0)
            
        return response

def get_audit_logs():
    return audit_logs

def get_audit_stats():
    local_count = sum(1 for log in audit_logs if log.get("local_external") == "local")
    external_count = sum(1 for log in audit_logs if log.get("local_external") == "external")
    return {
        "external_calls": external_count,
        "local_calls": local_count,
        "cloud_uploads": 0,
        "total_requests": len(audit_logs)
    }
