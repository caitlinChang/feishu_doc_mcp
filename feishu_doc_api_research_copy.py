#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书文档API调研示例代码 (用户身份认证版本)
根据飞书文档链接获取文档内容
"""

import requests
import re
import json
import os
from typing import Dict, Optional, Tuple, List

class FeishuDocAPI:
    def __init__(self):
        """
        初始化飞书API客户端
        """
        self.app_id = 'cli_9ff99e2a687a100e'
        self.app_secret = '7gahJEEkhktRmiUEGDeRKnG1WjVSIVWA'
        self.base_url = "https://open.feishu.cn/open-apis"
        self.user_access_token = None
        self.refresh_token = self._load_refresh_token()

    def _load_refresh_token(self) -> Optional[str]:
        """
        从本地文件加载 refresh_token
        """
        if os.path.exists("refresh_token.txt"):
            with open("refresh_token.txt", "r") as f:
                return f.read().strip()
        return None

    def refresh_user_access_token(self) -> str:
        """
        刷新 user_access_token
        """
        if not self.refresh_token:
            raise Exception("未找到 refresh_token.txt，请先运行 auth_server.py 完成授权流程。")

        url = f"{self.base_url}/authen/v1/refresh_access_token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                token_data = data.get("data", {})
                self.user_access_token = token_data.get("access_token")
                # Update the refresh token if a new one is provided
                new_refresh_token = token_data.get("refresh_token")
                if new_refresh_token:
                    self.refresh_token = new_refresh_token
                    with open("refresh_token.txt", "w") as f:
                        f.write(self.refresh_token)

                print("User access token refreshed successfully.")
                return self.user_access_token
            else:
                raise Exception(f"刷新用户访问令牌失败: {data.get('msg')}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {e}")

    def get_access_token(self) -> str:
        """
        获取有效的 user_access_token，如果不存在或即将过期则刷新
        """
        # For simplicity, we refresh the token on every run.
        # A more optimized approach would be to check the expiry time.
        return self.refresh_user_access_token()

    def extract_tokens(self, doc_url: str) -> Tuple[str, Optional[str], str]:
        """
        从飞书文档链接中提取token和类型
        :param doc_url: 飞书文档链接
        :return: (type, space_id, token)
        """
        # 匹配wiki格式: https://space.feishu.cn/wiki/token
        wiki_pattern = r'https://([^/]+)\.feishu\.cn/wiki/([a-zA-Z0-9]+)'
        match = re.search(wiki_pattern, doc_url)
        if match:
            return 'wiki', match.group(1), match.group(2)
        
        # 匹配旧版文档格式
        old_pattern = r'https://[^/]+/docs/([a-zA-Z0-9]+)'
        match = re.search(old_pattern, doc_url)
        if match:
            return 'doc', None, match.group(1)
        
        # 匹配新版文档格式
        new_pattern = r'https://[^/]+/docx/([a-zA-Z0-9]+)'
        match = re.search(new_pattern, doc_url)
        if match:
            return 'docx', None, match.group(1)
        
        raise ValueError("无法从链接中提取token，请检查链接格式")

    def get_content(self, doc_url: str, raw_text: bool = False) -> Dict:
        """
        获取文档内容，支持不同类型
        :param doc_url: 飞书文档链接
        :param raw_text: 是否获取纯文本内容
        :return: 文档内容字典
        """
        type_, space_id, token = self.extract_tokens(doc_url)
        access_token = self.get_access_token()
        
        # All modern Feishu docs use the docx API
        endpoint = "raw_content" if raw_text else "blocks"
        url = f"{self.base_url}/docx/v1/documents/{token}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"API返回错误: {data.get('msg', '未知错误')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取内容失败: {e}")

def parse_blocks_to_md(data: Dict) -> str:
    """
    将docx块数据解析为Markdown
    """
    item_data = data.get('data', {}).get('items', [])
    if not item_data:
        return ''
    
    block_map = {item['block_id']: item for item in item_data}
    
    md_lines = []
    
    # 查找根块 (page block)
    root = next((item for item in item_data if item.get('block_type') == 1), None)
    if not root:
        # If no page block, parse all blocks sequentially
        for item in item_data:
            parse_block_recursive(item['block_id'], block_map, md_lines)
        return '\n\n'.join(md_lines)

    # 解析标题
    page = root.get('page', {})
    if page:
        title_elements = page.get('elements', [])
        title = ''.join(
            elem.get('text_run', {}).get('content', '') 
            for elem in title_elements
        )
        if title.strip():
            md_lines.append(f"# {title.strip()}")
    
    # 递归解析子块
    for child_id in root.get('children', []):
        parse_block_recursive(child_id, block_map, md_lines)
    
    return '\n\n'.join(md_lines)

def parse_block_recursive(block_id: str, block_map: Dict[str, Dict], md_lines: List[str]):
    """
    递归解析块
    """
    block = block_map.get(block_id)
    if not block:
        return
    
    bt = block['block_type']
    
    if bt == 2:  # 文本块
        text_obj = block.get('text', {})
        elements = text_obj.get('elements', [])
        content = ''
        for elem in elements:
            text_run = elem.get('text_run', {})
            line_content = text_run.get('content', '')
            style = text_run.get('text_element_style', {})
            if style.get('bold'):
                line_content = f"**{line_content}**"
            if style.get('italic'):
                line_content = f"*{line_content}*"
            if style.get('strikethrough'):
                line_content = f"~~{line_content}~~"
            if style.get('underline'):
                # Markdown doesn't have a standard underline, but <u> can be used
                line_content = f"<u>{line_content}</u>"
            content += line_content

        if content.strip():
            md_lines.append(content.strip())
    
    elif bt in [3, 4, 5, 6]: # H1-H4
        text_obj = block.get(f'heading{bt-1}', {})
        elements = text_obj.get('elements', [])
        content = ''.join(elem.get('text_run', {}).get('content', '') for elem in elements)
        if content.strip():
            md_lines.append(f"{'#' * (bt-1)} {content.strip()}")

    elif bt == 11: # Bulleted List
        text_obj = block.get('bullet', {})
        elements = text_obj.get('elements', [])
        content = ''.join(elem.get('text_run', {}).get('content', '') for elem in elements)
        if content.strip():
            md_lines.append(f"- {content.strip()}")

    elif bt == 12: # Ordered List
        text_obj = block.get('ordered', {})
        elements = text_obj.get('elements', [])
        content = ''.join(elem.get('text_run', {}).get('content', '') for elem in elements)
        if content.strip():
            # The sequence number needs context from the parent, simplified here
            md_lines.append(f"1. {content.strip()}")

    elif bt == 15: # Code Block
        text_obj = block.get('code', {})
        elements = text_obj.get('elements', [])
        content = ''.join(elem.get('text_run', {}).get('content', '') for elem in elements)
        lang = block.get('code', {}).get('style', {}).get('language', '')
        md_lines.append(f"```{lang}\n{content.strip()}\n```")

    elif bt == 31:  # 表格块
        table_obj = block.get('table', {})
        cells = table_obj.get('cells', [])
        property_ = table_obj.get('property', {})
        row_size = property_.get('row_size', 1)
        col_size = property_.get('column_size', 1)
        
        # 构建表格行
        grid = [['' for _ in range(col_size)] for _ in range(row_size)]
        
        idx = 0
        for r in range(row_size):
            for c in range(col_size):
                if idx < len(cells):
                    cell_id = cells[idx]
                    cell_md = []
                    parse_block_recursive(cell_id, block_map, cell_md)
                    grid[r][c] = ' '.join(cell_md).strip().replace('\n', '<br>')
                idx += 1
        
        # 生成MD表格
        if grid:
            header = "| " + " | ".join(grid[0]) + " |"
            separator = "| " + " | ".join(["---"] * col_size) + " |"
            rows_md = [header, separator]
            for row in grid[1:]:
                rows_md.append("| " + " | ".join(row) + " |")
            md_lines.append('\n'.join(rows_md))
    
    # 递归子块
    for child_id in block.get('children', []):
        parse_block_recursive(child_id, block_map, md_lines)

def main():
    """
    示例用法
    """
    # 示例文档链接 (请替换为您自己的链接)
    doc_url = "https://bytedance.larkoffice.com/docx/EU6HdJw0BoZvi3xO1xzcEaARnZc"
    
    # 创建API客户端
    feishu = FeishuDocAPI()
    
    try:
        # 获取并刷新用户访问令牌 (此步骤在 get_content 内部自动完成)
        print("准备获取文档内容 (将自动刷新用户令牌)...")

        # 获取富文本内容
        content = feishu.get_content(doc_url, raw_text=False)
        
        # 解析为Markdown
        md_content = parse_blocks_to_md(content)
        
        # 生成markdown文件
        output_filename = 'feishu_content_user_auth.md'
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"Markdown 文件已生成: {output_filename}")
        preview = md_content[:500] + "..." if len(md_content) > 500 else md_content
        print("内容预览:")
        print(preview)
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()