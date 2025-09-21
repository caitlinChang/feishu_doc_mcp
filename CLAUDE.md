# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands
- Install dependencies: `pip install -r requirements.txt`
- Run the research script: `python feishu_doc_api_research.py`

## Project Architecture
This repository contains a simple Python script for interacting with the Feishu (Lark) Document API to retrieve document contents from provided URLs. The core logic is in `feishu_doc_api_research.py`, which implements the `FeishuDocAPI` class. This class handles:
- Authentication via tenant access tokens using App ID and Secret.
- Extraction of document tokens from URLs supporting both old (`/docs/`) and new (`/docx/`) formats.
- API calls to fetch rich text or raw content using the Feishu Open Platform APIs.

Dependencies include `requests` for HTTP interactions, and server-related packages like `fastapi`, `uvicorn`, and `mcp` indicating potential for building an API service around this functionality. The project supports Python 3.6+ and focuses on error handling for API responses, permissions, and network issues.

Refer to README.md for detailed API usage, permissions, and official documentation links.

## Contention
If the language you receive is Chinese, think and work in English, but output in Chinese.