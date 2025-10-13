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
-   pip tersedia.

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
