import os
import requests
import re
import time
from urllib.parse import quote
from typing import Optional, Tuple, List, Dict

from . import config

# --- Feishu API Client Class ---
class FeishuDocAPI:
    def __init__(self):
        self.app_id = config.APP_ID
        self.app_secret = config.APP_SECRET
        # Auth API uses feishu.cn domain (for China region)
        self.auth_base_url = "https://open.feishu.cn/open-apis"
        # Document API uses larkoffice.com domain (international)
        self.doc_base_url = "https://open.larkoffice.com/open-apis"
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

        # The authentication endpoint is global and should not be dynamically changed.
        url = "https://open.feishu.cn/open-apis/authen/v1/refresh_access_token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload, proxies={'http': None, 'https': None})
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

        url = f"{self.doc_base_url}/docx/v1/documents/{token}/blocks"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"[FeishuDocAPI.get_content] API Error: {data.get('msg', 'Unknown error')}")
        return data

    def get_content_as_markdown(self, doc_url: str) -> str:
        _type, _space_id, token = self.extract_tokens(doc_url)
        access_token = self.get_access_token()

        url = f"{self.doc_base_url}/docx/v1/documents/{token}/raw_content"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"[FeishuDocAPI.get_content_as_markdown] API Error: {data.get('msg', 'Unknown error')}")
        
        return data.get("data", {}).get("content", "")

    def get_document_info(self, document_id: str) -> Dict:
        access_token = self.get_access_token()
        url = f"{self.doc_base_url}/docx/v1/documents/{document_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        print(f"[get_document_info] Fetching document info for: {document_id}")
        print(f"[get_document_info] URL: {url}")
        response = requests.get(url, headers=headers, proxies={'http': None, 'https': None})
        response.raise_for_status()
        data = response.json()

        print(f"[get_document_info] Response code: {data.get('code')}")
        if data.get("code") != 0:
            print(f"[get_document_info] ERROR: {data.get('msg')}")
            raise Exception(f"[FeishuDocAPI.get_document_info] API Error getting document info: {data.get('msg', 'Unknown error')}")

        doc_info = data.get('data', {}).get('document', {})
        # Note: API returns 'revision_id', not 'revision'
        print(f"[get_document_info] Document revision_id: {doc_info.get('revision_id')}")
        print(f"[get_document_info] Document keys: {list(doc_info.keys())}")
        return doc_info

    def get_all_blocks(self, document_id: str) -> List[Dict]:
        access_token = self.get_access_token()
        url = f"{self.doc_base_url}/docx/v1/documents/{document_id}/blocks"
        headers = {"Authorization": f"Bearer {access_token}"}

        print(f"[get_all_blocks] Fetching blocks for document: {document_id}")
        print(f"[get_all_blocks] Using doc_base_url: {self.doc_base_url}")

        all_blocks = []
        page_token = None
        has_more = True
        page_count = 0

        while has_more:
            page_count += 1
            params = {}
            if page_token:
                params['page_token'] = page_token

            print(f"[get_all_blocks] Fetching page {page_count}...")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            if not response.text or not response.text.strip():
                print(f"[get_all_blocks] Empty response received on page {page_count}, stopping.")
                has_more = False
                continue

            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as e:
                print(f"[get_all_blocks] JSON decode error on page {page_count}: {e}")
                print(f"[get_all_blocks] Response text: {response.text[:200]}")
                has_more = False
                continue

            if data.get("code") != 0:
                error_msg = f"[FeishuDocAPI.get_all_blocks] API Error getting blocks: {data.get('msg', 'Unknown error')}, code: {data.get('code')}"
                print(error_msg)
                raise Exception(error_msg)

            items = data.get('data', {}).get('items', [])
            if items:
                print(f"[get_all_blocks] Retrieved {len(items)} blocks on page {page_count}")
                all_blocks.extend(items)

            has_more = data.get('data', {}).get('has_more', False)
            page_token = data.get('data', {}).get('page_token')

        print(f"[get_all_blocks] Total blocks retrieved: {len(all_blocks)}")
        return all_blocks

    def get_deletable_blocks(self, document_id: str, all_blocks: List[Dict], preserve_title: bool = True) -> List[str]:
        """
        Filter blocks to get IDs that can be safely deleted.
        Excludes:
        - Document root node (block_id == document_id)
        - Page blocks (block_type == 1)
        - Optionally title blocks (first heading block if preserve_title is True)
        """
        deletable_ids = []
        title_found = False

        print(f"[get_deletable_blocks] Filtering {len(all_blocks)} blocks...")
        print(f"[get_deletable_blocks] Document ID: {document_id}")
        print(f"[get_deletable_blocks] Preserve title: {preserve_title}")

        for block in all_blocks:
            block_id = block.get('block_id')
            block_type = block.get('block_type')
            parent_id = block.get('parent_id')

            # Skip document root node
            if block_id == document_id:
                print(f"[get_deletable_blocks] Skipping document root: {block_id}")
                continue

            # Skip page blocks (block_type == 1)
            if block_type == 1:
                print(f"[get_deletable_blocks] Skipping page block: {block_id}")
                continue

            # If preserve_title is True, skip the first heading block (block_type == 3)
            if preserve_title and block_type == 3 and not title_found:
                print(f"[get_deletable_blocks] Skipping title block: {block_id}")
                title_found = True
                continue

            deletable_ids.append(block_id)

        print(f"[get_deletable_blocks] Found {len(deletable_ids)} deletable blocks out of {len(all_blocks)} total blocks")
        return deletable_ids

    def delete_blocks_after_title(self, document_id: str, title_block_id: str = None):
        """
        Delete all blocks after the title in the document.
        This uses the batch_delete API which deletes children of a parent block by index range.

        Args:
            document_id: The document ID (also serves as the root block ID)
            title_block_id: Optional. The block ID of the title to preserve.
        """
        access_token = self.get_access_token()

        print(f"[delete_blocks_after_title] Deleting content after title in document: {document_id}")
        print(f"[delete_blocks_after_title] Title block ID: {title_block_id}")
        print(f"[delete_blocks_after_title] Using doc_base_url: {self.doc_base_url}")

        # Get document info for revision
        doc_info = self.get_document_info(document_id)
        revision_id = doc_info.get('revision_id')
        print(f"[delete_blocks_after_title] Document revision_id: {revision_id}")

        # Get all blocks to find the structure
        all_blocks = self.get_all_blocks(document_id)

        # Find the document root block (its children are the top-level blocks)
        root_block = None
        for block in all_blocks:
            if block.get('block_id') == document_id:
                root_block = block
                break

        if not root_block:
            print(f"[delete_blocks_after_title] ERROR: Could not find root block")
            raise Exception("Could not find document root block")

        children = root_block.get('children', [])
        print(f"[delete_blocks_after_title] Root block has {len(children)} children")

        if len(children) == 0:
            print(f"[delete_blocks_after_title] No children to delete")
            return True

        # Find the index to start deleting from
        start_index = 0
        if title_block_id:
            # Find the title block's index
            for i, child_id in enumerate(children):
                if child_id == title_block_id:
                    start_index = i + 1  # Start deleting after the title
                    print(f"[delete_blocks_after_title] Found title at index {i}, will delete from index {start_index}")
                    break

        # Calculate how many blocks to delete
        end_index = len(children)
        blocks_to_delete = end_index - start_index

        if blocks_to_delete <= 0:
            print(f"[delete_blocks_after_title] No blocks to delete after title")
            return True

        print(f"[delete_blocks_after_title] Will delete blocks from index {start_index} to {end_index} ({blocks_to_delete} blocks)")

        # API: DELETE /documents/{document_id}/blocks/{block_id}/children/batch_delete
        # The block_id here is the parent block (document root in our case)
        url = f"{self.doc_base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children/batch_delete"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        params = {
            "document_revision_id": revision_id if revision_id else -1
        }

        payload = {
            "start_index": start_index,
            "end_index": end_index
        }

        print(f"[delete_blocks_after_title] Sending DELETE request")
        print(f"[delete_blocks_after_title] URL: {url}")
        print(f"[delete_blocks_after_title] Params: {params}")
        print(f"[delete_blocks_after_title] Payload: {payload}")

        # Refresh access token again right before the delete request
        access_token = self.get_access_token()
        headers["Authorization"] = f"Bearer {access_token}"
        print(f"[delete_blocks_after_title] Refreshed access token before DELETE request")

        response = requests.delete(url, headers=headers, params=params, json=payload, proxies={'http': None, 'https': None})

        print(f"[delete_blocks_after_title] Response status code: {response.status_code}")
        print(f"[delete_blocks_after_title] Response text: {response.text}")

        if response.status_code >= 400:
            print(f"[delete_blocks_after_title] HTTP Error: {response.status_code}")
            response.raise_for_status()

        if response.text and response.text.strip():
            data = response.json()
            print(f"[delete_blocks_after_title] Response data: {data}")

            if data.get("code") != 0:
                error_msg = f"[FeishuDocAPI.delete_blocks_after_title] API Error: {data.get('msg', 'Unknown error')} code: {data.get('code')}"
                print(error_msg)
                raise Exception(error_msg)

        print(f"[delete_blocks_after_title] Successfully deleted {blocks_to_delete} blocks")
        return True
    
    # 将Markdown/HTML 格式的内容转换为文档块
    def convert_markdown_to_blocks(self, markdown_content: str) -> List[Dict]:
        access_token = self.get_access_token()
        url = f"{self.doc_base_url}/docx/v1/documents/blocks/convert"
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
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Error decoding JSON from response: {response.text}")
            raise
        if data.get("code") != 0:
            raise Exception(f"[FeishuDocAPI.convert_markdown_to_blocks] API Error: {data.get('msg', 'Unknown error')}, code: {data.get('code')}")
        return data.get("data", {}).get("blocks", [])

    def create_document(self, folder_token: str, body: dict = None) -> dict:
        access_token = self.get_access_token()
        url = f"{self.doc_base_url}/docx/v1/documents"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {"folder_token": folder_token}
        if body:
            payload['body'] = body
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"[FeishuDocAPI.create_document] API Error: {data.get('msg', 'Unknown error')}, code: {data.get('code')}")
        return data.get("data")

    def insert_blocks(self, document_id: str, blocks: List[Dict], retries: int = 3, delay: int = 2):
        access_token = self.get_access_token()
        url = f"{self.doc_base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "children": blocks
        }

        for attempt in range(retries):
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("code") == 0:
                    print("✅ Blocks inserted successfully.")
                    return data.get("data")
                else:
                    raise Exception(f"[FeishuDocAPI.insert_blocks] API Error: {data.get('msg', 'Unknown error')}, code: {data.get('code')}")
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise

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