from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional, List
from functools import lru_cache
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import base64

load_dotenv()

# Enable CORS (for frontend connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (update in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

# Step 1: Reconstruct credentials.json from base64 env var
creds_b64 = os.getenv("GOOGLE_CREDS_BASE64")
if creds_b64:
    try:
        with open("credentials.json", "wb") as f:
            f.write(base64.b64decode(creds_b64))
    except Exception as e:
        print(f"⚠️ Failed to decode and write credentials.json: {e}")
else:
    print("⚠️ GOOGLE_CREDS_BASE64 env var not set — credentials.json will be missing")

# Config (same as your Streamlit app)
class AppConfig:
    CREDENTIALS_FILE = "credentials.json"
    SHEET_KEY = os.getenv("SHEET_KEY")  # From .env or Render Environment tab

config = AppConfig()

# --- Data Loading ---
@lru_cache
def get_gsheet_client():
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(config.CREDENTIALS_FILE, scope)
    return gspread.authorize(creds)


@lru_cache
def load_data():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(config.SHEET_KEY)
        operations = pd.DataFrame(sheet.worksheet("operations").get_all_records())
        operations["Date"] = pd.to_datetime(operations["Date"])
        return operations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data error: {str(e)}")

# --- API Endpoints ---
@app.get("/api/data")
async def get_data():
    data = load_data()
    return data.to_dict(orient="records")

# --- Authentication ---
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("ADMIN_USERNAME", "admin")
    correct_password = os.getenv("ADMIN_PASSWORD", "1234")
    if not (credentials.username == correct_username and credentials.password == correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/api/login")
async def login(username: str = Depends(authenticate)):
    return {"status": "success", "user": username}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
