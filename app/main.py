from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import Dict
from uuid import uuid4
from datetime import date
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os, json, traceback

from .auth import require_api_key
from .models import CreateInvoice, Item, Charges

app = FastAPI(title="UMKM Invoice API (HTML)", version="1.0.0")

DB: Dict[str, dict] = {}

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(['html']))

def rupiah(n: float) -> str:
    return f"Rp {int(n):,}".replace(",", ".")
env.filters["rupiah"] = rupiah

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

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post("/v1/invoices", dependencies=[Depends(require_api_key)])
async def create_invoice(payload: CreateInvoice):
    inv_id = f"inv_{uuid4().hex[:8]}"
    number = next_number()
    totals = calc_totals(payload.items, payload.charges, payload.discount_total)
    record = {"id": inv_id, "number": number, "status": "issued", "payload": payload.model_dump(), "totals": totals}
    DB[inv_id] = record
    return {"id": inv_id, "number": number, "status": "issued", "totals": totals, "links": {"self": f"/v1/invoices/{inv_id}", "html": f"/v1/invoices/{inv_id}/html"}}

@app.get("/v1/invoices", dependencies=[Depends(require_api_key)])
async def list_invoices():
    return list(DB.values())

@app.get("/v1/invoices/{inv_id}", dependencies=[Depends(require_api_key)])
async def get_invoice(inv_id: str):
    if inv_id not in DB:
        raise HTTPException(404, "Invoice not found")
    return DB[inv_id]

@app.get("/v1/invoices/{inv_id}/html", response_class=HTMLResponse, dependencies=[Depends(require_api_key)])
async def invoice_html(inv_id: str):
    if inv_id not in DB:
        raise HTTPException(404, "Invoice not found")
    data = DB[inv_id]
    template = env.get_template("invoice.html")
    html = template.render(number=data["number"], totals=data["totals"], payload=data["payload"], status=data["status"])
    return HTMLResponse(content=html, media_type="text/html")
