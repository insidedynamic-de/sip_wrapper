<?php
// update-landing.php
// Webhook to auto-update landing files from GitHub
// URL: https://your-domain.com/update-landing.php?token=SECRET_TOKEN

$secret_token = 'CHANGE_THIS_SECRET_123'; // <-- CHANGE THIS!
// Landing URL: https://1ait.eu/products/sip-wraper
$landing_dir = __DIR__;
$repo_url = 'https://raw.githubusercontent.com/insidedynamic-de/sip_wrapper/main/landing/';

// Security check
if (!isset($_GET['token']) || $_GET['token'] !== $secret_token) {
    http_response_code(403);
    die('Forbidden');
}

$files = [
    'landing.html' => 'index.html',
    'integrations.js' => 'integrations.js'
];

$updated = [];
$errors = [];

foreach ($files as $source => $dest) {
    $content = @file_get_contents($repo_url . $source);
    if ($content !== false) {
        if (file_put_contents($landing_dir . '/' . $dest, $content) !== false) {
            $updated[] = $dest;
        } else {
            $errors[] = "Failed to write: $dest";
        }
    } else {
        $errors[] = "Failed to fetch: $source";
    }
}

header('Content-Type: application/json');
echo json_encode([
    'status' => empty($errors) ? 'ok' : 'partial',
    'updated' => $updated,
    'errors' => $errors,
    'time' => date('Y-m-d H:i:s')
], JSON_PRETTY_PRINT);
