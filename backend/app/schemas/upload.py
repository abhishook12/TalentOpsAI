from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class SheetAnalysis(BaseModel):
    sheet_name: str
    detected_format: str
    format_confidence: str
    has_headers: bool
    headers: List[str]
    total_rows: int
    data_rows: int
    blank_rows: int
    column_map: Dict[str, Optional[str]]
    preview: List[Dict[str, Any]]

class AnalyzeResponse(BaseModel):
    analysis_id: str = Field(..., description="Unique ID for this analysis session")
    total_rows: int = Field(..., description="Total number of rows in the uploaded file")
    file_size_bytes: int = Field(0, description="Size of the uploaded file")
    sheet_count: int = Field(1, description="Number of sheets in the file")
    sheets: List[SheetAnalysis] = Field(default_factory=list, description="Analysis per sheet")
    errors: List[str] = Field(default_factory=list, description="Parsing errors")
