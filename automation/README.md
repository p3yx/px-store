# PX STORE — Automasi Shopee Affiliate (Skrip & Panduan)

Repository ini berisi **semua skrip otomatisasi** untuk sistem PX STORE, lengkap dengan panduan instalasi dan penggunaan. **Tidak berisi aplikasi web** (website tetap di komputer pemilik).

## Isi Repository

| File | Deskripsi |
|------|-----------|
| `automation/shopee_common.py` | Modul shared: Chrome fullscreen, 1 tab bersih, profil login tersimpan |
| `automation/shopee_affiliate_import.py` | Impor produk dari Penawaran Produk Shopee (buat link affiliate otomatis) |
| `automation/shopee_import_all.py` | Impor SEMUA produk dari halaman 1–5 Penawaran Produk |
| `automation/shopee_import_full.py` | Scan penuh — tambahkan yang belum ada (tanpa duplikat) |
| `automation/shopee_import_remaining.py` | Impor sisa offset ≥ 100 |
| `automation/import_xtra.py` | Impor toko Komisi XTRA (offset 0) |
| `automation/import_xtra_all.py` | Import toko Komisi XTRA (gabungan urutan 1,2,3 dengan dedup) |
| `automation/daily_report.php` | Laporan 7 hari: order, omzet, terlaris |
| `automation/generate_ad_copy.php` | Teks iklan FB/IG/WA per produk |
| `automation/recommend.php` | Rekomendasi 10 produk unggul berdasarkan rating/terjual/harga |
| `automation/run_all.bat` | Jalankan semua tugas harian sekaligus |
| `automation/verify_browser.py` | Cek jendela Chrome & jumlah tab |
| `README.md` | Panduan instalasi & penggunaan (file ini) |

## Persiapan (sekali saja di komputer Anda)

### 1. XAMPP & Database
- Pasang **XAMPP** (Apache + MySQL/MariaDB) di `C:\xampp\`
- Jalankan Apache & MySQL dari XAMPP Control Panel
- Buat database: `C:\xampp\mysql\bin\mysql.exe -u root < pxstore\migration.sql` (atau leaskrip `import_all.py` akan bikin tabel jika belum ada)

### 2. Chrome Profile Login Shopee (SATU KALI)
- Jalankan `python automation\login_shopee.py` (jika ada) atau buka Chrome dan login Shopee di akun Anda
- Script akan menggunakan profil `pxstore-shopee-profile` di folder AppData
- **Jangan hapus folder profil ini** jika ingin menjalankan script ulang

### 3. Aktivasi Sistem Sewa (Opsional, butuh lisensi)
```bash
# Tampilkan HWID komputer
python pxstore.py hwid

# Aktifkan lisensi (dapatkan key dari pemilik)
python pxstore.py activate <KEY_LISENSI>

# Cek status
python pxstore.py status
```

## Perintah Utama (via `pxstore.py` di folder induk)

Semua perintah dijalankan dari folder `C:\xampp\htdocs\pxstore`:

```bash
# Impor Produk
python pxstore.py import-shopee --keyword "jas hujan" --limit 10           # Cari + buat link
python pxstore.py import-all          # Impor seluruh Penawaran Produk + link
python pxstore.py import-xtra         # Impor toko Komisi XTRA (500+ toko)

# Laporan & Rekomendasi
python pxstore.py report 7            # Laporan omzet 7 hari terakhir
python pxstore.py recommend           # Rekomendasi 10 produk promo

# Iklan & Verifikasi
python pxstore.py ads AFF-0001        # Teks iklan FB/IG/WA untuk produk
python pxstore.py verify              # Cek jendela Chrome fullscreen & tab

# Evaluasi (tanpa lisensi)
python pxstore.py hwid     # HWID komputer ini
python pxstore.py status   # Cek lisensi
python pxstore.py help     # Bantuan perintah
```

> **Catatan Penting:**
> - `import-shopee` / `import-all` / `import-xtra` membuka **jendela Chrome terlihat**. Jangan tutup browser selama skrip berjalan.
> - Setiap run hanya **1 tab**, otomatis **fullscreen**, dan tidak memakai profil browser utama Anda.
> - Data hasil impor disimpan di database `karyastore` (MySQL/XAMPP).
> - Lisensi diperlukan untuk semua perintah kecuali `hwid`/`status`/`help`.

## Jadwal Otomatis (Task Scheduler Windows)

Untuk otomatisasi harian (misimpan laporan & iklan setiap pagi):

1. Tekan **Win + R**, ketik `taskschd.msc`, tekan Enter
2. **Create Basic Task** → nama `PX STORE Auto` → Daily → jam 08:00
3. Action: Start a program → `C:\xampp\htdocs\pxstore\automation\run_all.bat`
4. Selesai — akan otomatis menjalankan laporan, rekomendasi, dan membersihkan tab Chrome setiap pagi

## Troubleshooting

- **Script gagal/login ulang**: Tutup semua jendela Chrome, lalu jalankan ulang skrip. Browser akan membuka profil login Shopee secara otomatis.
- **Tab bertambah**: Setiap skrip pastikan menutup tab setelah selesai. Cek dengan `python pxstore.py verify`.
- **Database error**: Pastikan XAMPP MySQL sudah running, dan `config.php` di `C:\xampp\htdocs\pxstore\` sudah benar (atau atur via env variable `PXSTORE_DB_*`).
- **Lisensi expired**: Buat lisensi baru dengan `python maker\make_license.py "Nama" 30` (30 hari) atau hubungi pemilik.

## Kontribusi / Pengembangan

Jika Anda ingin menambahkan fitur baru atau memodifikasi skrip:
1. Buat branch baru dari `main`
2. Lakukan perubahan, pastikan semua path relatif (tidak pakai `C:\Users\Peyx\...`)
3. Test di komputer sendiri sebelum commit
4. Kirik pull request ke pemilik repo

---

**Untuk pertanyaan tentang lisensi atau bantuan teknis, hubungi pemilik paket PX STORE.**