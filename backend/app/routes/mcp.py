"""
MCP (Model Context Protocol) Endpoint Router
Provides standardized tool execution for AI assistants and MCP clients:
- echo: Simple verification/roundtrip tool
- list_recruiters: Recruiter discovery query tool
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.recruiter_store import recruiter_store

logger = logging.getLogger("talentops.mcp")
router = APIRouter(prefix="/mcp", tags=["MCP"])


class MCPRequest(BaseModel):
    jsonrpc: Optional[str] = "2.0"
    id: Optional[Any] = 1
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    tool: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None


AVAILABLE_TOOLS = [
    {
        "name": "echo",
        "description": "Echoes back the input text or parameters for diagnostic verification.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to echo back."}
            },
            "required": ["message"],
        },
    },
    {
        "name": "list_recruiters",
        "description": "Lists recruiter records from the TalentOps intelligence database with optional filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of recruiters to return (default 20, max 100)."},
                "search": {"type": "string", "description": "Search term for recruiter name, company, or specialization."},
                "state": {"type": "string", "description": "US state code filter (e.g. 'TX', 'CA')."},
                "is_deliverable": {"type": "boolean", "description": "Filter by email deliverability pre-validation."}
            },
        },
    },
]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "echo":
        msg = arguments.get("message") or arguments.get("text") or str(arguments)
        return {"content": [{"type": "text", "text": msg}]}
    
    if tool_name == "list_recruiters":
        limit = min(int(arguments.get("limit", 20)), 100)
        search = arguments.get("search")
        state = arguments.get("state")
        is_deliverable = arguments.get("is_deliverable")
        
        results, total = recruiter_store.list_recruiters(
            page=1,
            limit=limit,
            search=search,
            state=state,
            is_deliverable=is_deliverable,
        )
        
        # Serialize recruiters safely
        clean_results = []
        for r in results:
            clean_results.append({
                "recruiter_id": r.get("recruiter_id"),
                "recruiter_name": r.get("recruiter_name"),
                "company_name": r.get("company_name") or (r.get("company") or {}).get("canonical_name"),
                "specialization": r.get("specialization"),
                "seniority_level": r.get("seniority_level"),
                "state": r.get("state"),
                "city": r.get("city"),
                "email": r.get("email"),
                "is_deliverable": r.get("is_deliverable"),
                "completeness_score": r.get("completeness_score"),
            })
            
        return {
            "content": [{
                "type": "text",
                "text": f"Found {total} total recruiters matching criteria. Returned {len(clean_results)}."
            }],
            "data": {
                "total": total,
                "count": len(clean_results),
                "recruiters": clean_results,
            }
        }
        
    raise ValueError(f"Unknown MCP tool: {tool_name}")


@router.get("")
@router.get("/")
def get_mcp_info():
    """Returns available MCP protocol endpoints and registered tools."""
    return {
        "status": "ready",
        "protocol": "mcp-jsonrpc-2.0",
        "server": "TalentOps MCP Gateway",
        "version": "1.0.0",
        "tools": AVAILABLE_TOOLS,
    }


@router.post("")
@router.post("/")
async def handle_mcp_post(req: MCPRequest):
    """
    Handles MCP JSON-RPC 2.0 and REST calls.
    Supports tools/list and tools/call.
    """
    # Check if JSON-RPC method call
    method = req.method
    params = req.params or {}
    
    # 1. tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "tools": AVAILABLE_TOOLS
            }
        }
        
    # 2. tools/call
    if method == "tools/call":
        tool_name = params.get("name") or req.tool
        tool_args = params.get("arguments") or req.arguments or {}
        try:
            result = execute_tool(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "result": result
            }
        except Exception as exc:
            logger.error(f"MCP tool error: {exc}")
            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "error": {
                    "code": -32603,
                    "message": str(exc)
                }
            }

    # 3. Direct tool execution via REST
    tool_name = req.tool or method
    if tool_name in ["echo", "list_recruiters"]:
        tool_args = req.arguments or params
        try:
            result = execute_tool(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "result": result
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "error": {
                    "code": -32603,
                    "message": str(exc)
                }
            }
            
    # Fallback default tools list
    return {
        "jsonrpc": "2.0",
        "id": req.id,
        "result": {
            "tools": AVAILABLE_TOOLS
        }
    }
