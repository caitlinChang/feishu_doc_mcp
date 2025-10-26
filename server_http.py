from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import re
import uvicorn
from urllib.parse import quote
from api import config
from api.create_mr import create_mr, CreateMergeRequestResponse
from api.feishu import FeishuDocAPI, parse_blocks_to_md

# --- FastAPI App Initialization ---
app = FastAPI(title="Feishu Doc HTTP Service", description="HTTP service to fetch and convert Feishu documents")
api_client = FeishuDocAPI()

# --- API Endpoints ---
class DocRequest(BaseModel):
    url: str
    format: Optional[str] = None

@app.post("/fetch-doc")
async def fetch_doc_endpoint(request: DocRequest):
    try:
        if request.format == 'markdown':
            md_content = api_client.get_content_as_markdown(request.url)
        else:
            content = api_client.get_content(request.url)
            md_content = parse_blocks_to_md(content)
        
        doc_dir = "doc"
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir)
        
        # Sanitize URL to create a valid filename
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

class CreateMRRequest(BaseModel):
    title: str
    description: str
    # source_repo_id: str
    # target_repo_id: str
    source_branch: str
    target_branch: str
    # reviewer_ids: Optional[List[int]] = None
    # work_item_ids: Optional[List[str]] = None
    # cookie: str

@app.post("/create-mr", response_model=CreateMergeRequestResponse)
async def create_mr_endpoint(request: CreateMRRequest):
    try:
        return create_mr(
            title=request.title,
            description=request.description,
            # source_repo_id=request.source_repo_id,
            # target_repo_id=request.target_repo_id,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
            # cookie=request.cookie,
            # reviewer_ids=request.reviewer_ids,
            # work_item_ids=request.work_item_ids,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateDocRequest(BaseModel):
    folder_token: str
    markdown_content: str

@app.post("/create-doc")
async def create_doc_endpoint(request: CreateDocRequest):
    try:
        # 1. Create an empty document
        new_doc_data = api_client.create_document(request.folder_token)
        document_id = new_doc_data.get("document", {}).get("document_id")

        # 2. Convert markdown to blocks
        blocks = api_client.convert_markdown_to_blocks(request.markdown_content)

        # 3. Insert blocks into the new document
        api_client.insert_blocks(document_id, blocks)

        doc_url = f"https://bytedance.larkoffice.com/docx/{document_id}"
        return {"success": True, "url": doc_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Server Startup Logic ---
def run_server():
    if not os.path.exists("refresh_token.txt"):
        auth_url = (
            f"https://open.feishu.cn/open-apis/authen/v1/authorize"
            f"?app_id={config.APP_ID}"
            f"&redirect_uri={quote(config.REDIRECT_URI)}"
            f"&scope=docx:document:readonly%20docx:document:create%20docx:document:write_only"
        )
        print("="*80)
        print("### 授权流程指南 (Authorization Required) ###")
        print("\n1. 复制下面的URL到您的浏览器中打开，并完成飞书授权:")
        print(f"\n   {auth_url}\n")
        print("2. 授权后，您将被重定向到一个URL。请完整复制那个重定向后的URL。")
        print("   (例如: https://lumi-boe.bytedance.net/?code=...)")
        print("\n3. 打开一个新的终端，运行以下命令 (将'PASTE_URL_HERE'替换为您复制的URL):")
        print("\n   python get_token.py \"PASTE_URL_HERE\"\n")
        print("4. 成功生成 `refresh_token.txt` 文件后，请重新启动本服务 (python server_http.py)。")
        print("="*80)
        return # Stop server execution if token is missing

    print("✅ Refresh token found. Starting server at http://0.0.0.0:8001")
    uvicorn.run("server_http:app", host="0.0.0.0", port=8001, reload=True)

if __name__ == "__main__":
    run_server()