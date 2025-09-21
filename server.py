from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from feishu_doc_api_research import FeishuDocAPI, parse_blocks_to_md

app = FastAPI(title="Feishu Doc MCP Service", description="Service to fetch and convert Feishu documents to Markdown")

api_client = FeishuDocAPI()

class DocRequest(BaseModel):
    url: str
    raw_text: Optional[bool] = False

@app.post("/fetch_doc")
async def fetch_doc(request: DocRequest):
    try:
        content = api_client.get_content(request.url, request.raw_text)
        md_content = parse_blocks_to_md(content)
        
        # Generate filename with timestamp or unique
        filename = f"feishu_content_{len(os.listdir('.')) + 1}.md"
        filepath = os.path.join(os.getcwd(), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return {
            "success": True,
            "markdown_content": md_content,
            "file_path": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)