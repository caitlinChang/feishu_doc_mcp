import requests
import argparse
from urllib.parse import urlparse, parse_qs
from api import config

APP_ID = config.APP_ID
APP_SECRET = config.APP_SECRET
BASE_URL = config.BASE_URL

def get_token_from_url(redirect_url: str):
    """
    Parses the redirect URL to get the 'code', then exchanges it for a refresh token.
    """
    try:
        # Parse the URL and extract the 'code' parameter
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        code = query_params.get('code', [None])[0]

        if not code:
            print("❌ Error: Could not find 'code' in the provided URL.")
            print("Please make sure you have copied the full URL after redirection.")
            return

        print(f"✅ Successfully extracted authorization code: {code[:10]}...")

        # Exchange authorization code for user_access_token
        url = f"{BASE_URL}/authen/v1/access_token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "app_id": APP_ID,
            "app_secret": APP_SECRET
        }
        
        print("🔄 Exchanging code for refresh token...")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 0:
            token_data = data.get("data", {})
            refresh_token = token_data.get("refresh_token")
            
            if not refresh_token:
                print("❌ Error: API response did not contain a refresh_token.")
                print(f"Response: {data}")
                return

            # Save the refresh_token for later use
            with open("refresh_token.txt", "w") as f:
                f.write(refresh_token)
            
            print("🎉 Success! `refresh_token.txt` has been created.")
            print("You can now start the main server.")
        else:
            print(f"❌ Error: Failed to get access token: {data.get('msg')}")
            print(f"Full error response: {data}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error: An error occurred while communicating with the Feishu API: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Feishu refresh token from a redirect URL.")
    parser.add_argument("url", type=str, help="The full redirect URL from Feishu after authorization.")
    args = parser.parse_args()
    
    get_token_from_url(args.url)