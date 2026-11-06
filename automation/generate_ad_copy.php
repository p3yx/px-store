<?php
/* generate_ad_copy.php — Buat teks iklan/caption otomatis dari data produk di database.
   Cara pakai: php generate_ad_copy.php [AFF-0001 | 1] [--all] [--format=fb|ig|wa|semua]
   Output: teks siap pakai, tidak perlu API/internet. Simpan otomatis ke automation/output/<kode>-<format>.txt */

if (PHP_SAPI !== 'cli') { http_response_code(403); echo "Jalankan via CLI\n"; exit(1); }
require __DIR__ . '/../config.php';

$outDir = __DIR__ . '/output';
if (!is_dir($outDir)) mkdir($outDir, 0777, true);

$pick = null; $all = in_array('--all', $_SERVER['argv'] ?? [], true); $format = 'semua';
foreach (array_slice($_SERVER['argv'] ?? [], 1) as $arg) {
  if (strpos($arg, '--format=') === 0) $format = strtolower(substr($arg, 9));
  elseif (strpos($arg, '--') !== 0 && $pick === null) $pick = $arg;
}

function format_rupiah(int $n): string { return 'Rp ' . number_format($n, 0, ',', '.'); }

function ad_assets(array $p): array {
  $name = $p['name'];
  $price = (int)$p['price'];
  $old = (int)$p['old_price'];
  $priceFmt = format_rupiah($price);
  $oldFmt = format_rupiah($old - $price);
  $discount = $old > $price ? ' hemat ' . $oldFmt : '';
  $url = $p['url'];
  $rating = (float)$p['rating'];
  $features = json_decode((string)($p['features'] ?? ''), true) ?: [];
  $featList = implode(', ', array_slice($features, 0, 3));
  $featLine = $featList !== '' ? "Keunggulan: {$featList}. " : '';
  $short = mb_strlen($name) > 60 ? mb_substr($name, 0, 60) . '…' : $name;

  return [
    'fb' => "🔥 {$name}\n" .
            "{$featLine}Cuma {$priceFmt}{$discount}.\n" .
            "Rating {$rating}/5 — dipercaya pembeli.\n" .
            "Klik link & pesan sekarang: {$url}\n" .
            "(promo dapat berubah sewaktu-waktu)",
    'ig' => "{$name} ✨\n" .
            "{$featLine}Harga {$priceFmt}{$discount}.\n" .
            "⭐ {$rating}/5 — worth it buat kamu yang butuh ini sekarang.\n" .
            "Cek langsung → link di bio / klik: {$url}\n" .
            "#affiliate #shopeehaul #belanjaonline #diskon",
    'wa' => "Hai! Lagi cari {$short}? Ini di Shopee dengan harga {$priceFmt}{$discount}. {$featLine}Rating {$rating}/5. Yuk klik: {$url}",
    'caption' => "{$name} — {$priceFmt}{$discount}. {$featLine}Rating {$rating}/5. Beli di merchant lewat link: {$url}",
  ];
}

if ($all) {
  $rows = $pdo->query("SELECT * FROM products WHERE visible=1 ORDER BY id DESC")->fetchAll();
} elseif ($pick) {
  $id = (int) preg_replace('/[^0-9]/', '', $pick);
  $st = $pdo->prepare("SELECT * FROM products WHERE id=? OR UPPER(product_code)=UPPER(?) LIMIT 1");
  $st->execute([$id ?: 0, $pick]);
  $rows = $st->fetchAll();
} else {
  $rows = $pdo->query("SELECT * FROM products WHERE visible=1 ORDER BY id DESC LIMIT 10")->fetchAll();
}
if (!$rows) { echo "Produk tidak ditemukan.\n"; exit(1); }

foreach ($rows as $p) {
  $a = ad_assets($p);
  $code = $p['product_code'] ?: ('ID-' . $p['id']);
  $which = $format === 'semua' ? array_keys($a) : [$format];
  foreach ($which as $f) {
    if (!isset($a[$f])) continue;
    $file = $outDir . '/' . $code . '-' . $f . '.txt';
    file_put_contents($file, $a[$f]);
    echo "=== {$code} ({$f}) ===\n{$a[$f]}\n\n";
    echo "Tersimpan: {$file}\n\n";
  }
}
echo "Selesai. Salin teks di atas atau ambil dari folder automation/output/.\n";
