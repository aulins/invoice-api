import os
from fastapi import Header, HTTPException

EXPECTED_KEY = os.getenv("API_KEY", "demo_merchant_key")

async def require_api_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or x_api_key != EXPECTED_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
