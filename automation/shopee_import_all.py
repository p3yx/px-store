#!/usr/bin/env python3
"""
PX STORE â€” Import SEMUA produk dari Penawaran Produk Shopee ke katalog web.

Alur:
  1. Buka Penawaran Produk (sesi login tersimpan di profil pxstore-shopee)
  2. Intercept respons API /api/v3/offer/product/list untuk halaman 1..N
  3. Ekstrak: nama, harga, harga coret, foto, rating, terjual, toko, komisi, link affiliate (long_link)
  4. Tulis CSV, impor ke database dengan import_shopee_csv.php (--publish)
"""
import os, sys, time, json, csv, tempfile, subprocess, argparse, re

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopee_common import launch_context, clean_pages, PROFILE_DIR
OFFER_URL = "https://affiliate.shopee.co.id/offer/product_offer"
SHOPEE_PHP = r"C:\xampp\php\php.exe"
IMPORT_PHP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "import_shopee_csv.php")
IMG_BASE = "https://down-aka-id.img.susercontent.com"


def log(msg):
    print(f"[import-all] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', type=int, default=5, help='jumlah halaman yang diimpor (default 5 = 100 produk)')
    ap.add_argument('--publish', action='store_true', default=True)
    ap.add_argument('--no-publish', dest='publish', action='store_false')
    ap.add_argument('--dry', action='store_true', help='simulasi saja')
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    captured = {}

    def on_response(resp):
        if '/api/v3/offer/product/list' in resp.url:
            try:
                captured[resp.url] = resp.text()
            except Exception:
                pass

    with sync_playwright() as p:
        ctx = launch_context(p)
        page = clean_pages(ctx)
        page.on("response", on_response)

        log("Membuka Penawaran Produk...")
        page.goto(OFFER_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector('.AffiliateItemCard', timeout=30000)

        for page_no in range(1, args.pages + 1):
            if page_no > 1:
                log(f"Pindah ke halaman {page_no}...")
                clicked = False
                for sel in [f'.page-item.page-page:text-is("{page_no}")',
                            f'.page-item:has-text("{page_no}")',
                            f'text="{page_no}"']:
                    loc = page.locator(sel).first
                    try:
                        if loc.count() and loc.is_visible():
                            loc.click()
                            clicked = True
                            break
                    except Exception:
                        continue
                if not clicked:
                    log(f"   -> halaman {page_no} tidak ditemukan, berhenti")
                    break
                time.sleep(4)
            else:
                time.sleep(2)

        ctx.close()

    # kumpulkan semua produk
    all_items = []
    for url, body in captured.items():
        try:
            data = json.loads(body)
            lst = (data.get('data') or {}).get('list') or []
            # urutkan berdasarkan offset dari URL
            m = re.search(r'page_offset=(\d+)', url)
            off = int(m.group(1)) if m else 0
            all_items.append((off, lst))
        except Exception as e:
            log(f"Gagal parse {url}: {e}")
    all_items.sort(key=lambda x: x[0])
    seen = set()
    products = []
    for _, lst in all_items:
        for item in lst:
            if item.get('item_id') in seen:
                continue
            seen.add(item.get('item_id'))
            products.append(item)
    log(f"Produk tertangkap dari API: {len(products)}")

    fd, csv_path = tempfile.mkstemp(suffix='.csv', prefix='shopee_all_')
    with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Nama Produk', 'Harga', 'Link Universal (Affiliate)', 'Link Gambar 1',
                    'Kategori', 'Rating', 'Deskripsi Produk'])
        for item in products:
            bci = item.get('batch_item_for_item_card_full') or {}
            name = (bci.get('name') or '').strip()
            price = int(bci.get('price') or 0) // 100000
            old_price = int(bci.get('price_max_before_discount') or bci.get('price_before_discount') or 0) // 100000
            img_id = bci.get('image') or ''
            img = f"{IMG_BASE}/{img_id}.webp" if img_id else ''
            rating = round(((bci.get('item_rating') or {}).get('rating_star') or 0), 1)
            sold_text = bci.get('historical_sold_text') or bci.get('sold_text') or ''
            discount = bci.get('discount') or ''
            shop = (bci.get('shop_name') or '').strip()
            comm = item.get('default_commission_rate') or item.get('max_commission_rate') or ''
            sold_int = int(bci.get('historical_sold') or 0)
            # rating harus 0-5 untuk DB (default 0 kalau tidak ada)
            rating_db = f"{rating:.1f}" if rating else "0"
            desc = (f"{name}. Terjual {sold_text}. "
                    f"{'Diskon ' + discount + '. ' if discount else ''}"
                    f"Komisi affiliate hingga {comm}. "
                    f"{'Toko: ' + shop + '. ' if shop else ''}"
                    f"Kualitas & layanan menyesuaikan merchant Shopee.")
            features_note = f"Terjual {sold_text} | Komisi {comm} | {shop}"
            w.writerow([name[:190], price, item.get('long_link') or '', img,
                        'Shopee Affiliate', rating_db, desc[:5000]])
    log(f"CSV sementara: {csv_path}")

    cmd = [SHOPEE_PHP, IMPORT_PHP, csv_path, '--publish']
    if args.dry:
        cmd.append('--dry')
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)


if __name__ == '__main__':
    main()
