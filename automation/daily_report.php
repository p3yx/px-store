<?php
/* daily_report.php — Ringkasan toko otomatis (order, omzet, produk).
   Cara pakai: php daily_report.php [hari=7] [--telegram]
   --telegram kirim ke bot Telegram hanya jika env PXAFF_TELEGRAM_BOT_TOKEN & PXAFF_TELEGRAM_CHAT_ID diset. */

if (PHP_SAPI !== 'cli') { http_response_code(403); echo "Jalankan via CLI\n"; exit(1); }
require __DIR__ . '/../config.php';

$days = 7; $toTelegram = in_array('--telegram', $_SERVER['argv'] ?? [], true);
foreach (array_slice($_SERVER['argv'] ?? [], 1) as $arg) if (is_numeric($arg)) $days = max(1, min(365, (int)$arg));
$days = (int)$days;
$outDir = __DIR__ . '/output';
if (!is_dir($outDir)) mkdir($outDir, 0777, true);

$since = (new DateTime('-' . $days . ' days'))->format('Y-m-d H:i:s');

$pCount = (int)$pdo->query('SELECT COUNT(*) FROM products')->fetchColumn();
$pVisible = (int)$pdo->query('SELECT COUNT(*) FROM products WHERE visible=1')->fetchColumn();
$pAff = (int)$pdo->query("SELECT COUNT(*) FROM products WHERE product_type='affiliate'")->fetchColumn();
$pDig = (int)$pdo->query("SELECT COUNT(*) FROM products WHERE is_digital=1")->fetchColumn();

$st = $pdo->prepare("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS rev FROM orders WHERE payment_status='paid' AND created_at >= ?");
$st->execute([$since]); $ord = $st->fetch();
$st = $pdo->prepare("SELECT COUNT(*) FROM orders WHERE payment_status='pending' AND created_at >= ?");
$st->execute([$since]); $pending = (int)$st->fetchColumn();
$st = $pdo->prepare("SELECT product_name, SUM(quantity) qty, SUM(total) rev FROM orders WHERE payment_status='paid' AND created_at >= ? GROUP BY product_name ORDER BY qty DESC LIMIT 5");
$st->execute([$since]); $top = $st->fetchAll();

$lines = [];
$lines[] = "=== LAPORAN PX STORE ({$days} hari terakhir) ===";
$lines[] = "Produk: {$pCount} total | {$pVisible} tampil | {$pAff} affiliate | {$pDig} digital";
$lines[] = "Order lunas: " . (int)$ord['n'] . " | Omzet: Rp" . number_format((float)$ord['rev'], 0, ',', '.');
$lines[] = "Order pending: {$pending} (cek di tab Pesanan)";
if ($top) {
  $lines[] = "Produk terjual:";
  foreach ($top as $t) $lines[] = "  • {$t['product_name']} — {$t['qty']} unit (Rp" . number_format((float)$t['rev'], 0, ',', '.') . ")";
} else {
  $lines[] = "Produk terjual: belum ada penjualan tercatat (wajar untuk toko afiliasi yang baru mulai; klik affiliate bukan pesanan).";
}
$text = implode("\n", $lines);
echo $text . "\n";

file_put_contents(__DIR__ . '/output/laporan-' . date('Ymd-His') . '.txt', $text);

if ($toTelegram) {
  $token = trim((string)getenv('PXAFF_TELEGRAM_BOT_TOKEN'));
  $chat = trim((string)getenv('PXAFF_TELEGRAM_CHAT_ID'));
  if ($token === '' || $chat === '') { echo "\nTelegram: env PXAFF_TELEGRAM_BOT_TOKEN / PXAFF_TELEGRAM_CHAT_ID belum diset.\n"; exit(0); }
  $url = 'https://api.telegram.org/bot' . rawurlencode($token) . '/sendMessage';
  $ctx = stream_context_create(['http' => ['method' => 'POST', 'header' => "Content-Type: application/x-www-form-urlencoded\r\n", 'content' => http_build_query(['chat_id' => $chat, 'text' => $text]), 'ignore_errors' => true]]);
  @file_get_contents($url, false, $ctx);
  echo "\nLaporan terkirim ke Telegram.\n";
}
