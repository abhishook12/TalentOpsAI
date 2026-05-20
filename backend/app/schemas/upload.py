from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class AnalyzeResponse(BaseModel):
    analysis_id: str = Field(..., description="Unique ID for this analysis session")
    total_rows: int = Field(..., description="Total number of rows in the uploaded file")
    duplicates: int = Field(..., description="Number of duplicate email rows detected")
    missing_fields: int = Field(..., description="Rows missing required email field")
    invalid_emails: int = Field(..., description="Count of emails that fail regex validation")
    invalid_phones: int = Field(..., description="Count of phone numbers that fail regex validation")
    empty_columns: List[str] = Field(default_factory=list, description="Columns that are entirely empty")
    corrupted_rows: int = Field(0, description="Rows where all fields are empty")
    column_map: Dict[str, str] = Field(..., description="Mapping from logical field name to original column header")
    original_headers: List[str] = Field(default_factory=list, description="Original column headers from file")
    preview: List[Dict[str, Any]] = Field(..., description="First few rows for preview")
