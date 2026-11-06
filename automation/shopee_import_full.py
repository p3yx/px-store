#!/usr/bin/env python3
"""Full scan Penawaran Produk; impor hanya produk yang belum ada di database."""
import os, sys, time, json, csv, tempfile, subprocess, re

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopee_common import launch_context, clean_pages, PROFILE_DIR
OFFER_URL = "https://affiliate.shopee.co.id/offer/product_offer"
API = "https://affiliate.shopee.co.id/api/v3/offer/product/list?list_type=0&sort_type=1&page_offset={off}&page_limit=20&client_type=1"
SHOPEE_PHP = r"C:\xampp\php\php.exe"
IMPORT_PHP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "import_shopee_csv.php")
IMG_BASE = "https://down-aka-id.img.susercontent.com"
EXISTING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "existing_ids.txt")


def log(msg):
    print(f"[scan] {msg}", flush=True)


existing = set()
if os.path.exists(EXISTING_FILE):
    for line in open(EXISTING_FILE, encoding='utf-8', errors='ignore'):
        line = line.strip().split('?')[0]
        if '/' in line:
            line = line.split('/')[-1]
        if line:
            existing.add(line)
log(f"Produk sudah ada di DB: {len(existing)}")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = launch_context(p)
    page = clean_pages(ctx)
    page.goto(OFFER_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector('.AffiliateItemCard', timeout=30000)

    all_items = []
    seen = set()
    for off in range(0, 4000, 20):
        body = page.evaluate("""async (url) => { const r = await fetch(url, {credentials: 'include'}); return await r.text(); }""", API.format(off=off))
        try:
            data = json.loads(body)
        except Exception:
            log(f"offset={off}: respons tidak bisa diparse, berhenti")
            break
        lst = (data.get('data') or {}).get('list') or []
        if not lst:
            log(f"offset={off}: kosong -> selesai")
            break
        log(f"offset={off}: {len(lst)} item")
        for item in lst:
            iid = item.get('item_id')
            if iid in seen:
                continue
            seen.add(iid)
            all_items.append(item)
        time.sleep(0.4)
    ctx.close()

missing = [i for i in all_items if (i.get('batch_item_for_item_card_full') or {}).get('itemid') not in existing
           and i.get('item_id') not in existing]
log(f"Total penawaran saat ini: {len(all_items)} | Belum di DB: {len(missing)}")

fd, csv_path = tempfile.mkstemp(suffix='.csv', prefix='shopee_scan_')
with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Nama Produk', 'Harga', 'Link Universal (Affiliate)', 'Link Gambar 1',
                'Kategori', 'Rating', 'Deskripsi Produk'])
    for item in missing:
        bci = item.get('batch_item_for_item_card_full') or {}
        name = (bci.get('name') or '').strip()
        price = int(bci.get('price') or 0) // 100000
        img_id = bci.get('image') or ''
        img = f"{IMG_BASE}/{img_id}.webp" if img_id else ''
        rating = round(((bci.get('item_rating') or {}).get('rating_star') or 0), 1)
        sold_text = bci.get('historical_sold_text') or bci.get('sold_text') or ''
        discount = bci.get('discount') or ''
        shop = (bci.get('shop_name') or '').strip()
        comm = item.get('default_commission_rate') or item.get('max_commission_rate') or ''
        rating_db = f"{rating:.1f}" if rating else "0"
        desc = (f"{name}. Terjual {sold_text}. "
                f"{'Diskon ' + discount + '. ' if discount else ''}"
                f"Komisi affiliate hingga {comm}. "
                f"{'Toko: ' + shop + '. ' if shop else ''}"
                f"Kualitas & layanan menyesuaikan merchant Shopee.")
        w.writerow([name[:190], price, item.get('long_link') or '', img,
                    'Shopee Affiliate', rating_db, desc[:5000]])

result = subprocess.run([SHOPEE_PHP, IMPORT_PHP, csv_path, '--publish'],
                        capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
