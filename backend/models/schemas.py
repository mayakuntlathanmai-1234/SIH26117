from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    history: Optional[List[dict]] = None

class QueryRequest(BaseModel):
    query: str

class ImageAnalysisRequest(BaseModel):
    image_path: Optional[str] = None
    image_name: Optional[str] = None
    prompt: Optional[str] = "Describe the visible condition of this equipment in detail."

class ReportRequest(BaseModel):
    title: str
    summary: str
    cause: str
    recommendations: str
    data: Optional[dict] = None
