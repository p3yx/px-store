"""Modul bersama untuk semua skrip PX STORE <-> Shopee.

- launch_context(): Chrome profil khusus, no_viewport=True (full window),
  bersihkan session/tabs restored, supaya tidak ada tab menumpuk.
- clean_pages(): tutup semua tab restored, kembalikan tepat 1 tab.
"""
import os

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

PROFILE_DIR = os.path.join(os.path.expanduser("~"), "pxstore-shopee-profile")


def wipe_session_restore():
    """Hapus file sesi agar Chrome tidak me-restore tab lama.
    Kuki & Local State TIDAK dihapus — login Shopee Anda tetap tersimpan."""
    default_dir = os.path.join(PROFILE_DIR, 'Default')
    if not os.path.isdir(default_dir):
        return
    for name in ['Current Session', 'Current Tabs', 'Last Session', 'Last Tabs', 'Sessions']:
        target = os.path.join(default_dir, name)
        try:
            if os.path.isdir(target):
                for f in os.listdir(target):
                    try:
                        os.remove(os.path.join(target, f))
                    except Exception:
                        pass
                try:
                    os.rmdir(target)
                except Exception:
                    pass
            elif os.path.isfile(target):
                os.remove(target)
        except Exception:
            # diamkan bila terkunci — Chrome akan tetap restore nanti ditangani clean_pages()
            pass


def launch_context(p):
    wipe_session_restore()
    kwargs = dict(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--start-maximized", "--disable-session-crashed-bubble", "--disable-infobars"],
        no_viewport=True,          # konten mengisi seluruh jendela, bukan 1280x720
    )
    if os.path.exists(CHROME_PATH):
        ctx = p.chromium.launch_persistent_context(executable_path=CHROME_PATH, **kwargs)
    else:
        ctx = p.chromium.launch_persistent_context(**kwargs)
    maximize_windows(ctx)
    return ctx


def maximize_windows(context):
    """Paksa semua jendela Chrome menjadi maximized via CDP."""
    for page in context.pages:
        try:
            session = context.new_cdp_session(page)
            win = session.send('Browser.getWindowForTarget')
            session.send('Browser.setWindowBounds', {
                'windowId': win['windowId'],
                'bounds': {'windowState': 'maximized'},
            })
        except Exception:
            # tidak fatal: jendela tetap terbuka meski tidak melebar
            pass


def clean_pages(context):
    """Tutup semua tab restored, sisakan tepat 1 tab di depan."""
    pages = list(context.pages)
    if not pages:
        return context.new_page()
    keep = pages[0]
    for pg in pages[1:]:
        try:
            pg.close()
        except Exception:
            pass
    try:
        keep.bring_to_front()
    except Exception:
        pass
    return keep
