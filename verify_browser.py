import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopee_common import launch_context, clean_pages
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    ctx = launch_context(p)
    page = clean_pages(ctx)
    page.goto("https://affiliate.shopee.co.id/offer/product_offer", wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)
    print("JUMLAH TAB TERBUKA:", len(ctx.pages))
    size = page.evaluate("() => ({w: window.innerWidth, h: window.innerHeight, outerW: window.outerWidth, outerH: window.outerHeight})")
    print("innerWidth:", size['w'], "innerHeight:", size['h'])
    print("outerWidth:", size['outerW'], "outerHeight:", size['outerH'])
    screen = page.evaluate("() => ({w: screen.width, h: screen.height})")
    print("screen:", screen)
    for pg in ctx.pages:
        print("tab:", (pg.title() or pg.url)[:60])
    ctx.close()
