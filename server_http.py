from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Tuple, List, Dict
import os
import requests
import re
import uvicorn
from urllib.parse import quote

# --- Configuration ---
APP_ID = 'cli_9ff99e2a687a100e'
APP_SECRET = '7gahJEEkhktRmiUEGDeRKnG1WjVSIVWA'
# IMPORTANT: This must match the redirect URI in your Feishu App settings
REDIRECT_URI = 'https://lumi-boe.bytedance.net'
BASE_URL = "https://open.feishu.cn/open-apis"

# --- FastAPI App Initialization ---
app = FastAPI(title="Feishu Doc HTTP Service", description="HTTP service to fetch and convert Feishu documents")

# --- Feishu API Client Class ---
class FeishuDocAPI:
    def __init__(self):
        self.app_id = APP_ID
        self.app_secret = APP_SECRET
        self.base_url = BASE_URL
        self.user_access_token = None
        self.refresh_token = self._load_refresh_token()

    def _load_refresh_token(self) -> Optional[str]:
        if os.path.exists("refresh_token.txt"):
            with open("refresh_token.txt", "r") as f:
                return f.read().strip()
        return None

    def refresh_user_access_token(self) -> str:
        if not self.refresh_token:
            raise Exception("Refresh token not found. Please generate it first using get_token.py.")

        url = f"{self.base_url}/authen/v1/refresh_access_token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            token_data = data.get("data", {})
            self.user_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")
            if new_refresh_token:
                self.refresh_token = new_refresh_token
                with open("refresh_token.txt", "w") as f:
                    f.write(self.refresh_token)
            print("✅ User access token refreshed successfully.")
            return self.user_access_token
        else:
            if os.path.exists("refresh_token.txt"):
                os.remove("refresh_token.txt")
            raise Exception(f"❌ Failed to refresh token: {data.get('msg')}. The token might be expired. Please re-authorize.")

    def get_access_token(self) -> str:
        return self.refresh_user_access_token()

    def extract_tokens(self, doc_url: str) -> Tuple[str, Optional[str], str]:
        patterns = {
            'wiki': r'https://([^/]+)\.feishu\.cn/wiki/([a-zA-Z0-9]+)',
            'doc': r'https://[^/]+/docs/([a-zA-Z0-9]+)',
            'docx': r'https://[^/]+/docx/([a-zA-Z0-9]+)'
        }
        for type_, pattern in patterns.items():
            match = re.search(pattern, doc_url)
            if match:
                # For wiki, group(1) is space_id, group(2) is token
                return (type_, match.group(1), match.group(2)) if type_ == 'wiki' else (type_, None, match.group(1))
        raise ValueError("Could not extract token from URL.")

    def get_content(self, doc_url: str) -> dict:
        _type, _space_id, token = self.extract_tokens(doc_url)
        access_token = self.get_access_token()
        
        url = f"{self.base_url}/docx/v1/documents/{token}/blocks"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')}")
        return data

    def get_content_as_markdown(self, doc_url: str) -> str:
        _type, _space_id, token = self.extract_tokens(doc_url)
        access_token = self.get_access_token()

        url = f"{self.base_url}/docx/v1/documents/{token}/raw_content"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')}")
        
        return data.get("data", {}).get("content", "")

    def convert_markdown_to_blocks(self, markdown_content: str) -> List[Dict]:
        access_token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents/blocks/convert"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "content_type": "markdown",
            "content": markdown_content
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')}, code: {data.get('code')}")
        return data.get("data", {}).get("blocks", [])

    def create_document(self, folder_token: str, body: dict = None) -> dict:
        access_token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {"folder_token": folder_token}
        if body:
            payload['body'] = body
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')}, code: {data.get('code')}")
        response.raise_for_status()
        return data.get("data")

    def insert_blocks(self, document_id: str, blocks: List[Dict]):
        access_token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "children": blocks
        }
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')}, code: {data.get('code')}")

        response.raise_for_status()
        return data.get("data")

api_client = FeishuDocAPI()

# --- Markdown Parsing Functions ---
def parse_blocks_to_md(data: dict) -> str:
    items = data.get('data', {}).get('items', [])
    if not items:
        return ''
    block_map = {item['block_id']: item for item in items}
    md_lines = []
    # Process blocks in the order they appear
    for item in items:
        parse_block_recursive(item['block_id'], block_map, md_lines, processed_ids=set())
    return '\n\n'.join(md_lines)

def parse_block_recursive(block_id: str, block_map: dict, md_lines: List[str], processed_ids: set):
    if block_id in processed_ids:
        return
    processed_ids.add(block_id)

    block = block_map.get(block_id)
    if not block: return

    # Simplified parser logic - extend as needed
    bt = block.get('block_type')
    if bt == 2: # Text
        elements = block.get('text', {}).get('elements', [])
        content = ''.join(e.get('text_run', {}).get('content', '') for e in elements)
        if content.strip():
            md_lines.append(content.strip())

    # Recursively parse children
    for child_id in block.get('children', []):
        parse_block_recursive(child_id, block_map, md_lines, processed_ids)

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
            f"?app_id={APP_ID}"
            f"&redirect_uri={quote(REDIRECT_URI)}"
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

    print("✅ Refresh token found. Starting server at http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run_server()