# ReceiptBot: Automated Expense & Split-Bill System via Telegram Bot

**Version:** 2.0.0 (Comprehensive Specification)  
**Target Environment:** Python 3.12 LTS, Telegram Bot API, MariaDB, Tesseract OCR Engine  

---

## 📌 Deskripsi Proyek

**ReceiptBot** adalah solusi otomatisasi pencatatan keuangan personal dan kalkulasi *Split Bill* grup berbasis **Telegram Bot**. Bot ini mengombinasikan *conversational UI*, pemrosesan citra digital (Computer Vision via OpenCV & Tesseract OCR), ekstraksi informasi pola (*regex entity parsing*), serta persistensi data berbasis basis data relasional MariaDB (dengan opsi *fallback* SQLite).

---

## 🚀 Fitur Utama

1. **📸 Otomatisasi Pemindaian Struk (OCR Engine):**
   - Pemrosesan citra digital otomatis: Grayscale, Denoising, CLAHE (Contrast Enhancement), Otsu Binarization.
   - Ekstraksi entitas otomatis: Nama Toko/Merchant, Tanggal Transaksi, Nominal Total, Pajak (PPN/PB1), Service Charge, Diskon, dan Rincian Item Produk.
   - Antarmuka konfirmasi interaktif (*Inline Keyboard*) untuk penyuntingan parameter draf sebelum disimpan ke basis data.

2. **👥 Engine Kalkulasi Split Bill Grup:**
   - Pembagian biaya per item secara fleksibel (*Itemized Split* atau *Equal Split*).
   - Kalkulasi alokasi proporsional untuk Pajak (PPN), Biaya Layanan (*Service Charge*), dan Diskon Promo.
   - Algoritma resolusi pembulatan Rupiah (*remainder distribution*) untuk menjamin presisi 100% tanpa selisih hitung.

3. **📊 Rekapitulasi & Ekspor Laporan Keuangan:**
   - Filter ringkasan pengeluaran berdasarkan periode: Hari Ini, Minggu Ini, Bulan Ini, Semua Waktu.
   - Analisis persentase pengeluaran per kategori.
   - Fitur Ekspor Data ke berkas laporan format **Excel (`.xlsx`)** dan **CSV (`.csv`)**.

---

## 🛠️ Arsitektur Sistem & Struktur Direktori

```text
E:\Project\receipt_bot\
├── .env                    # Konfigurasi variabel lingkungan & kredensial
├── .env.example            # Template berkas konfigurasi
├── README.md               # Dokumentasi utama proyek
├── requirements.txt        # Dependensi pustaka Python
├── config.py               # Pengaturan konfigurasi aplikasi
├── database/
│   ├── connection.py       # Pengelola koneksi SQLAlchemy engine & session
│   └── models.py           # Definisi skema tabel ORM (User, Transaction, SplitBill, dll)
├── services/
│   ├── ocr_engine.py       # Engine pemrosesan citra OpenCV & Tesseract OCR
│   ├── parser_service.py   # Layanan Regex Entity Parsing (Merchant, Date, Total, Items)
│   └── split_bill_engine.py# Engine kalkulasi proporsional split bill
├── bot/
│   ├── main.py             # Entrypoint & Telegram Dispatcher Bot
│   ├── handlers/           # Handler Telegram (Start, Receipt OCR, SplitBill, Rekap)
│   └── utils/
│       └── formatters.py   # Formatter Rupiah, Tanggal, dan Teks Ringkasan
├── scripts/
│   └── init_db.py          # Skrip inisialisasi tabel basis data
└── tests/                  # Suite pengujian otomatis (Pytest)
    ├── test_ocr.py
    ├── test_parser.py
    ├── test_split_bill.py
    └── test_db.py
```

---

## 🗄️ Skema Basis Data (MariaDB: `db_receipt_bot`)

Sistem menggunakan skema basis data relasional terstruktur:

- **`users`**: Menyimpan identitas pengguna Telegram (`id`, `username`, `first_name`, `created_at`).
- **`transactions`**: Menyimpan catatan pengeluaran (`id`, `user_id`, `merchant`, `transaction_date`, `total_amount`, `category`, `image_path`).
- **`transaction_items`**: Menyimpan rincian produk/item transaksi (`id`, `transaction_id`, `item_name`, `qty`, `price`, `subtotal`).
- **`split_bills`**: Menyimpan data sesi split bill (`id`, `creator_id`, `title`, `total_amount`, `tax_amount`, `service_charge`, `discount_amount`, `status`).
- **`split_bill_items`**: Rincian item split bill (`id`, `split_bill_id`, `item_name`, `price`, `subtotal`).
- **`split_bill_participants`**: Menyimpan status tagihan anggota (`id`, `split_bill_id`, `participant_name`, `allocated_amount`, `is_paid`).

---

## 📦 Petunjuk Instalasi & Penggunaan

### 1. Persyaratan Sistem
- **Python 3.12+**
- **Tesseract OCR Engine** terpasang di `C:\Program Files\Tesseract-OCR\tesseract.exe`
- **MariaDB Server** (Port 3306)

### 2. Persiapan Lingkungan & Dependensi
```powershell
cd E:\Project\receipt_bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Konfigurasi Variabel Lingkungan (`.env`)
Salin `.env.example` ke `.env` lalu sesuaikan kredensial bot Telegram Anda:
```ini
TELEGRAM_BOT_TOKEN=7890123456:AAYourActualTelegramTokenHere
DATABASE_URL=mysql+pymysql://root:@localhost:3306/db_receipt_bot
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 4. Inisialisasi Basis Data
```powershell
python scripts/init_db.py
```

### 5. Menjalankan Test Suite (`pytest`)
```powershell
pytest -v
```

### 6. Menjalankan Bot Telegram
```powershell
python bot/main.py
```

---

## 🧪 Pengujian & Verifikasi System

Pengujian unit dan integrasi otomatis diuji menggunakan `pytest` dengan cakupan:
- **`test_ocr.py`**: Verifikasi fungsi preprocessing image OpenCV & Tesseract binary pipeline.
- **`test_parser.py`**: Ekstraksi nominal mata uang Rupiah, penanggalan Indonesia, deteksi toko, dan rincian item.
- **`test_split_bill.py`**: Uji presisi rumus proporsional pajak/diskon dan resolusi pembulatan selisih sisa.
- **`test_db.py`**: Uji fungsi CRUD SQLAlchemy ORM pada MariaDB/SQLite.

---

## 📝 Lisensi & Hak Cipta
Hak Cipta © 2026 Proyek ReceiptBot. Dikembangkan untuk Penyerahan Proyek Akademik & Penggunaan Internal.
