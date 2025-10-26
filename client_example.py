#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例：如何调用 Feishu Doc HTTP 服务
"""

import requests
import json

def fetch_feishu_doc(url, raw_text=False):
    """
    调用 Feishu Doc HTTP 服务获取文档内容并转换为 Markdown
    
    Args:
        url: 飞书文档链接
        raw_text: 是否获取原始文本
    
    Returns:
        包含文档内容的字典
    """
    # 服务端点
    service_url = "http://localhost:8000/fetch-doc"
    
    # 请求数据
    payload = {
        "url": url,
        "raw_text": raw_text
    }
    
    try:
        # 发送 POST 请求
        response = requests.post(
            service_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )
        
        # 检查响应状态
        response.raise_for_status()
        
        # 返回解析后的 JSON 数据
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 示例使用
if __name__ == "__main__":
    # 示例文档链接
    doc_url = "https://y0by3nrkq8i.feishu.cn/wiki/LiANwgX12iOJGOkR7GRczr7LnM8"
    
    print(f"正在获取文档: {doc_url}")
    result = fetch_feishu_doc(doc_url)
    
    if result and result.get("success"):
        print("\n获取成功!")
        print(f"文件保存路径: {result.get('file_path')}")
        
        # 预览内容
        preview = result.get("markdown_content", "")[:500]
        print(f"\n内容预览: {preview}" + ("..." if len(preview) >= 500 else ""))
    else:
        print("获取失败")
        print(f"错误详情: {result}")