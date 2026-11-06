<?php
/* recommend.php — Rekomendasi produk untuk dipromosikan (dibuat otomatis dari data toko).
   Cara pakai: php recommend.php [hari=7]
   Kriteria: rating tinggi, ada komisi/fitur terjual, murah -> prioritas dipromosikan.
   Output: file rekomendasi-*.txt di folder output/ + tampilkan di layar. */

if (PHP_SAPI !== 'cli') { http_response_code(403); echo "Jalankan via CLI\n"; exit(1); }
require __DIR__ . '/../config.php';

$outDir = __DIR__ . '/output';
if (!is_dir($outDir)) mkdir($outDir, 0777, true);

$rows = $pdo->query("SELECT product_code, name, price, rating, category, visible, features FROM products WHERE visible=1")->fetchAll();
if (!$rows) { echo "Belum ada produk tampil.\n"; exit(0); }

$scored = [];
foreach ($rows as $r) {
  $rating = (float)$r['rating'];
  $price = (int)$r['price'];
  $features = json_decode((string)($r['features'] ?? ''), true) ?: [];
  $terjual = 0; $komisi = '';
  foreach ($features as $f) {
    if (preg_match('/terjual\D*([0-9.,]+)/i', $f, $m)) $terjual = (float)str_replace(['.', ','], ['', '.'], $m[1]);
    if (stripos($f, 'komisi') !== false) $komisi = $f;
  }
  $score = $rating * 10;
  if ($terjual > 0) $score += min(30, log10(max(1, $terjual)) * 8);
  if ($price > 0 && $price <= 100000) $score += 8;   // harga terjangkau = konversi lebih mudah
  if ($price >= 100000) $score += 5;                 // margin lebih besar
  $scored[] = ['score' => $score, 'code' => $r['product_code'], 'name' => $r['name'], 'price' => $price, 'rating' => $rating, 'komisi' => $komisi, 'terjual' => $terjual];
}
usort($scored, fn($a, $b) => $b['score'] <=> $a['score']);

$lines = ["=== REKOMENDASI PRODUK DIPROMOSIKAN (otomatis) ===", "Diurutkan dari peluang terbaik (rating + terjual + harga).", ""];
foreach (array_slice($scored, 0, 10) as $i => $s) {
  $nr = $i + 1;
  $lines[] = "{$nr}. [{$s['code']}] {$s['name']}";
  $lines[] = "   Skor {$s['score']} | Rating {$s['rating']}/5 | Rp" . number_format($s['price'], 0, ',', '.');
  if ($s['terjual']) $lines[] = "   Terjual (log): sekitar " . number_format($s['terjual'], 0, ',', '.');
  if ($s['komisi']) $lines[] = "   {$s['komisi']}";
  $lines[] = "";
}
$text = implode("\n", $lines);
echo $text;
$file = $outDir . '/rekomendasi-' . date('Ymd-His') . '.txt';
file_put_contents($file, $text);
echo "Tersimpan: {$file}\n";
