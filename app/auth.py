"""
Authentication - support both old (env var) and new (database) methods
"""
import os
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

# Backward compatibility: still support env var for testing
LEGACY_API_KEY = os.getenv("API_KEY", "demo_merchant_key")


async def require_api_key_legacy(x_api_key: str | None = Header(default=None)):
    """
    LEGACY: Simple auth dengan env var
    Untuk backward compatibility - akan dihapus setelah migration
    """
    if not x_api_key or x_api_key != LEGACY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def get_current_merchant(
    x_api_key: str = Header(alias="X-API-Key"),
    db: Session = Depends(lambda: None)  # Will be injected properly
):
    """
    NEW: Database-based auth
    Returns merchant object if API key valid
    """
    # Import here to avoid circular dependency
    from app.database import get_db
    from app.db_models import APIKey, Merchant, hash_key
    
    # Get actual db session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        key_hash = hash_key(x_api_key)
        
        api_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Update last used
        api_key.last_used = datetime.utcnow()
        db.commit()
        
        # Get merchant
        merchant = db.query(Merchant).filter(
            Merchant.id == api_key.merchant_id,
            Merchant.is_active == True
        ).first()
        
        if not merchant:
            raise HTTPException(status_code=401, detail="Merchant inactive")
        
        return merchant
        
    finally:
        db.close()


# Alias untuk backward compatibility
require_api_key = require_api_key_legacy  # Default ke legacy mode dulu