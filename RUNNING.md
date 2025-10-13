# Cara Menjalankan Cepat (CMD)

## Set sekali (opsional, biar API_KEY nempel di Windows)

setx API_KEY demo_merchant_key

## Setiap kali mau lanjut kerja (hari berikutnya)

1. Buka CMD di folder proyek
2. Aktifkan venv
   .\.venv\Scripts\activate
3. Jalankan server
   uvicorn app.main:app --reload
    - Cek: http://127.0.0.1:8000/healthz → {"ok": true}
    - Docs: http://127.0.0.1:8000/docs

## Bikin invoice baru (di CMD lain, folder yang sama)

echo {"customer":{"name":"Toko X"},"items":[{"name":"Produk A","qty":2,"unit_price":10000,"tax_rate":0.11}],"issue_date":"2025-10-13"}>data.json
curl.exe -H "X-API-Key: demo_merchant_key" -H "Content-Type: application/json" --data "@data.json" http://127.0.0.1:8000/v1/invoices

-   Salin nilai "id" dari respons (contoh: inv_ab12cd34)

## Lihat daftar invoice (opsional)

curl.exe -H "X-API-Key: demo_merchant_key" http://127.0.0.1:8000/v1/invoices

## Ambil & buka HTML (ganti INV_ID)

curl.exe -H "X-API-Key: demo_merchant_key" -o invoice.html "http://127.0.0.1:8000/v1/invoices/INV_ID/html" & start "" invoice.html

## Catatan penting

-   Data disimpan **in-memory** → kalau server di-restart, buat invoice baru lagi.
-   401 → API_KEY berbeda. Jalankan server di CMD yang sama dengan `set API_KEY=demo_merchant_key` (kalau belum pakai `setx`).
-   404 → ID salah/expired (karena restart). Buat invoice baru.
-   500 → (harusnya tidak di SAFE MODE). Lihat log di jendela `uvicorn`.
