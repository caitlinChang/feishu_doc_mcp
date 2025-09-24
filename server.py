from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional
from mcp.server.fastmcp import FastMCP
import os
from feishu_doc_api_research import FeishuDocAPI, parse_blocks_to_md

# app = FastAPI(title="Feishu Doc MCP Service", description="Service to fetch and convert Feishu documents to Markdown")
mcp = FastMCP("feishu_doc_fetch", host="0.0.0.0", port=8000)
api_client = FeishuDocAPI()

class DocRequest(BaseModel):
    url: str
    raw_text: Optional[bool] = False

# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     print(f"Request: {request.method} {request.url}")
#     response = await call_next(request)
#     print(f"Response status: {response.status_code}")
#     return response

# @app.post("/")
# async def register(req: Request):
#     body = await req.json()
#     client_name = body.get("client", {}).get("name", "unknown")

#     return {
#         "protocol": "mcp/1.0",
#         "server": {
#             "name": "mcp_feishu_doc_fetch",
#             "version": "0.1.0"
#         },
#         "tools": [
#             {
#                 "name": "fetch_doc",
#                 "description": "Fetch Feishu document content from URL and convert to Markdown",
#                 "inputSchema": {
#                     "type": "object",
#                     "properties": {
#                         "url": {"type": "string"},
#                     },
#                     "required": ["url"]
#                 }
#             }
#         ]
#     }

# @app.post("/register")
# async def register(req: Request):
#     body = await req.json()
#     print(f"register: {body}")
#     return {
#         "protocol": "mcp/1.0",
#         "server": {
#             "name": "mcp_feishu_doc_fetch",
#             "version": "0.1.0"
#         },
#         "tools": [
#             {
#                 "name": "fetch_doc",
#                 "description": "Fetch Feishu document content from URL and convert to Markdown",
#                 "inputSchema": {
#                     "type": "object",
#                     "properties": {
#                         "url": {"type": "string"},
#                     },
#                     "required": ["url"]
#                 }
#             }
#         ]
#     }

# @app.post("/tools/execute")
# async def execute(req: Request):
#     body = await req.json()
#     tool = body.get("tool")
#     args = body.get("arguments", {})
#     print(tool, args)
#     if tool == "fetch_doc":
#         url = args.get("url", "")
#         return {"output": f"Hello, {url}!"}

#     return {"error": f"Unknown tool {tool}"}


@mcp.tool()
async def fetch_doc(request: DocRequest):
    """
    Fetch Feishu document content from URL and convert to Markdown
    Arg:
     url: The URL of the Feishu document
     raw_text: whether to return raw text instead of blocks
    Return:
     success: Whether the operation was successful
     markdown_content: The Markdown content of the document
     file_path: The path to the generated Markdown file
    """
    try:
        content = api_client.get_content(request.url, request.raw_text)
        print(f"content: {content}")
        md_content = parse_blocks_to_md(content)
        
        # Generate filename with timestamp or unique
        filename = f"feishu_content_{len(os.listdir('.')) + 1}.md"
        filepath = os.path.join(os.getcwd(), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return {
            "success": True,
            "markdown_content": md_content,
            "file_path": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    mcp.run(transport="streamable-http")