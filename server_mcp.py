from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import re

from mcp.server.fastmcp import FastMCP
from api.feishu import FeishuDocAPI, parse_blocks_to_md
from api.create_mr import create_mr, CreateMergeRequestResponse

mcp = FastMCP(
    "feishu_doc_mcp_service",
    host="0.0.0.0",
    port=8000  # Running on a different port to avoid conflict with HTTP server
)

api_client = FeishuDocAPI()

class DocRequest(BaseModel):
    url: str
    format: Optional[str] = None

class CreateDocRequest(BaseModel):
    folder_token: str
    markdown_content: str

class CreateMRRequest(BaseModel):
    title: str
    description: str
    source_branch: str
    target_branch: str

@mcp.tool()
def fetch_doc(request: DocRequest):
    """
    Fetch Feishu document content from URL and convert to Markdown.
    Args:
        url: The URL of the Feishu document.
        format: The format to return, either 'markdown' for raw markdown or 'blocks' for structured content.
    Returns:
        A dictionary containing the success status, markdown content, and file path.
    """
    try:
        if request.format == 'markdown':
            md_content = api_client.get_content_as_markdown(request.url)
        else:
            content = api_client.get_content(request.url)
            md_content = parse_blocks_to_md(content)
        
        doc_dir = "doc"
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir)
        
        sanitized_token = re.sub(r'[\W_]+', '-', request.url.split('/')[-1])
        filename = f"feishu_content_{sanitized_token}.md"
        filepath = os.path.join(doc_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return {
            "success": True,
            "markdown_content": md_content,
            "file_path": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@mcp.tool()
def create_doc(request: CreateDocRequest):
    """
    Create a new Feishu document with the given markdown content.
    Args:
        folder_token: The token of the folder to create the document in.
        markdown_content: The markdown content of the document.
    Returns:
        A dictionary containing the success status and the URL of the new document.
    """
    try:
        new_doc_data = api_client.create_document(request.folder_token)
        document_id = new_doc_data.get("document", {}).get("document_id")

        blocks = api_client.convert_markdown_to_blocks(request.markdown_content)

        api_client.insert_blocks(document_id, blocks)

        doc_url = f"https://bytedance.larkoffice.com/docx/{document_id}"
        return {"success": True, "url": doc_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@mcp.tool()
def create_mr_mcp(request: CreateMRRequest):
    """
    Create a new merge request.
    Args:
        title: The title of the merge request.
        description: The description of the merge request.
        source_branch: The source branch of the merge request.
        target_branch: The target branch of the merge request.
    Returns:
        A CreateMergeRequestResponse object.
    """
    try:
        return create_mr(
            title=request.title,
            description=request.description,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    mcp.run(transport="streamable-http")