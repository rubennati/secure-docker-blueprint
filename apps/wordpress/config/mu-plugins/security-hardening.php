<?php
/**
 * Security Hardening (Must-Use Plugin)
 *
 * Loaded automatically by WordPress. Cannot be deactivated via dashboard.
 * Mounted from config/mu-plugins/ into wp-content/mu-plugins/.
 *
 * What it does:
 * - Blocks REST API user enumeration for anonymous visitors
 * - Removes WordPress version from HTML, RSS, and HTTP headers
 * - Shows generic login error messages (no username/password hints)
 * - Disables XML-RPC (redundant with .htaccess, defense in depth)
 *
 * What it does NOT do:
 * - Block the entire REST API (WordPress needs it for Gutenberg,
 *   Loopback, WP-Cron, and Site Health checks)
 */

// ============================================================
// 1. Block REST API user enumeration for anonymous visitors
// ============================================================
// Only blocks /wp/v2/users — everything else stays open so that
// Gutenberg, Loopback, WP-Cron, and Site Health keep working.
add_filter('rest_endpoints', function ($endpoints) {
    if (!is_user_logged_in()) {
        // Remove user endpoints for anonymous visitors
        if (isset($endpoints['/wp/v2/users'])) {
            unset($endpoints['/wp/v2/users']);
        }
        if (isset($endpoints['/wp/v2/users/(?P<id>[\d]+)'])) {
            unset($endpoints['/wp/v2/users/(?P<id>[\d]+)']);
        }
    }
    return $endpoints;
});

// ============================================================
// 2. Remove WordPress version everywhere
// ============================================================
// HTML meta tag: <meta name="generator" content="WordPress 6.x">
remove_action('wp_head', 'wp_generator');

// RSS feed generator tag
add_filter('the_generator', '__return_empty_string');

// Version from scripts and styles (?ver=6.x.x)
add_filter('style_loader_src', 'blueprint_remove_version_query', 9999);
add_filter('script_loader_src', 'blueprint_remove_version_query', 9999);
function blueprint_remove_version_query($src) {
    if (strpos($src, 'ver=') !== false) {
        $src = remove_query_arg('ver', $src);
    }
    return $src;
}

// ============================================================
// 3. Generic login error message
// ============================================================
// Default: "Invalid username" or "Incorrect password" — reveals which is wrong.
// This replaces both with the same generic message.
add_filter('login_errors', function () {
    return 'Invalid credentials.';
});

// ============================================================
// 4. Disable XML-RPC (defense in depth — also blocked in .htaccess)
// ============================================================
add_filter('xmlrpc_enabled', '__return_false');
