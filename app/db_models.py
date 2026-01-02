"""
SQLAlchemy models - sesuai dengan struktur existing
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import uuid
import hashlib


def gen_id(prefix: str):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class Merchant(Base):
    """Merchant = customer yang pakai API kamu"""
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=lambda: gen_id("mrc"))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    
    # Subscription
    plan = Column(String(50), default="free")
    quota_limit = Column(Integer, default=10)  # invoices/month
    quota_used = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    api_keys = relationship("APIKey", back_populates="merchant")
    invoices = relationship("Invoice", back_populates="merchant")


class APIKey(Base):
    """API Keys per merchant"""
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: gen_id("key"))
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    
    key_hash = Column(String(255), nullable=False, unique=True)
    key_prefix = Column(String(20), nullable=False)  # untuk display
    name = Column(String(100), default="Default Key")
    
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    merchant = relationship("Merchant", back_populates="api_keys")


class Invoice(Base):
    """Invoice - simpan semua data"""
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=lambda: gen_id("inv"))
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    
    number = Column(String(100), nullable=False)
    status = Column(String(20), default="issued")
    
    # Simpan payload lengkap sebagai JSON (backward compatible!)
    payload = Column(JSON, nullable=False)
    
    # Totals untuk query cepat
    subtotal = Column(Integer, default=0)
    tax_total = Column(Integer, default=0)
    grand_total = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    merchant = relationship("Merchant", back_populates="invoices")


def hash_key(key: str) -> str:
    """Hash API key untuk storage"""
    return hashlib.sha256(key.encode()).hexdigest()