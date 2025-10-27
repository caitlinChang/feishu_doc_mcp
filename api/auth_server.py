from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import requests
import webbrowser
from api import config

APP_ID = config.APP_ID
APP_SECRET = config.APP_SECRET
REDIRECT_URI = config.REDIRECT_URI

app = FastAPI()

# Configuration from your Feishu app
APP_ID = config.APP_ID
APP_SECRET = config.APP_SECRET
REDIRECT_URI = config.REDIRECT_URI

@app.get("/authorize")
async def authorize():
    """
    Redirects the user to Feishu's authorization page.
    """
    auth_url = (
        f"https://open.feishu.cn/open-apis/authen/v1/authorize"
        f"?app_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=docx:document:readonly"
    )
    return RedirectResponse(url=auth_url)

@app.get("/callback")
async def callback(request: Request):
    """
    Handles the callback from Feishu after user authorization.
    """
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found.")

    # Exchange authorization code for user_access_token
    url = "https://open.feishu.cn/open-apis/authen/v1/access_token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 0:
            token_data = data.get("data", {})
            refresh_token = token_data.get("refresh_token")
            
            # Save the refresh_token for later use
            with open("refresh_token.txt", "w") as f:
                f.write(refresh_token)
            
            # Return the success HTML page
            with open("auth_success.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        else:
            error_message = f"Failed to get access token: {data.get('msg')}"
            return HTMLResponse(content=f"<h1>Error</h1><p>{error_message}</p>", status_code=400)
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network request failed: {e}")

if __name__ == "__main__":
    print("Starting authentication server...")
    print(f"Please open your browser and go to http://127.0.0.1:8000/authorize")
    uvicorn.run(app, host="127.0.0.1", port=8000)