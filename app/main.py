from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from typing import Dict
from uuid import uuid4
from datetime import date
import os, json

from .auth import require_api_key
from .models import CreateInvoice, Item, Charges

app = FastAPI(title="UMKM Invoice API (SAFE MODE)", version="1.0.0")

# --- In-memory store ---
DB: Dict[str, dict] = {}

def rupiah(n: float) -> str:
    try:
        return f"Rp {int(n):,}".replace(",", ".")
    except Exception:
        return "Rp 0"

def calc_totals(items: list[Item], charges: Charges, discount_total: float):
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
    return {"subtotal": round(subtotal), "tax_total": round(tax_total), "grand_total": round(grand)}

def next_number():
    return f"INV/{date.today().year}/{date.today().month:02d}/{len(DB)+1:04d}"

# --- Health & debug ---
@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/debug/info", response_class=PlainTextResponse)
async def debug_info():
    return "OK: SAFE MODE (no Jinja template)."

# --- Invoices API ---
@app.post("/v1/invoices", dependencies=[Depends(require_api_key)])
async def create_invoice(payload: CreateInvoice):
    inv_id = f"inv_{uuid4().hex[:8]}"
    number = next_number()
    totals = calc_totals(payload.items, payload.charges, payload.discount_total)
    record = {"id": inv_id, "number": number, "status": "issued", "payload": payload.model_dump(), "totals": totals}
    DB[inv_id] = record
    return {
        "id": inv_id,
        "number": number,
        "status": "issued",
        "totals": totals,
        "links": {"self": f"/v1/invoices/{inv_id}", "html": f"/v1/invoices/{inv_id}/html"}
    }

@app.get("/v1/invoices", dependencies=[Depends(require_api_key)])
async def list_invoices():
    return list(DB.values())

@app.get("/v1/invoices/{inv_id}", dependencies=[Depends(require_api_key)])
async def get_invoice(inv_id: str):
    if inv_id not in DB:
        raise HTTPException(404, "Invoice not found")
    return DB[inv_id]

# --- HTML tanpa Jinja (aman) ---
@app.get("/v1/invoices/{inv_id}/html", response_class=HTMLResponse, dependencies=[Depends(require_api_key)])
async def invoice_html(inv_id: str):
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
