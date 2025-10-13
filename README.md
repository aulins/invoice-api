# UMKM Invoice API

Microservice sederhana untuk **menerbitkan dan menampilkan invoice komersial** bagi UMKM. Proyek ini dirancang sebagai fondasi API yang ringan: mudah dijalankan, jelas kontraknya, dan siap dikembangkan menjadi layanan berbayar.

> **Catatan hukum**  
> Proyek ini menerbitkan **invoice/kwitansi komersial** (nota/tagihan), **bukan** e-Faktur pajak. Jika Pelaku Usaha adalah PKP dan butuh e-Faktur, penerbitannya tetap melalui kanal resmi DJP/PJAP. API ini hanya dapat memuat **nomor referensi** e-Faktur pada invoice jika diperlukan.

---

## Fitur utama

-   **Create & read invoice**: item, kuantitas, harga, diskon, pajak per-item, biaya lain (shipping/service/rounding).
-   **Perhitungan otomatis**: subtotal, pajak, total akhir; format IDR (Rp).
-   **Penomoran**: `INV/YYYY/MM/SEQ`.
-   **Render HTML**: server menghasilkan **HTML siap cetak** (Ctrl/Cmd + P → “Save as PDF”).
    > Implementasi saat ini **tanpa template engine** untuk meminimalkan dependensi & error (SAFE MODE).
-   **Auth sederhana**: header `X-API-Key`.
-   **OpenAPI/Swagger**: dokumentasi otomatis di `/docs`.
-   **Penyimpanan sementara (in-memory)**: cocok untuk belajar/MVP.

---

## Arsitektur singkat

> Client → FastAPI (app/main.py) → In-memory store
> ↳ HTML renderer (server-side)

## Prasyarat

-   Python 3.10+
-   Windows Command Prompt (CMD) / macOS / Linux terminal.
-   `pip` tersedia.

## Menjalankan (Quick Start)

### 1) Instalasi

```bash
# clone repo ini, lalu:
python -m venv .venv
# Windows CMD
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Konfigurasi kunci API

```bash
# Windows CMD (hanya untuk sesi terminal ini)
set API_KEY=demo_merchant_key
# macOS/Linux
export API_KEY=demo_merchant_key
```

### 3) Start server

```bash
uvicorn app.main:app --reload
```

-   Health check: `http://127.0.0.1:8000/healthz` → `{"ok": true}`
-   Swagger/OpenAPI: `http://127.0.0.1:8000/docs`

## Membuat invoice pertama

### Siapkan body request

```bash
# Windows cmd
echo {"customer":{"name":"Toko X"},"items":[{"name":"Produk A","qty":2,"unit_price":10000,"tax_rate":0.11}],"issue_date":"2025-10-13"}>data.json
```

```bash
#macOS/Linux
cat > data.json <<'JSON'
{
  "customer": { "name": "Toko X" },
  "items": [ { "name": "Produk A", "qty": 2, "unit_price": 10000, "tax_rate": 0.11 } ],
  "issue_date": "2025-10-13"
}
JSON
```

### Kirim request

```bash
# Windows CMD
curl.exe -H "X-API-Key: demo_merchant_key" -H "Content-Type: application/json" --data "@data.json" http://127.0.0.1:8000/v1/invoices
```

```bash
# macOS/Linux
curl -H "X-API-Key: demo_merchant_key" -H "Content-Type: application/json" --data @data.json http://127.0.0.1:8000/v1/invoices
```

Salin nilai `id` dari respons `(mis. inv_abc12345)`.

### Tampilkan HTML & cetak PDF

```bash
# windows cmd
curl.exe -H "X-API-Key: demo_merchant_key" -o invoice.html "http://127.0.0.1:8000/v1/invoices/INV_ID/html" & start "" invoice.html
```

```bash
# macOS/Linux
curl -H "X-API-Key: demo_merchant_key" -o invoice.html "http://127.0.0.1:8000/v1/invoices/INV_ID/html" && open invoice.html   # macOS
# atau:
xdg-open invoice.html  # Linux
```

---

## API endpoints

Method > Path > Deskripsi
GET `/healthz` : Health check –
POST `/v1/invoices` : Buat invoice baru
GET `/v1/invoices` : Daftar invoice
GET `/v1/invoices/{id}` : Detail invoice
GET `/v1/invoices/{id}/html` : HTML invoice siap cetak

### Contoh request – `POST /v1/invoices`

```bash
{
  "customer": { "name": "Toko X" },
  "items": [
    { "name": "Produk A", "qty": 2, "unit_price": 10000, "tax_rate": 0.11 }
  ],
  "issue_date": "2025-10-13"
}

```

Contoh respons

```bash
{
  "id": "inv_abc12345",
  "number": "INV/2025/10/0001",
  "status": "issued",
  "totals": { "subtotal": 20000, "tax_total": 2200, "grand_total": 22200 },
  "links": {
    "self": "/v1/invoices/inv_abc12345",
    "html": "/v1/invoices/inv_abc12345/html"
  }
}
```

## Konfigurasi

-   `API_KEY` (env var): nilai yang wajib sama dengan header `X-API-Key` pada setiap request ber-privilege.
-   Windows CMD (sesi saat ini): `set API_KEY=demo_merchant_key`
-   macOS/Linux: `export API_KEY=demo_merchant_key`

## Batasan saat ini

-   In-memory storage: data hilang saat proses server berhenti/restart.
-   Single tenant dan tanpa rate-limit.
-   Tidak menerbitkan e-Faktur pajak.
-   HTML server-side (tanpa template engine); tampilan sederhana namun stabil untuk pemula.

## Roadmap

-   Persistensi Postgres (SQLModel/SQLAlchemy) + migrasi.
-   Penomoran yang persisten per bulan/tahun.
-   Template engine (Jinja2) & tema invoice.
-   Ekspor PDF server-side.
-   Webhook pembayaran & kwitansi “LUNAS” otomatis.
-   Multi-tenant, API key per merchant, rate limiting, dan usage metering.

## Struktur proyek

```bash
app/
  main.py        # FastAPI app, endpoints, kalkulasi, renderer HTML
  auth.py        # Validasi header X-API-Key
  models.py      # Skema request (Pydantic)
requirements.txt
```

## Keamanan & privasi

-   Jangan menaruh rahasia di URL (gunakan header `X-API-Key`).
-   Batasi data pelanggan yang dikirim (minim yang diperlukan).
-   Gunakan HTTPS saat dipublikasikan

## Kontribusi

Issue & PR dipersilakan. Mohon sertakan langkah reproduksi yang jelas.

## Lisensi

-
