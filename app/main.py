from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import date, datetime, timedelta
import os

from .auth import get_current_merchant
from .models import CreateInvoice, Item, Charges
from .database import get_db, engine, Base
from .db_models import Merchant, Invoice, APIKey, UsageLog, hash_key, gen_id
# from .middleware import log_request_middleware  # Skip dulu untuk fix error

# Create tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not create tables: {e}")

app = FastAPI(
    title="UMKM Invoice API - Multi-tenant",
    version="4.0.0",
    description="Multi-tenant invoice API with usage tracking & analytics"
)

# Add middleware (skip dulu untuk fix error)
# app.middleware("http")(log_request_middleware)

# CORS configuration (untuk frontend nanti)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: ganti dengan domain spesifik
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"
DB = {}  # In-memory fallback


# ==================== ROOT & LANDING PAGE ====================

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """
    Landing page - Marketing & onboarding
    """
    html = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Invoice API untuk UMKM Indonesia</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
            
            /* Hero */
            .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 80px 0; text-align: center; }
            .hero h1 { font-size: 48px; margin-bottom: 20px; }
            .hero p { font-size: 20px; margin-bottom: 30px; }
            .cta-button { display: inline-block; background: white; color: #667eea; padding: 15px 40px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 18px; transition: transform 0.3s; }
            .cta-button:hover { transform: scale(1.05); }
            
            /* Features */
            .features { padding: 80px 0; background: #f9f9f9; }
            .features h2 { text-align: center; font-size: 36px; margin-bottom: 50px; }
            .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }
            .feature-card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .feature-card h3 { color: #667eea; margin-bottom: 15px; }
            
            /* Pricing */
            .pricing { padding: 80px 0; }
            .pricing h2 { text-align: center; font-size: 36px; margin-bottom: 50px; }
            .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 30px; max-width: 1000px; margin: 0 auto; }
            .pricing-card { border: 2px solid #e0e0e0; border-radius: 10px; padding: 30px; text-align: center; transition: transform 0.3s; }
            .pricing-card:hover { transform: translateY(-10px); border-color: #667eea; }
            .pricing-card.featured { border-color: #667eea; box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3); }
            .plan-name { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
            .plan-price { font-size: 36px; color: #667eea; margin-bottom: 20px; }
            .plan-features { list-style: none; margin-bottom: 30px; text-align: left; }
            .plan-features li { padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
            
            /* CTA */
            .cta-section { background: #667eea; color: white; padding: 80px 0; text-align: center; }
            .cta-section h2 { font-size: 36px; margin-bottom: 20px; }
            
            /* Footer */
            footer { background: #333; color: white; padding: 40px 0; text-align: center; }
            footer a { color: #667eea; text-decoration: none; }
        </style>
    </head>
    <body>
        <!-- Hero Section -->
        <section class="hero">
            <div class="container">
                <h1>Invoice API untuk UMKM Indonesia</h1>
                <p>Generate invoice profesional dalam hitungan detik. Simple, cepat, dan terpercaya.</p>
                <a href="/v1/merchants/register?name=Your+Business&email=your@email.com&plan=free" class="cta-button">Mulai Gratis</a>
                <p style="margin-top: 20px; font-size: 14px;">✓ Gratis 10 invoice/bulan • ✓ Tanpa kartu kredit • ✓ Setup 2 menit</p>
            </div>
        </section>
        
        <!-- Features Section -->
        <section class="features">
            <div class="container">
                <h2>Kenapa Pilih Invoice API?</h2>
                <div class="feature-grid">
                    <div class="feature-card">
                        <h3>⚡ Super Cepat</h3>
                        <p>Generate invoice dalam milliseconds. API response time rata-rata < 100ms.</p>
                    </div>
                    <div class="feature-card">
                        <h3>💯 Akurat</h3>
                        <p>Perhitungan pajak otomatis (PPN 11%), diskon, biaya kirim, dan rounding.</p>
                    </div>
                    <div class="feature-card">
                        <h3>🔒 Aman</h3>
                        <p>Data terisolasi per merchant. API key authentication dengan encryption.</p>
                    </div>
                    <div class="feature-card">
                        <h3>📊 Analytics</h3>
                        <p>Track usage, quota, dan performance metrics real-time.</p>
                    </div>
                    <div class="feature-card">
                        <h3>🎨 Customizable</h3>
                        <p>HTML invoice siap print/PDF. Template yang bisa disesuaikan.</p>
                    </div>
                    <div class="feature-card">
                        <h3>🚀 Scalable</h3>
                        <p>Dari 10 invoice/bulan sampai unlimited. Upgrade kapan saja.</p>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- Pricing Section -->
        <section class="pricing">
            <div class="container">
                <h2>Harga yang Transparan</h2>
                <div class="pricing-grid">
                    <div class="pricing-card">
                        <div class="plan-name">Free</div>
                        <div class="plan-price">Rp 0</div>
                        <ul class="plan-features">
                            <li>✓ 10 invoice/bulan</li>
                            <li>✓ API documentation</li>
                            <li>✓ Email support</li>
                            <li>✓ Basic analytics</li>
                        </ul>
                        <a href="/v1/merchants/register?plan=free" class="cta-button">Daftar Gratis</a>
                    </div>
                    <div class="pricing-card featured">
                        <div class="plan-name">Starter</div>
                        <div class="plan-price">Rp 99K<span style="font-size:14px">/bulan</span></div>
                        <ul class="plan-features">
                            <li>✓ 100 invoice/bulan</li>
                            <li>✓ Priority support</li>
                            <li>✓ Advanced analytics</li>
                            <li>✓ API key management</li>
                        </ul>
                        <a href="/v1/merchants/me/upgrade?new_plan=starter" class="cta-button">Pilih Starter</a>
                    </div>
                    <div class="pricing-card">
                        <div class="plan-name">Pro</div>
                        <div class="plan-price">Rp 499K<span style="font-size:14px">/bulan</span></div>
                        <ul class="plan-features">
                            <li>✓ 1000 invoice/bulan</li>
                            <li>✓ 24/7 support</li>
                            <li>✓ Custom branding</li>
                            <li>✓ Webhook integration</li>
                        </ul>
                        <a href="/v1/merchants/me/upgrade?new_plan=pro" class="cta-button">Pilih Pro</a>
                    </div>
                </div>
                <p style="text-align:center; margin-top:30px; color:#666;">
                    Butuh lebih dari 1000 invoice/bulan? <a href="mailto:support@invoiceapi.com" style="color:#667eea;">Hubungi kami</a> untuk Enterprise plan.
                </p>
            </div>
        </section>
        
        <!-- CTA Section -->
        <section class="cta-section">
            <div class="container">
                <h2>Siap untuk Mulai?</h2>
                <p style="font-size:18px; margin-bottom:30px;">Daftar sekarang dan dapatkan 10 invoice gratis!</p>
                <a href="/docs" class="cta-button">Lihat Dokumentasi</a>
                <a href="/v1/merchants/register?name=Your+Business&email=your@email.com&plan=free" class="cta-button" style="margin-left:20px;">Daftar Sekarang</a>
            </div>
        </section>
        
        <!-- Footer -->
        <footer>
            <div class="container">
                <p>© 2026 Invoice API Indonesia. Built with ❤️ for UMKM.</p>
                <p style="margin-top:10px;">
                    <a href="/docs">API Docs</a> • 
                    <a href="/v1/pricing">Pricing</a> • 
                    <a href="mailto:support@invoiceapi.com">Support</a>
                </p>
            </div>
        </footer>
    </body>
    </html>
    """
    return html


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
    request: Request,
    payload: CreateInvoice,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Create new invoice
    
    MULTI-TENANT: Each merchant gets their own invoice numbering & data
    
    Requires: X-API-Key header
    """
    
    # Set merchant_id in request state (for middleware logging)
    request.state.merchant_id = merchant.id
    
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


# ==================== USAGE & ANALYTICS ====================

@app.get("/v1/merchants/me/usage")
async def get_usage_stats(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Get current usage statistics
    
    Returns:
    - Quota info (used, limit, remaining)
    - Usage percentage
    - Days until quota reset
    """
    
    # Calculate quota percentage
    percentage = round((merchant.quota_used / merchant.quota_limit) * 100, 1) if merchant.quota_limit > 0 else 0
    
    # Calculate days until reset (assume reset on 1st of month)
    today = datetime.utcnow()
    if today.month == 12:
        next_reset = datetime(today.year + 1, 1, 1)
    else:
        next_reset = datetime(today.year, today.month + 1, 1)
    days_until_reset = (next_reset - today).days
    
    return {
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "plan": merchant.plan,
        "quota": {
            "limit": merchant.quota_limit,
            "used": merchant.quota_used,
            "remaining": merchant.quota_limit - merchant.quota_used,
            "percentage": percentage
        },
        "status": {
            "ok": merchant.quota_used < merchant.quota_limit,
            "warning": percentage >= 80,
            "exceeded": merchant.quota_used >= merchant.quota_limit
        },
        "reset": {
            "days_remaining": days_until_reset,
            "next_reset_date": next_reset.date().isoformat()
        }
    }


@app.get("/v1/merchants/me/analytics")
async def get_analytics(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get usage analytics
    
    Returns:
    - Total API calls
    - Calls by endpoint
    - Average response time
    - Peak usage times
    """
    
    # Date range
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total API calls
    total_calls = db.query(func.count(UsageLog.id)).filter(
        UsageLog.merchant_id == merchant.id,
        UsageLog.created_at >= start_date
    ).scalar() or 0
    
    # Calls by endpoint
    endpoint_stats = db.query(
        UsageLog.endpoint,
        func.count(UsageLog.id).label("count")
    ).filter(
        UsageLog.merchant_id == merchant.id,
        UsageLog.created_at >= start_date
    ).group_by(UsageLog.endpoint).all()
    
    # Average response time
    avg_response_time = db.query(
        func.avg(UsageLog.response_time_ms)
    ).filter(
        UsageLog.merchant_id == merchant.id,
        UsageLog.created_at >= start_date
    ).scalar() or 0
    
    # Total invoices created
    total_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.merchant_id == merchant.id,
        Invoice.created_at >= start_date
    ).scalar() or 0
    
    return {
        "period": {
            "days": days,
            "start_date": start_date.date().isoformat(),
            "end_date": datetime.utcnow().date().isoformat()
        },
        "summary": {
            "total_api_calls": total_calls,
            "total_invoices_created": total_invoices,
            "average_response_time_ms": round(avg_response_time, 2)
        },
        "by_endpoint": [
            {
                "endpoint": stat.endpoint,
                "calls": stat.count
            }
            for stat in endpoint_stats
        ]
    }


# ==================== PRICING & SUBSCRIPTION ====================

# Pricing configuration
PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "quota": 10,
        "features": ["10 invoices/month", "Basic support", "Email notifications"]
    },
    "starter": {
        "name": "Starter",
        "price": 99000,  # Rp 99.000
        "quota": 100,
        "features": ["100 invoices/month", "Priority support", "Email notifications", "API analytics"]
    },
    "pro": {
        "name": "Pro",
        "price": 499000,  # Rp 499.000
        "quota": 1000,
        "features": ["1000 invoices/month", "24/7 support", "Custom branding", "Advanced analytics", "Webhook integration"]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 2499000,  # Rp 2.499.000
        "quota": 999999,
        "features": ["Unlimited invoices", "Dedicated support", "Custom features", "SLA guarantee", "Priority feature requests"]
    }
}


@app.get("/v1/pricing")
async def get_pricing():
    """
    PUBLIC ENDPOINT - Get pricing plans
    
    Returns all available plans with features & pricing
    """
    return {
        "currency": "IDR",
        "plans": [
            {
                "id": plan_id,
                **plan_details
            }
            for plan_id, plan_details in PLANS.items()
        ]
    }


@app.post("/v1/merchants/me/upgrade")
async def request_upgrade(
    new_plan: str = Query(..., description="Plan to upgrade to: starter, pro, enterprise"),
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Request plan upgrade
    
    MANUAL PAYMENT (MVP):
    Returns payment instructions (bank transfer)
    
    AUTOMATIC PAYMENT (Production):
    Integrate with Midtrans/Xendit for automatic payment
    """
    
    # Validate plan
    if new_plan not in PLANS or new_plan == "free":
        raise HTTPException(400, f"Invalid plan. Available plans: starter, pro, enterprise")
    
    # Check if already on this plan
    if merchant.plan == new_plan:
        raise HTTPException(400, f"You are already on the '{new_plan}' plan")
    
    plan_details = PLANS[new_plan]
    
    # For MVP: Return manual payment instructions
    # Production: Create payment link via Midtrans/Xendit
    
    return {
        "upgrade_request": {
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "current_plan": merchant.plan,
            "requested_plan": new_plan,
            "price": plan_details["price"],
            "currency": "IDR"
        },
        "payment_instructions": {
            "method": "Bank Transfer (Manual)",
            "bank": "BCA",
            "account_number": "1234567890",
            "account_name": "Invoice API Indonesia",
            "amount": plan_details["price"],
            "reference": f"UPGRADE-{merchant.id}-{new_plan.upper()}",
            "note": "Include reference in transfer notes"
        },
        "next_steps": [
            f"1. Transfer Rp {plan_details['price']:,} to the account above",
            "2. Include reference code in transfer notes",
            "3. Send proof of payment to support@invoiceapi.com",
            "4. We will upgrade your account within 1 business day",
            "5. You will receive confirmation email"
        ],
        "note": "For automatic payment integration (coming soon), contact support@invoiceapi.com"
    }


@app.post("/v1/merchants/me/confirm-upgrade")
async def confirm_upgrade(
    new_plan: str = Query(..., description="Plan to upgrade to"),
    payment_proof: str = Query(..., description="Payment reference or transaction ID"),
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Confirm manual payment (ADMIN will approve)
    
    In production: This will be replaced by webhook from payment gateway
    """
    
    if new_plan not in PLANS or new_plan == "free":
        raise HTTPException(400, "Invalid plan")
    
    return {
        "success": True,
        "message": "Upgrade request received",
        "merchant_id": merchant.id,
        "requested_plan": new_plan,
        "payment_reference": payment_proof,
        "status": "pending_verification",
        "note": "Admin will verify your payment and upgrade your account within 1 business day"
    }


@app.post("/admin/approve-upgrade/{merchant_id}", include_in_schema=False)
async def admin_approve_upgrade(
    merchant_id: str,
    new_plan: str = Query(..., description="Plan to upgrade to"),
    admin_key: str = Query(..., description="Admin API key"),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY - Approve upgrade and change merchant plan
    
    This endpoint will be called after verifying payment
    """
    
    ADMIN_KEY = os.getenv("ADMIN_KEY", "admin_secret_key_change_me")
    if admin_key != ADMIN_KEY:
        raise HTTPException(403, "Unauthorized")
    
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(404, "Merchant not found")
    
    if new_plan not in PLANS:
        raise HTTPException(400, "Invalid plan")
    
    old_plan = merchant.plan
    old_quota = merchant.quota_limit
    
    # Update merchant
    merchant.plan = new_plan
    merchant.quota_limit = PLANS[new_plan]["quota"]
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Merchant upgraded from {old_plan} to {new_plan}",
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "upgrade": {
            "old_plan": old_plan,
            "new_plan": new_plan,
            "old_quota": old_quota,
            "new_quota": merchant.quota_limit
        }
    }


# ==================== ADMIN ENDPOINTS ====================

@app.post("/admin/reset-quota/{merchant_id}", include_in_schema=False)
async def admin_reset_quota(
    merchant_id: str,
    admin_key: str = Query(..., description="Admin API key"),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY - Reset merchant quota
    
    Use case: Monthly quota reset or manual adjustment
    """
    
    # Simple admin auth (production: use proper admin authentication)
    ADMIN_KEY = os.getenv("ADMIN_KEY", "admin_secret_key_change_me")
    if admin_key != ADMIN_KEY:
        raise HTTPException(403, "Unauthorized")
    
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(404, "Merchant not found")
    
    old_used = merchant.quota_used
    merchant.quota_used = 0
    db.commit()
    
    return {
        "success": True,
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "quota_reset": {
            "old_used": old_used,
            "new_used": 0,
            "limit": merchant.quota_limit
        }
    }


@app.post("/admin/reset-all-quotas", include_in_schema=False)
async def admin_reset_all_quotas(
    admin_key: str = Query(..., description="Admin API key"),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY - Reset ALL merchants quota
    
    Use case: Monthly reset (run via cron job on 1st of month)
    """
    
    ADMIN_KEY = os.getenv("ADMIN_KEY", "admin_secret_key_change_me")
    if admin_key != ADMIN_KEY:
        raise HTTPException(403, "Unauthorized")
    
    merchants = db.query(Merchant).filter(Merchant.is_active == True).all()
    
    reset_count = 0
    for merchant in merchants:
        if merchant.quota_used > 0:
            merchant.quota_used = 0
            reset_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Reset quota for {reset_count} merchants",
        "total_merchants": len(merchants),
        "reset_date": datetime.utcnow().date().isoformat()
    }


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