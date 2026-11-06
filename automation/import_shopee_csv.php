<?php
/* import_shopee_csv.php — Import produk dari ekspor CSV Shopee Affiliate Dashboard.
   Cara pakai: php import_shopee_csv.php file.csv [--dry] [--publish] [--limit=N]
   - Membaca CSV dengan header fleksibel (nama produk, harga, link, gambar, dll).
   - Harga diparse ("Rp 125.000" / "125000" -> 125000).
   - Duplikat dilewati berdasarkan URL.
   - Default: produk disembunyikan (visible=0) supaya bisa dicek dulu; --publish untuk langsung tampil.
   - --dry hanya menampilkan apa yang akan diimpor tanpa mengubah database. */

if (PHP_SAPI !== 'cli') { http_response_code(403); echo "Jalankan via CLI\n"; exit(1); }

require __DIR__ . '/../config.php';

$argv = $_SERVER['argv'] ?? [];
array_shift($argv);
$file = null; $dry = in_array('--dry', $argv, true); $publish = in_array('--publish', $argv, true); $limit = 500;
foreach ($argv as $arg) {
  if (strpos($arg, '--limit=') === 0) $limit = max(1, (int)substr($arg, 8));
  elseif (strpos($arg, '--') !== 0 && $file === null) $file = $arg;
}
if (!$file || !is_file($file)) {
  fwrite(STDERR, "File CSV tidak ditemukan. Contoh: php import_shopee_csv.php ekspor.csv --publish\n");
  exit(1);
}

/* ---------- normalisasi header ---------- */
function norm_key(string $s): string {
  $s = mb_strtolower($s, 'UTF-8');
  $s = preg_replace('/[^a-z0-9]+/', '_', $s) ?? $s;
  return trim($s, '_');
}
function pick(array $row, array $aliases): string {
  foreach ($aliases as $alias) {
    $k = norm_key($alias);
    if (isset($row[$k]) && trim((string)$row[$k]) !== '') return trim((string)$row[$k]);
  }
  return '';
}
function parse_price(string $s): int {
  $s = trim($s);
  if ($s === '') return 0;
  // ambil angka + separator, lalu normalisasi
  $s = str_replace(['Rp', 'IDR', ' '], '', $s);
  // format 125.000 (titik ribuan) atau 125,000
  $digits = preg_replace('/[^0-9,.\-]/', '', $s);
  $hasComma = strpos($digits, ',') !== false;
  $hasDot = strpos($digits, '.') !== false;
  if ($hasComma && $hasDot) {
    // asumsi titik ribuan & koma desimal (format id)
    $digits = str_replace('.', '', $digits);
    $digits = str_replace(',', '.', $digits);
  } elseif ($hasDot) {
    // 125.000 -> hapus titik (ribuan); 1234.5 kecil -> biarkan? harga selalu bulat
    $digits = str_replace('.', '', $digits);
  } elseif ($hasComma) {
    $digits = str_replace(',', '', $digits);
  }
  $n = (float)$digits;
  return $n > 0 ? (int)round($n) : 0;
}
function parse_url_string(string $s): string { return trim($s); }

/* ---------- baca CSV ---------- */
$fh = fopen($file, 'r');
if (!$fh) { fwrite(STDERR, "Tidak bisa membuka CSV\n"); exit(1); }
// deteksi BOM / separator
$firstLine = fgets($fh);
if ($firstLine === false) { fwrite(STDERR, "CSV kosong\n"); exit(1); }
$firstLine = preg_replace('/^\xEF\xBB\xBF/', '', $firstLine);
$delim = substr_count($firstLine, ';') > substr_count($firstLine, ',') ? ';' : ',';
if (substr_count($firstLine, "\t") > substr_count($firstLine, $delim)) $delim = "\t";
rewind($fh);

$headerLine = fgets($fh);
$headerLine = preg_replace('/^\xEF\xBB\xBF/', '', (string)$headerLine);
$headers = array_map('norm_key', str_getcsv($headerLine, $delim));

$imported = 0; $skipped = 0; $updated = 0; $errors = [];
$i = 0;
while (($line = fgets($fh)) !== false) {
  $i++;
  if ($i > $limit) break;
  $cols = str_getcsv($line, $delim);
  if (count($cols) < 2) continue;
  $row = [];
  foreach ($headers as $h => $k) $row[$k] = $cols[$h] ?? '';

  $name = pick($row, ['nama produk','nama','product name','name','produk']);
  $url  = pick($row, ['link universal (affiliate)','link affiliate','affiliate link','url','link','link produk']);
  $price = parse_price(pick($row, ['harga','price','harga produk']));
  $oldPrice = parse_price(pick($row, ['harga sebelum diskon','harga coret','old price','harga diskon (sebelumnya)']));
  $commission = parse_price(pick($row, ['komisi %','komisi','commission %','commission'])) ? pick($row, ['komisi %','komisi','commission']) : pick($row, ['komisi %','komisi','commission']);
  $image = pick($row, ['link gambar 1','gambar','foto','image','img url','image url','link foto']);
  $category = pick($row, ['kategori','kategori produk','category']);
  $rating = (float) str_replace(',', '.', pick($row, ['rating','rating produk']));
  $description = pick($row, ['deskripsi produk','deskripsi','description','deskripsi singkat']);
  $sold = pick($row, ['terjual bulanan','terjual','terjual bulan ini','total penjualan','sales']);

  if ($name === '' || $url === '') { $errors[] = "baris $i: nama atau link kosong -> dilewati"; $skipped++; continue; }
  if (!filter_var($url, FILTER_VALIDATE_URL)) { $errors[] = "baris $i: URL tidak valid ($url) -> dilewati"; $skipped++; continue; }

  if ($dry) {
    echo "[DRY] + $name | Rp" . number_format($price, 0, ',', '.') . " | $url\n";
    $imported++;
    continue;
  }

  // duplikat berdasarkan url
  $st = $pdo->prepare('SELECT id, name FROM products WHERE url = ? LIMIT 1');
  $st->execute([$url]);
  $existing = $st->fetch();
  $visible = $publish ? 1 : 0;
  $features = [];
  if ($sold !== '') $features[] = 'Terjual: ' . $sold;
  if ($commission !== '' && $commission !== null && $commission !== false) $features[] = 'Komisi: ' . $commission;
  $imageShort = $image !== '' ? $image : '🛍️';

  if ($existing) {
    $st = $pdo->prepare('UPDATE products SET name=?, price=?, old_price=?, image=?, images=?, category=?, rating=?, description=?, features=?, visible=? WHERE id=?');
    $st->execute([
      mb_substr($name, 0, 190),
      $price,
      $oldPrice,
      mb_substr($imageShort, 0, 500),
      json_encode([mb_substr($imageShort, 0, 500)], JSON_UNESCAPED_UNICODE),
      mb_substr($category !== '' ? $category : 'Shopee Affiliate', 0, 80),
      max(0, min(5, $rating ?: 0)),
      mb_substr($description, 0, 5000),
      $features ? json_encode($features, JSON_UNESCAPED_UNICODE) : null,
      $visible,
      (int)$existing['id'],
    ]);
    echo "UPDATE #{$existing['id']} {$existing['name']} -> {$name}\n";
    $updated++;
    continue;
  }

  $st = $pdo->prepare('INSERT INTO products (name, category, merchant, price, old_price, badge, image, images, rating, description, features, url, product_type, is_digital, visible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,\'affiliate\',0,?)');
  $st->execute([
    mb_substr($name, 0, 190),
    mb_substr($category !== '' ? $category : 'Shopee Affiliate', 0, 80),
    'Shopee',
    $price,
    $oldPrice,
    'Affiliate',
    mb_substr($imageShort, 0, 500),
    json_encode([mb_substr($imageShort, 0, 500)], JSON_UNESCAPED_UNICODE),
    max(0, min(5, $rating ?: 0)),
    mb_substr($description, 0, 5000),
    $features ? json_encode($features, JSON_UNESCAPED_UNICODE) : null,
    mb_substr($url, 0, 500),
    $visible,
  ]);
  $newId = (int)$pdo->lastInsertId();
  $code = 'AFF-' . str_pad((string)$newId, 4, '0', STR_PAD_LEFT);
  $pdo->prepare('UPDATE products SET product_code=? WHERE id=?')->execute([$code, $newId]);
  echo "INSERT {$code} {$name}\n";
  $imported++;
}
fclose($fh);

echo "\n=== SELESAI ===\n";
echo ($dry ? "Simulasi: " : "Hasil: ") . "{$imported} produk diimpor, {$updated} diperbarui, {$skipped} dilewati\n";
if ($errors) { echo "Catatan:\n- " . implode("\n- ", array_slice($errors, 0, 10)) . "\n"; }
if (!$publish && !$dry) echo "Produk baru disembunyikan dari publik (centang 'Tampilkan' di admin atau impor ulang dengan --publish).\n";
