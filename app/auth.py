"""
Authentication module - Multi-tenant support
"""
import os
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime


# ==================== DATABASE AUTH (Multi-tenant) ====================

async def get_current_merchant(
    x_api_key: str = Header(alias="X-API-Key"),
    db: Session = Depends(lambda: None)  # Will be injected properly by FastAPI
):
    """
    Get current merchant from API key in database.
    
    HOW IT WORKS:
    1. Extract API key dari header "X-API-Key"
    2. Hash API key (untuk keamanan)
    3. Cari di database table `api_keys`
    4. Kalau ketemu & active → return merchant object
    5. Kalau tidak → error 401
    
    Returns:
        Merchant object (from database)
    
    Raises:
        HTTPException 401: Invalid or inactive API key
    """
    from app.database import get_db
    from app.db_models import APIKey, Merchant, hash_key
    
    # Get database session
    db = next(get_db())
    
    try:
        # Hash API key untuk compare dengan database
        key_hash = hash_key(x_api_key)
        
        # Cari API key di database
        api_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key. Please check your API key or register at /v1/merchants/register"
            )
        
        # Update last used timestamp
        api_key.last_used = datetime.utcnow()
        db.commit()
        
        # Get merchant dari API key
        merchant = db.query(Merchant).filter(
            Merchant.id == api_key.merchant_id,
            Merchant.is_active == True
        ).first()
        
        if not merchant:
            raise HTTPException(
                status_code=401,
                detail="Merchant account is inactive. Please contact support."
            )
        
        return merchant
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Authentication error: {str(e)}"
        )
    finally:
        db.close()


# ==================== LEGACY AUTH (Backward compatibility) ====================

LEGACY_API_KEY = os.getenv("API_KEY", "demo_merchant_key")

async def require_api_key_legacy(x_api_key: str | None = Header(default=None)):
    """
    LEGACY: Simple auth dengan env var.
    Hanya untuk backward compatibility saat USE_DATABASE=false.
    AKAN DIHAPUS setelah full migration ke database mode.
    """
    if not x_api_key or x_api_key != LEGACY_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key (legacy mode)"
        )