"""
Middleware untuk track usage & analytics
"""
from fastapi import Request
from sqlalchemy.orm import Session
from datetime import datetime
import time

from .database import SessionLocal
from .db_models import UsageLog


async def log_request_middleware(request: Request, call_next):
    """
    Middleware untuk log setiap API request
    
    Tracks:
    - Endpoint yang diakses
    - HTTP method
    - Status code
    - Response time
    - User agent
    - IP address
    - Merchant ID (kalau authenticated)
    """
    
    # Skip logging untuk endpoints tertentu
    skip_paths = ["/healthz", "/docs", "/openapi.json", "/favicon.ico"]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return await call_next(request)
    
    # Start timer
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # Extract merchant_id dari request state (set by auth middleware)
    merchant_id = getattr(request.state, "merchant_id", None)
    
    # Log to database (async, non-blocking)
    try:
        db = SessionLocal()
        
        # Only log if merchant authenticated (has merchant_id)
        if merchant_id:
            usage_log = UsageLog(
                merchant_id=merchant_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                user_agent=request.headers.get("user-agent", ""),
                ip_address=request.client.host if request.client else ""
            )
            db.add(usage_log)
            db.commit()
        
        db.close()
    except Exception as e:
        # Don't fail request if logging fails
        print(f"Usage logging error: {e}")
    
    return response