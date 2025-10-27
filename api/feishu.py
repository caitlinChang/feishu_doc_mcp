import os
import requests
import re
from urllib.parse import quote
from typing import Optional, Tuple, List, Dict

from . import config

# --- Feishu API Client Class ---
class FeishuDocAPI:
    def __init__(self):
        self.app_id = config.APP_ID
        self.app_secret = config.APP_SECRET
        self.base_url = config.BASE_URL
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
    
    # 将Markdown/HTML 格式的内容转换为文档块
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
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks"
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