from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime
import os

from .auth import get_current_merchant
from .models import CreateInvoice, Item, Charges
from .database import get_db, engine, Base
from .db_models import Merchant, Invoice, APIKey, hash_key, gen_id

# Create tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not create tables: {e}")

app = FastAPI(
    title="UMKM Invoice API - Multi-tenant",
    version="3.0.0",
    description="Multi-tenant invoice API with database persistence"
)

USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"
DB = {}  # In-memory fallback


# ==================== HELPER FUNCTIONS ====================

def rupiah(n: float) -> str:
    """Format angka ke format Rupiah"""
    try:
        return f"Rp {int(n):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


def calc_totals(items: list[Item], charges: Charges, discount_total: float):
    """Calculate invoice totals"""
    subtotal = sum(i.qty * i.unit_price - i.discount for i in items)
    tax_total = 0.0
    for i in items:
        base = (i.unit_price * i.qty - i.discount)
        if i.is_tax_inclusive:
            base_wo_tax = base / (1 + i.tax_rate) if i.tax_rate > 0 else base
            tax_total += base - base_wo_tax
        else:
            tax_total += base * i.tax_rate
    grand = subtotal + tax_total + charges.shipping + charges.service + charges.rounding - discount_total
    return {
        "subtotal": round(subtotal),
        "tax_total": round(tax_total),
        "grand_total": round(grand)
    }


def next_number_db(merchant_id: str, db: Session):
    """Generate invoice number per merchant (persistent)"""
    today = date.today()
    year, month = today.year, today.month
    
    count = db.query(Invoice).filter(
        Invoice.merchant_id == merchant_id,
        Invoice.number.like(f"INV/{year}/{month:02d}/%")
    ).count()
    
    seq = count + 1
    return f"INV/{year}/{month:02d}/{seq:04d}"


# ==================== HEALTH CHECK ====================

@app.get("/healthz")
async def healthz(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        if USE_DATABASE:
            db.execute(text("SELECT 1"))
            db_status = "connected"
        else:
            db_status = "in-memory mode"
        
        return {
            "ok": True,
            "version": "3.0.0",
            "database": db_status,
            "mode": "database" if USE_DATABASE else "legacy",
            "multi_tenant": USE_DATABASE
        }
    except Exception as e:
        return {
            "ok": False,
            "database": "error",
            "error": str(e)
        }


# ==================== MERCHANT MANAGEMENT ====================

@app.post("/v1/merchants/register")
async def register_merchant(
    name: str = Query(..., description="Merchant name"),
    email: str = Query(..., description="Merchant email (must be unique)"),
    plan: str = Query("free", description="Subscription plan: free, starter, pro"),
    db: Session = Depends(get_db)
):
    """
    PUBLIC ENDPOINT - Register new merchant
    
    HOW IT WORKS:
    1. User provide: name, email, plan
    2. System check: email must be unique
    3. System create: merchant + API key
    4. Response: merchant info + API key (SHOWN ONCE!)
    
    Example:
        POST /v1/merchants/register?name=Toko+ABC&email=toko@example.com&plan=free
    
    Returns:
        - merchant_id: Unique merchant ID
        - api_key: SECRET API KEY (save this!)
        - quota_limit: Invoice quota per month
    """
    
    # Validate email format
    if "@" not in email or "." not in email:
        raise HTTPException(400, "Invalid email format")
    
    # Check if email already exists
    existing = db.query(Merchant).filter(Merchant.email == email).first()
    if existing:
        raise HTTPException(
            400,
            f"Email '{email}' is already registered. Please use a different email or login with your existing API key."
        )
    
    # Determine quota based on plan
    quota_map = {
        "free": 10,
        "starter": 100,
        "pro": 1000,
        "enterprise": 999999
    }
    quota = quota_map.get(plan, 10)
    
    # Create merchant
    merchant = Merchant(
        name=name,
        email=email,
        plan=plan,
        quota_limit=quota,
        quota_used=0
    )
    db.add(merchant)
    db.flush()
    
    # Generate unique API key
    api_key_value = f"inv_live_{os.urandom(16).hex()}"
    key_hash_value = hash_key(api_key_value)
    
    api_key = APIKey(
        merchant_id=merchant.id,
        key_hash=key_hash_value,
        key_prefix=api_key_value[:15],
        name="Default API Key"
    )
    db.add(api_key)
    db.commit()
    
    return {
        "success": True,
        "message": "Merchant registered successfully!",
        "merchant_id": merchant.id,
        "name": merchant.name,
        "email": merchant.email,
        "plan": merchant.plan,
        "quota_limit": merchant.quota_limit,
        "api_key": api_key_value,
        "warning": "⚠️  SAVE THIS API KEY! It will not be shown again for security reasons.",
        "next_steps": [
            "1. Save your API key in a secure location",
            "2. Add header 'X-API-Key: YOUR_API_KEY' to all API requests",
            "3. Read documentation: /docs",
            "4. Create your first invoice: POST /v1/invoices"
        ]
    }


@app.get("/v1/merchants/me")
async def get_merchant_info(
    merchant: Merchant = Depends(get_current_merchant)
):
    """
    Get current merchant information
    
    Requires: X-API-Key header
    
    Returns merchant profile + quota usage
    """
    return {
        "id": merchant.id,
        "name": merchant.name,
        "email": merchant.email,
        "plan": merchant.plan,
        "quota": {
            "limit": merchant.quota_limit,
            "used": merchant.quota_used,
            "remaining": merchant.quota_limit - merchant.quota_used,
            "percentage": round((merchant.quota_used / merchant.quota_limit) * 100, 1) if merchant.quota_limit > 0 else 0
        },
        "is_active": merchant.is_active,
        "created_at": merchant.created_at.isoformat()
    }


# ==================== API KEY MANAGEMENT ====================

@app.get("/v1/merchants/me/api-keys")
async def list_api_keys(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    List all API keys for current merchant
    
    Shows: key prefix (not full key!), status, last used
    """
    keys = db.query(APIKey).filter(
        APIKey.merchant_id == merchant.id
    ).order_by(APIKey.created_at.desc()).all()
    
    return {
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "total_keys": len(keys),
        "keys": [
            {
                "id": key.id,
                "prefix": key.key_prefix + "...",  # Only show prefix
                "name": key.name,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat(),
                "last_used": key.last_used.isoformat() if key.last_used else "Never used"
            }
            for key in keys
        ]
    }


@app.post("/v1/merchants/me/api-keys")
async def create_api_key(
    name: str = Query(..., description="Name/label for this API key"),
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Create new API key for current merchant
    
    Use case: Rotate keys, separate keys for different apps
    
    Returns: NEW API KEY (shown once!)
    """
    
    # Generate new key
    api_key_value = f"inv_live_{os.urandom(16).hex()}"
    key_hash_value = hash_key(api_key_value)
    
    api_key = APIKey(
        merchant_id=merchant.id,
        key_hash=key_hash_value,
        key_prefix=api_key_value[:15],
        name=name
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return {
        "success": True,
        "message": "New API key created successfully!",
        "key_id": api_key.id,
        "api_key": api_key_value,
        "name": api_key.name,
        "created_at": api_key.created_at.isoformat(),
        "warning": "⚠️  SAVE THIS API KEY! It will not be shown again."
    }


@app.delete("/v1/merchants/me/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Revoke/deactivate an API key
    
    Use case: Compromised key, rotate keys
    
    Note: Key is not deleted (for audit trail), just deactivated
    """
    
    # Find key
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.merchant_id == merchant.id
    ).first()
    
    if not api_key:
        raise HTTPException(404, "API key not found")
    
    if not api_key.is_active:
        raise HTTPException(400, "API key is already revoked")
    
    # Deactivate
    api_key.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": f"API key '{api_key.name}' has been revoked successfully",
        "key_id": key_id,
        "key_prefix": api_key.key_prefix + "..."
    }


# ==================== INVOICE ENDPOINTS ====================

@app.post("/v1/invoices")
async def create_invoice(
    payload: CreateInvoice,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Create new invoice
    
    MULTI-TENANT: Each merchant gets their own invoice numbering & data
    
    Requires: X-API-Key header
    """
    
    # Check quota
    if merchant.quota_used >= merchant.quota_limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Quota exceeded",
                "message": f"Your '{merchant.plan}' plan allows {merchant.quota_limit} invoices per month",
                "quota_used": merchant.quota_used,
                "quota_limit": merchant.quota_limit,
                "suggestion": "Upgrade your plan to create more invoices",
                "upgrade_url": "/v1/merchants/me/upgrade"
            }
        )
    
    # Generate invoice
    inv_id = gen_id("inv")
    number = next_number_db(merchant.id, db)  # ✅ Per merchant!
    totals = calc_totals(payload.items, payload.charges, payload.discount_total)
    
    payload_json = payload.model_dump(mode="json")
    
    invoice = Invoice(
        id=inv_id,
        merchant_id=merchant.id,  # ✅ Auto dari auth!
        number=number,
        status="issued",
        payload=payload_json,
        subtotal=totals["subtotal"],
        tax_total=totals["tax_total"],
        grand_total=totals["grand_total"]
    )
    
    db.add(invoice)
    
    # FIX: Re-query merchant from current session to ensure it's tracked
    merchant_in_session = db.query(Merchant).filter(Merchant.id == merchant.id).first()
    merchant_in_session.quota_used += 1
    
    db.commit()
    db.refresh(merchant_in_session)
    
    return {
        "id": inv_id,
        "number": number,
        "status": "issued",
        "merchant_id": merchant.id,
        "totals": totals,
        "quota_remaining": merchant_in_session.quota_limit - merchant_in_session.quota_used,
        "links": {
            "self": f"/v1/invoices/{inv_id}",
            "html": f"/v1/invoices/{inv_id}/html"
        }
    }


@app.get("/v1/invoices")
async def list_invoices(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
    limit: int = Query(50, description="Max results to return"),
    offset: int = Query(0, description="Pagination offset")
):
    """
    List invoices for current merchant
    
    DATA ISOLATION: Only shows invoices belonging to current merchant
    """
    
    invoices = db.query(Invoice).filter(
        Invoice.merchant_id == merchant.id  # ✅ Filter by merchant!
    ).order_by(Invoice.created_at.desc()).limit(limit).offset(offset).all()
    
    total = db.query(Invoice).filter(
        Invoice.merchant_id == merchant.id
    ).count()
    
    return {
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "total": total,
        "limit": limit,
        "offset": offset,
        "invoices": [
            {
                "id": inv.id,
                "number": inv.number,
                "status": inv.status,
                "customer": inv.payload.get("customer", {}),
                "grand_total": inv.grand_total,
                "created_at": inv.created_at.isoformat()
            }
            for inv in invoices
        ]
    }


@app.get("/v1/invoices/{inv_id}")
async def get_invoice(
    inv_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Get invoice detail
    
    DATA ISOLATION: Only shows if invoice belongs to current merchant
    """
    
    invoice = db.query(Invoice).filter(
        Invoice.id == inv_id,
        Invoice.merchant_id == merchant.id  # ✅ Security check!
    ).first()
    
    if not invoice:
        raise HTTPException(
            404,
            "Invoice not found or you don't have permission to access it"
        )
    
    return {
        "id": invoice.id,
        "number": invoice.number,
        "status": invoice.status,
        "merchant_id": invoice.merchant_id,
        "payload": invoice.payload,
        "totals": {
            "subtotal": invoice.subtotal,
            "tax_total": invoice.tax_total,
            "grand_total": invoice.grand_total
        },
        "created_at": invoice.created_at.isoformat()
    }


@app.get("/v1/invoices/{inv_id}/html", response_class=HTMLResponse)
async def invoice_html(
    inv_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Render invoice as HTML (printable)
    
    DATA ISOLATION: Only renders if invoice belongs to current merchant
    """
    
    invoice = db.query(Invoice).filter(
        Invoice.id == inv_id,
        Invoice.merchant_id == merchant.id  # ✅ Security check!
    ).first()
    
    if not invoice:
        raise HTTPException(
            404,
            "Invoice not found or you don't have permission to access it"
        )
    
    d = {
        "id": invoice.id,
        "number": invoice.number,
        "status": invoice.status,
        "payload": invoice.payload,
        "totals": {
            "subtotal": invoice.subtotal,
            "tax_total": invoice.tax_total,
            "grand_total": invoice.grand_total
        }
    }
    
    p = d["payload"]
    rows = ""
    
    for i in p.get("items", []):
        base = i.get("qty", 0) * i.get("unit_price", 0) - i.get("discount", 0)
        if i.get("is_tax_inclusive"):
            tax = base - (base / (1 + i.get("tax_rate", 0)))
            line_total = base
        else:
            tax = base * i.get("tax_rate", 0)
            line_total = base + tax
        
        rows += (
            "<tr>"
            f"<td>{i.get('name','')}</td>"
            f"<td style='text-align:right'>{i.get('qty',0)}</td>"
            f"<td style='text-align:right'>{rupiah(i.get('unit_price',0))}</td>"
            f"<td style='text-align:right'>{rupiah(i.get('discount',0))}</td>"
            f"<td style='text-align:right'>{rupiah(int(tax))}</td>"
            f"<td style='text-align:right'>{rupiah(int(line_total))}</td>"
            "</tr>"
        )
    
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{d['number']}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .header {{ display:flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
    .merchant {{ font-size: 12px; color: #666; }}
    .box {{ border:1px solid #ddd; padding:12px; border-radius:8px; }}
    table {{ width:100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border-bottom:1px solid #eee; padding:8px; text-align:left; }}
    th {{ background:#fafafa; }}
    .right {{ text-align:right; }}
    .totals {{ margin-top: 20px; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h2>INVOICE</h2>
      <div>No: {d['number']}</div>
      <div class="merchant">Merchant: {merchant.name}</div>
    </div>
    <div style="padding:4px 8px;border-radius:6px;background:#eef;display:inline-block;">{d['status'].upper()}</div>
  </div>

  <div class="box" style="margin-top:16px">
    <strong>Bill To</strong>
    <div>{p.get('customer',{}).get('name','')}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Item</th><th class="right">Qty</th><th class="right">Harga</th>
        <th class="right">Diskon</th><th class="right">Pajak</th><th class="right">Subtotal</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <div class="totals">
    <table style="width:300px; margin-left:auto;">
      <tr><td class="right">Subtotal:</td><td class="right">{rupiah(d['totals']['subtotal'])}</td></tr>
      <tr><td class="right">Pajak:</td><td class="right">{rupiah(d['totals']['tax_total'])}</td></tr>
      <tr style="font-weight:bold; background:#f5f5f5;">
        <td class="right">TOTAL:</td>
        <td class="right">{rupiah(d['totals']['grand_total'])}</td>
      </tr>
    </table>
  </div>
</body>
</html>"""
    
    return HTMLResponse(content=html, media_type="text/html")


# ==================== ADMIN SETUP (Development Only) ====================

@app.post("/admin/setup", include_in_schema=False)
async def admin_setup(db: Session = Depends(get_db)):
    """
    DEVELOPMENT ONLY - Setup default merchant
    
    Use /v1/merchants/register for production!
    """
    
    existing = db.query(Merchant).filter(Merchant.id == "mrc_default").first()
    if existing:
        return {
            "message": "Already setup",
            "merchant": existing.name,
            "note": "Use /v1/merchants/register to create new merchants"
        }
    
    merchant = Merchant(
        id="mrc_default",
        name="Default Merchant",
        email="demo@example.com",
        plan="free",
        quota_limit=10
    )
    db.add(merchant)
    db.flush()
    
    api_key_value = f"inv_test_{os.urandom(12).hex()}"
    key_hash_value = hash_key(api_key_value)
    
    api_key = APIKey(
        merchant_id=merchant.id,
        key_hash=key_hash_value,
        key_prefix=api_key_value[:12],
        name="Default API Key"
    )
    db.add(api_key)
    db.commit()
    
    return {
        "message": "Setup complete!",
        "merchant_id": merchant.id,
        "api_key": api_key_value,
        "note": "SAVE THIS API KEY!"
    }