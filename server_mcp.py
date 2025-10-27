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
    url: str
    doc_url: Optional[str] = None
    is_replace: Optional[bool] = False

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
    Create a new Feishu document with markdown content from a file, or update an existing document.
    Args:
        url: The file path to the markdown file.
        doc_url: (Optional) The URL of an existing Feishu document to update.
        is_replace: (Optional) If true, replace existing content. If false, append content. Default is false.
    Returns:
        A dictionary containing the success status and the URL of the document.
    """
    from api import config
    import time

    try:
        # 1. Read markdown content from file
        with open(request.url, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        document_id = None

        # 2. Determine the document_id
        if request.doc_url:
            # Use existing document
            # Extract document_id from doc_url
            match = re.search(r'/docx/([a-zA-Z0-9]+)', request.doc_url)
            if match:
                document_id = match.group(1)
            else:
                raise Exception("Invalid doc_url format. Could not extract document_id.")

            if request.is_replace:
                # Get all blocks and filter deletable ones
                all_blocks = api_client.get_all_blocks(document_id)
                if all_blocks:
                    # Find the title block (first heading block)
                    title_block_id = None
                    for block in all_blocks:
                        if block.get('block_type') == 3:  # Heading block
                            title_block_id = block.get('block_id')
                            break

                    # Delete all blocks after the title
                    api_client.delete_blocks_after_title(document_id, title_block_id)
                    time.sleep(1)  # Wait for deletion to complete
        else:
            # Create a new document
            new_doc_data = api_client.create_document(config.FOLDER_TOKEN)
            document_id = new_doc_data.get("document", {}).get("document_id")

        if not document_id:
            raise Exception("Failed to get document_id.")

        # 3. Convert markdown to blocks
        blocks = api_client.convert_markdown_to_blocks(markdown_content)

        # 4. Insert blocks into the document
        api_client.insert_blocks(document_id, blocks)

        # Use the same domain as the input doc_url if provided
        if request.doc_url:
            match = re.search(r'https://([^/]+)', request.doc_url)
            if match:
                domain = match.group(1)
                doc_url = f"https://{domain}/docx/{document_id}"
            else:
                doc_url = f"https://bytedance.larkoffice.com/docx/{document_id}"
        else:
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