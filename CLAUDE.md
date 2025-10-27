# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands
- Install dependencies: `pip install -r requirements.txt`
- Run HTTP server: `python3 server_http.py` (runs on port 8001)
- Run MCP server: `python3 server_mcp.py` (runs on port 8000)
- Generate refresh token (first-time setup): `python3 get_token.py "REDIRECT_URL"`

## Project Architecture

This is a Feishu (Lark) Document API integration project that provides both HTTP and MCP (Model Context Protocol) servers for interacting with Feishu documents.

### Core Components

1. **api/feishu.py** - Main API client (`FeishuDocAPI` class)
   - User access token authentication with refresh token mechanism
   - Document token extraction from URLs (supports `/docs/`, `/docx/`, `/wiki/` formats)
   - Fetch document content as blocks or markdown
   - Create new documents and insert markdown content as blocks
   - Batch delete blocks and manage document structure
   - Dynamic base URL detection based on document domain

2. **server_http.py** - FastAPI HTTP service (port 8001)
   - `/fetch-doc`: Fetch document content and save as markdown file
   - `/create-doc`: Create or update Feishu documents from markdown files
   - `/create-mr`: Create merge requests (integration with internal Code system)
   - Requires `refresh_token.txt` for authentication

3. **server_mcp.py** - MCP server (port 8000)
   - Exposes same functionality as HTTP server via MCP protocol
   - Tools: `fetch_doc`, `create_doc`, `create_mr_mcp`
   - Uses FastMCP framework with streamable-http transport

4. **api/config.py** - Configuration constants
   - Contains APP_ID, APP_SECRET, redirect URIs, and API endpoints
   - NOTE: Contains sensitive credentials - should be in .gitignore in production

5. **get_token.py** - OAuth token generator
   - Exchanges authorization code for refresh token
   - Creates `refresh_token.txt` file required by servers

### Authentication Flow

1. First run requires OAuth authorization via browser
2. `get_token.py` exchanges authorization code for refresh token
3. Refresh token stored in `refresh_token.txt`
4. Servers use refresh token to obtain user access tokens
5. Access tokens auto-refresh on expiry

### Key Features

- Bi-directional document sync (read from and write to Feishu)
- Markdown conversion using Feishu's native API
- Support for replacing entire document content or creating new documents
- Pagination handling for large documents
- Automatic token refresh and error handling

## Working Instructions

If the language you receive is Chinese, think and work in English, but output in Chinese.