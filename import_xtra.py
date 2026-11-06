#!/usr/bin/env python3
"""Import semua toko Komisi XTRA dari Shopee Affiliate ke katalog PX STORE."""
import os, sys, json, csv, tempfile, subprocess, datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopee_common import launch_context, clean_pages, PROFILE_DIR
API = "https://affiliate.shopee.co.id/api/v3/offer/shop/list?sort_type=1&page_offset={off}&page_limit=20&keyword="
OFFER_URL = "https://affiliate.shopee.co.id/offer/brand_offer"
SHOPEE_PHP = r"C:\xampp\php\php.exe"
IMPORT_PHP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "import_shopee_csv.php")


def log(msg):
    print(f"[xtra] {msg}", flush=True)


def tgl(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts)).strftime('%d-%m-%Y')
    except Exception:
        return '-'


from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = launch_context(p)
    page = clean_pages(ctx)
    page.goto(OFFER_URL, wait_until="domcontentloaded", timeout=60000)
    time.sleep(6) if (time := __import__('time')) else None

    shops = []
    seen = set()
    for off in range(0, 2000, 20):
        body = page.evaluate("""async (url) => { const r = await fetch(url, {credentials: 'include'}); return await r.text(); }""", API.format(off=off))
        data = json.loads(body)
        d = data.get('data') or {}
        batch = d.get('list') or []
        if not batch:
            log(f"offset={off}: kosong -> selesai")
            break
        log(f"offset={off}: {len(batch)} toko (has_more={d.get('has_more')}, total={d.get('total_count')})")
        for s in batch:
            sid = s.get('shop_id')
            if sid in seen:
                continue
            seen.add(sid)
            shops.append(s)
    ctx.close()

log(f"Total toko diambil: {len(shops)}")

fd, csv_path = tempfile.mkstemp(suffix='.csv', prefix='xtra_')
with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Nama Produk', 'Harga', 'Link Universal (Affiliate)', 'Link Gambar 1',
                'Kategori', 'Rating', 'Deskripsi Produk'])
    for s in shops:
        name = (s.get('shop_name') or '').strip()
        rate = s.get('commission_rate') or ''
        try:
            end = int(s.get('period_end_time') or 0)
            end_txt = 'Tanpa batas akhir' if end > 30000000000 else f"hingga {tgl(end)}"
        except Exception:
            end_txt = 'Tanpa batas akhir'
        start_txt = tgl(s.get('period_start_time') or 0)
        url = s.get('long_link') or s.get('shop_link') or ''
        img = s.get('shop_image') or ''
        desc = (f"Toko Shopee {name} dengan program Komisi XTRA â€” "
                f"komisi affiliate hingga {rate}. Berlaku mulai {start_txt}, {end_txt}. "
                f"Klik untuk kunjungi toko dan jelajahi ribuan produk berkomisi XTRA.")
        w.writerow([f"Toko {name} (Komisi hingga {rate})"[:190], 0, url, img,
                    'Komisi XTRA', 0, desc[:5000]])
log(f"CSV: {csv_path}")
result = subprocess.run([SHOPEE_PHP, IMPORT_PHP, csv_path, '--publish'],
                        capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
