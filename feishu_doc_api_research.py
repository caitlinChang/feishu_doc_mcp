#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书文档API调研示例代码
根据飞书文档链接获取文档内容
"""

import requests
import re
import json
from typing import Dict, Optional, Tuple, List

class FeishuDocAPI:
    def __init__(self):
        """
        初始化飞书API客户端
        """
        self.app_id = 'cli_a8454a4ec139100d'
        self.app_secret = ''
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
    
    def get_access_token(self) -> str:
        """
        获取租户访问令牌 (tenant_access_token)
        """
        if self.access_token:
            return self.access_token
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal/"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                self.access_token = data["tenant_access_token"]
                return self.access_token
            else:
                raise Exception(f"获取访问令牌失败: {data.get('msg')}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {e}")
    
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
        
        if type_ == 'wiki':
            if raw_text:
                endpoint = "raw_content"
                url = f"{self.base_url}/docx/v1/documents/{token}/{endpoint}"
                params = None
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            else:
                endpoint = "blocks"
                url = f"{self.base_url}/docx/v1/documents/{token}/{endpoint}"
                params = None
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
        elif type_ == 'docx':
            endpoint = "raw_content" if raw_text else "blocks"
            url = f"{self.base_url}/docx/v1/documents/{token}/{endpoint}"
            params = None
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        elif type_ == 'doc':
            endpoint = "raw_content" if raw_text else "content"
            url = f"{self.base_url}/doc/v2/{token}/{endpoint}"
            params = None
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        else:
            raise ValueError("不支持的文档类型")
        
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
    
    # 查找根块，通常block_type为1
    root = next((item for item in item_data if item.get('block_type') == 1), None)
    if not root:
        root = item_data[0]
    
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
            content += elem.get('text_run', {}).get('content', '')
        if content.strip():
            md_lines.append(content.strip())
    
    elif bt == 31:  # 表格块
        md_lines.append("## 表格")
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
                    grid[r][c] = ' '.join(cell_md).strip()
                idx += 1
        
        # 生成MD表格
        if grid:
            header = "| " + " | ".join(grid[0]) + " |"
            separator = "| " + " | ".join(["---"] * col_size) + " |"
            rows_md = [header, separator]
            for row in grid[1:]:
                rows_md.append("| " + " | ".join(row) + " |")
            md_lines.extend(rows_md)
    
    # 其他类型可以扩展
    # 递归子块
    for child_id in block.get('children', []):
        parse_block_recursive(child_id, block_map, md_lines)

def main():
    """
    示例用法
    """
    # 示例文档链接
    doc_url = "https://y0by3nrkq8i.feishu.cn/wiki/LiANwgX12iOJGOkR7GRczr7LnM8"
    
    # 创建API客户端
    feishu = FeishuDocAPI()
    
    try:
        # 获取富文本内容
        print("获取文档内容...")
        content = feishu.get_content(doc_url, raw_text=False)
        
        # 解析为Markdown
        md_content = parse_blocks_to_md(content)
        
        # 生成markdown文件
        with open('feishu_content.md', 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print("Markdown 文件已生成: feishu_content.md")
        preview = md_content[:500] + "..." if len(md_content) > 500 else md_content
        print("内容预览:")
        print(preview)
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
