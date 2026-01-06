from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import os

from .auth import require_api_key, get_current_merchant
from .models import CreateInvoice, Item, Charges
from .database import get_db, engine, Base
from .db_models import Merchant, Invoice, APIKey, hash_key, gen_id

# Create tables (hanya untuk development, production pakai Alembic)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not create tables: {e}")

app = FastAPI(
    title="UMKM Invoice API",
    version="2.0.0",
    description="Multi-tenant invoice API with database"
)

# Feature flag: set USE_DATABASE=true di env untuk enable database mode
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

# In-memory fallback (untuk testing tanpa database)
DB = {}


def rupiah(n: float) -> str:
    try:
        return f"Rp {int(n):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


def calc_totals(items: list[Item], charges: Charges, discount_total: float):
    """Perhitungan yang sama seperti sebelumnya"""
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


def next_number_legacy():
    """Legacy numbering (in-memory)"""
    return f"INV/{date.today().year}/{date.today().month:02d}/{len(DB)+1:04d}"


def next_number_db(merchant_id: str, db: Session):
    """Database-based numbering (persistent per merchant)"""
    today = date.today()
    year, month = today.year, today.month
    
    # Count invoices untuk merchant ini di bulan ini
    count = db.query(Invoice).filter(
        Invoice.merchant_id == merchant_id,
        Invoice.number.like(f"INV/{year}/{month:02d}/%")
    ).count()
    
    seq = count + 1
    return f"INV/{year}/{month:02d}/{seq:04d}"


# ==================== HEALTH CHECK ====================

@app.get("/healthz")
async def healthz(db: Session = Depends(get_db)):
    """Health check"""
    try:
        if USE_DATABASE:
            db.execute("SELECT 1")
            db_status = "connected"
        else:
            db_status = "in-memory mode"
        
        return {
            "ok": True,
            "version": "2.0.0",
            "database": db_status,
            "mode": "database" if USE_DATABASE else "legacy"
        }
    except Exception as e:
        return {
            "ok": False,
            "database": "error",
            "error": str(e)
        }


@app.get("/debug/info", response_class=PlainTextResponse)
async def debug_info():
    mode = "DATABASE" if USE_DATABASE else "LEGACY (in-memory)"
    return f"OK: Running in {mode} mode"


# ==================== CREATE INVOICE ====================

@app.post("/v1/invoices")
async def create_invoice(
    payload: CreateInvoice,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Create invoice - works in both legacy and database mode
    """
    
    if USE_DATABASE:
        # DATABASE MODE - Multi-tenant (merchant sudah dari auth)
        
        # Check quota
        if merchant.quota_used >= merchant.quota_limit:
            raise HTTPException(
                429,
                f"Quota exceeded. Plan '{merchant.plan}' allows {merchant.quota_limit} invoices/month"
            )
        
        # Generate invoice
        inv_id = gen_id("inv")
        number = next_number_db(merchant.id, db)
        totals = calc_totals(payload.items, payload.charges, payload.discount_total)
        
        invoice = Invoice(
            id=inv_id,
            merchant_id=merchant.id,
            number=number,
            status="issued",
            payload=payload.model_dump(),
            subtotal=totals["subtotal"],
            tax_total=totals["tax_total"],
            grand_total=totals["grand_total"]
        )
        
        db.add(invoice)
        merchant.quota_used += 1
        db.commit()
        
    else:
        # LEGACY MODE - In-memory
        inv_id = f"inv_{gen_id('tmp')}"
        number = next_number_legacy()
        totals = calc_totals(payload.items, payload.charges, payload.discount_total)
        
        invoice = {
            "id": inv_id,
            "number": number,
            "status": "issued",
            "payload": payload.model_dump(),
            "totals": totals
        }
        DB[inv_id] = invoice
    
    return {
        "id": inv_id,
        "number": number,
        "status": "issued",
        "totals": totals,
        "links": {
            "self": f"/v1/invoices/{inv_id}",
            "html": f"/v1/invoices/{inv_id}/html"
        }
    }


# ==================== LIST INVOICES ====================

@app.get("/v1/invoices")
async def list_invoices(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """List invoices"""
    
    if USE_DATABASE:
        invoices = db.query(Invoice).filter(
            Invoice.merchant_id == merchant.id
        ).order_by(Invoice.created_at.desc()).limit(50).all()
        
        return [
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
    else:
        return list(DB.values())


# ==================== GET INVOICE ====================

@app.get("/v1/invoices/{inv_id}")
async def get_invoice(
    inv_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """Get invoice detail"""
    
    if USE_DATABASE:
        invoice = db.query(Invoice).filter(
            Invoice.id == inv_id,
            Invoice.merchant_id == merchant.id  # Data isolation!
        ).first()
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        
        return {
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
    else:
        if inv_id not in DB:
            raise HTTPException(404, "Invoice not found")
        return DB[inv_id]


# ==================== HTML INVOICE ====================

@app.get("/v1/invoices/{inv_id}/html", response_class=HTMLResponse)
async def invoice_html(
    inv_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """Render HTML - sama seperti sebelumnya"""
    
    if USE_DATABASE:
        invoice = db.query(Invoice).filter(
            Invoice.id == inv_id,
            Invoice.merchant_id == merchant.id  # Data isolation!
        ).first()
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        
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
    else:
        if inv_id not in DB:
            raise HTTPException(404, "Invoice not found")
        d = DB[inv_id]
    
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
    .header {{ display:flex; justify-content: space-between; align-items: center; }}
    .box {{ border:1px solid #ddd; padding:12px; border-radius:8px; }}
    table {{ width:100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border-bottom:1px solid #eee; padding:8px; text-align:left; }}
    th {{ background:#fafafa; }}
    .right {{ text-align:right; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h2>INVOICE</h2>
      <div>No: {d['number']}</div>
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

  <table style="margin-top:12px; width:100%">
    <tr><td class="right" style="width:80%">Subtotal:</td><td class="right">{rupiah(d['totals']['subtotal'])}</td></tr>
    <tr><td class="right">Pajak:</td><td class="right">{rupiah(d['totals']['tax_total'])}</td></tr>
    <tr><td class="right"><strong>Total:</strong></td><td class="right"><strong>{rupiah(d['totals']['grand_total'])}</strong></td></tr>
  </table>
</body>
</html>"""
    
    return HTMLResponse(content=html, media_type="text/html")


# ==================== ADMIN SETUP ====================

@app.post("/admin/setup", include_in_schema=False)
async def admin_setup(db: Session = Depends(get_db)):
    """
    Setup merchant & API key pertama kali (DEVELOPMENT ONLY)
    Jalankan sekali saja setelah database ready
    """
    
    # Check if merchant already exists
    existing = db.query(Merchant).filter(Merchant.id == "mrc_default").first()
    if existing:
        return {"message": "Already setup", "merchant": existing.name}
    
    # Create default merchant
    merchant = Merchant(
        id="mrc_default",
        name="Default Merchant",
        email="demo@example.com",
        plan="free",
        quota_limit=10
    )
    db.add(merchant)
    db.flush()
    
    # Create API key
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
        "merchant_name": merchant.name,
        "api_key": api_key_value,
        "note": "SAVE THIS API KEY - won't be shown again!",
        "next_step": "Set USE_DATABASE=true in .env and restart server"
    }