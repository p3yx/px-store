@echo off
REM PX STORE — Automasi harian untuk "tim karyawan".
REM Jalankan manual: run_all.bat
REM Jadwalkan otomatis: lihat README.md (Task Scheduler).
setlocal
set PHP=C:\xampp\php\php.exe
set DIR=%~dp0

echo === PX STORE AUTOMASI ===
if not exist "%DIR%output" mkdir "%DIR%output"

echo.
echo [1/3] Laporan harian (7 hari)...
"%PHP%" "%DIR%daily_report.php" 7

echo.
echo [3/4] Generate teks iklan produk terbaru...
"%PHP%" "%DIR%generate_ad_copy.php" --all

echo.
echo [4/4] Rekomendasi produk untuk dipromosikan...
"%PHP%" "%DIR%recommend.php"

echo.
echo Selesai. Hasil di folder output\

echo Catatan: import produk Shopee dilakukan manual dengan file CSV:
echo   php import_shopee_csv.php E:\Downloads\ekspor-shopee.csv --publish
endlocal
