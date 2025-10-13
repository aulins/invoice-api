# UMKM Invoice API — Starter + HTML Invoice

API-only MVP dengan endpoint HTML invoice siap cetak (Ctrl/Cmd+P -> Save as PDF).

## Jalankan
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
set API_KEY=demo_merchant_key   # Windows (PowerShell: $env:API_KEY='demo_merchant_key')
export API_KEY=demo_merchant_key # Mac/Linux

uvicorn app.main:app --reload
```
Buka docs: http://127.0.0.1:8000/docs

## Coba cepat
1) Create invoice:
```bash
curl -X POST http://127.0.0.1:8000/v1/invoices   -H "X-API-Key: demo_merchant_key" -H "Content-Type: application/json"   -d '{"customer":{"name":"Toko X"},"items":[{"name":"Produk A","qty":2,"unit_price":10000,"tax_rate":0.11}],"issue_date":"2025-10-13"}'
```
2) Render HTML:
http://127.0.0.1:8000/v1/invoices/<id>/html
