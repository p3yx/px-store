#!/usr/bin/env python3
"""
PX STORE â€” Otomasi Shopee Affiliate (kolom Penawaran Produk).

Alur:
  1. Buka https://affiliate.shopee.co.id/offer/product_offer (login sesi Anda, profil khusus)
  2. Jika --keyword diisi, ketik di kolom pencarian lalu tekan Cari
  3. Ambil data tiap kartu produk (nama, harga, foto, terjual, komisi)
  4. Klik "Buat Link" pada tiap produk, baca link affiliate dari modal
  5. Impor ke database pxstore lewat import_shopee_csv.php (draft dulu, kecuali --publish)

Cara pakai:
  python shopee_affiliate_import.py --keyword "jas hujan" --limit 10
  python shopee_affiliate_import.py --keyword "kabel" --limit 5 --dry
  python shopee_affiliate_import.py --limit 10 --publish
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopee_common import launch_context, clean_pages, PROFILE_DIR

OFFER_URL = "https://affiliate.shopee.co.id/offer/product_offer"
SHOPEE_PHP = r"C:\xampp\php\php.exe"
IMPORT_PHP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "import_shopee_csv.php")


def log(msg):
    print(f"[shopee] {msg}", flush=True)


def extract_cards(page):
    return page.eval_on_selector_all(
        '.AffiliateItemCard',
        """els => els.map((el, i) => {
            const name = (el.querySelector('.ItemCard__name') || {}).innerText || '';
            const priceText = (el.querySelector('.ItemCard__price .price') || {}).innerText || '';
            const img = (el.querySelector('.ItemCard__image img') || {}).src || '';
            const sold = (el.querySelector('.ItemCardSold__wrap') || {}).innerText || '';
            const komisi = (el.querySelector('.commRate') || {}).innerText || '';
            const detail = el.querySelector('a') ? el.querySelector('a').href : '';
            return { idx: i, name: name.trim(), priceText, img, sold, komisi, detail };
        })"""
    )


def parse_price(text):
    digits = re.sub(r'[^0-9]', '', text or '')
    return int(digits) if digits else 0


def search_products(page, keyword):
    log(f"Mencari: {keyword}")
    try:
        box = page.locator('input[placeholder*="Cari Produk"]').first
        box.fill(keyword)
        time.sleep(0.5)
        box.press('Enter')
    except Exception:
        try:
            page.get_by_text('Cari', exact=True).first.click()
        except Exception:
            log("Tombol Cari tidak ditemukan; lanjut tanpa pencarian")
    time.sleep(6)


def click_buat_link(page, card_index, retries=3):
    """Klik 'Buat Link' pada kartu ke-index, baca link dari modal, tutup modal."""
    for attempt in range(retries):
        buttons = page.locator('.AffiliateItemCard__getlinkBtn')
        if buttons.count() <= card_index:
            log(f"   -> tombol ke-{card_index+1} tidak ditemukan (percobaan {attempt+1})")
            time.sleep(2)
            continue
        try:
            buttons.nth(card_index).scroll_into_view_if_needed()
            time.sleep(0.4)
            buttons.nth(card_index).click()
        except Exception as e:
            log(f"   -> klik gagal: {e} (percobaan {attempt+1})")
            time.sleep(2)
            continue
        try:
            page.wait_for_selector('.get-link-modal textarea', timeout=15000)
        except Exception:
            log(f"   -> modal tidak muncul (percobaan {attempt+1})")
            page.screenshot(path=os.path.join(os.path.dirname(__file__), 'offer_modal_error.png'))
            time.sleep(2)
            continue
        link = page.locator('.get-link-modal textarea').first.input_value().strip()
        # tutup modal
        try:
            page.locator('.ant-modal-close').first.click()
        except Exception:
            page.keyboard.press('Escape')
        for _ in range(20):  # tunggu modal benar-benar hilang
            if page.locator('.get-link-modal').count() == 0:
                break
            time.sleep(0.3)
        time.sleep(0.8)
        return link
    return None


def main():
    ap = argparse.ArgumentParser(description="Import produk dari Penawaran Produk Shopee + link affiliate ke PX STORE")
    ap.add_argument('--keyword', default='', help='kata kunci pencarian di Penawaran Produk (opsional)')
    ap.add_argument('--limit', type=int, default=10, help='jumlah produk per halaman (default 10)')
    ap.add_argument('--publish', action='store_true', help='langsung tayang (default: draft/sembunyi)')
    ap.add_argument('--dry', action='store_true', help='simulasi impor, tidak menyimpan')
    ap.add_argument('--no-link', action='store_true', help='lewati pembuatan link affiliate')
    args = ap.parse_args()

    if not os.path.exists(SHOPEE_PHP):
        print(f"PHP tidak ditemukan: {SHOPEE_PHP}"); sys.exit(1)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        context = launch_context(p)
        page = clean_pages(context)
        log("Membuka Penawaran Produk...")
        page.goto(OFFER_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_selector('.AffiliateItemCard', timeout=30000)
        except Exception:
            log("Kartu produk tidak muncul. Periksa sesi login / halaman.")
            page.screenshot(path=os.path.join(os.path.dirname(__file__), 'offer_error.png'))
            context.close(); sys.exit(1)
        time.sleep(3)
        if args.keyword:
            search_products(page, args.keyword)
            try:
                page.wait_for_selector('.AffiliateItemCard', timeout=30000)
            except Exception:
                log("Tidak ada hasil untuk kata kunci itu."); context.close(); sys.exit(1)
            time.sleep(2)

        cards = extract_cards(page)[:args.limit]
        log(f"Kartu terdeteksi: {len(cards)}")
        if not cards:
            context.close(); sys.exit(1)

        results = []
        for i, card in enumerate(cards, 1):
            name = card['name']
            price = parse_price(card['priceText'])
            log(f"[{i}/{len(cards)}] {name[:70]} | Rp{price:,.0f}")
            aff = None
            if not args.no_link:
                aff = click_buat_link(page, i - 1)
                if aff:
                    log(f"   -> {aff}")
                else:
                    log("   -> gagal ambil link, dilewati")
                    continue
            else:
                aff = card['detail']
            results.append({**card, 'price': price, 'affiliate_url': aff})

        context.close()

    if not results:
        print("Tidak ada produk yang berhasil diproses."); sys.exit(1)

    fd, csv_path = tempfile.mkstemp(suffix='.csv', prefix='shopee_offer_')
    with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Nama Produk', 'Harga', 'Link Universal (Affiliate)', 'Link Gambar 1', 'Kategori', 'Rating', 'Deskripsi Produk'])
        for r in results:
            desc = (f"{r['sold']}; {r['komisi']}").strip('; ')
            w.writerow([r['name'], r['price'], r['affiliate_url'], r['img'], 'Shopee Affiliate', 4.5, desc])

    log(f"CSV sementara: {csv_path}")
    cmd = [SHOPEE_PHP, IMPORT_PHP, csv_path]
    if args.publish:
        cmd.append('--publish')
    if args.dry:
        cmd.append('--dry')
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(p.stdout)
    if p.stderr:
        print(p.stderr)


if __name__ == '__main__':
    main()
