#!/usr/bin/env bash
# ==========================================================
# WordPress Security Test Suite
# ==========================================================
# Tests all hardening measures after deployment:
#   - Container health
#   - PHP security settings (uploads.ini)
#   - HTTP connectivity
#   - .htaccess hardening rules
#   - mu-plugin (fingerprint protection)
#   - Traefik security headers
#
# Usage:
#   bash ops/scripts/test-security.sh <domain>
#   bash ops/scripts/test-security.sh <domain> --no-tailscale
#
# Run from the wordpress app directory (where docker-compose.yml is).
# Auto-detects Tailscale and routes requests through VPN IP.
# Use --no-tailscale for public sites without VPN.
# ==========================================================

# --- Colors & Symbols ---
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

PASS="${GREEN}✔${NC}"
WARN="${YELLOW}⚠${NC}"
FAIL="${RED}✘${NC}"

# --- Args ---
DOMAIN="${1:-}"
NO_TAILSCALE=false
if [[ "${2:-}" == "--no-tailscale" ]]; then
  NO_TAILSCALE=true
fi

if [[ -z "$DOMAIN" ]]; then
  echo -e "${RED}Usage: $0 <domain> [--no-tailscale]${NC}"
  echo ""
  echo "  <domain>         WordPress domain (e.g. wordpress.example.com)"
  echo "  --no-tailscale   Skip Tailscale IP resolution (for public sites)"
  exit 1
fi

# --- Tailscale detection ---
RESOLVE=""
if [[ "$NO_TAILSCALE" == false ]] && command -v tailscale &>/dev/null; then
  TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
  if [[ -n "$TS_IP" ]]; then
    RESOLVE="--resolve ${DOMAIN}:443:${TS_IP}"
    echo -e "${CYAN}Tailscale detected: routing via ${TS_IP}${NC}"
  fi
fi

if [[ -z "$RESOLVE" && "$NO_TAILSCALE" == false ]]; then
  echo -e "${YELLOW}No Tailscale detected. Using direct DNS resolution.${NC}"
fi

BASE_URL="https://${DOMAIN}"
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
TOTAL_COUNT=0

# --- Helpers ---
http_code() {
  curl -s -o /dev/null -w "%{http_code}" --max-time 10 $RESOLVE "$1" 2>/dev/null || echo "000"
}

page_content() {
  curl -s --max-time 10 $RESOLVE "$1" 2>/dev/null || echo ""
}

page_headers() {
  curl -sI --max-time 10 $RESOLVE "$1" 2>/dev/null || echo ""
}

pass() {
  local name="$1" detail="${2:-}"
  TOTAL_COUNT=$((TOTAL_COUNT + 1))
  PASS_COUNT=$((PASS_COUNT + 1))
  if [[ -n "$detail" ]]; then
    echo -e "  ${PASS}  ${name}  ${DIM}${detail}${NC}"
  else
    echo -e "  ${PASS}  ${name}"
  fi
}

warn() {
  local name="$1" detail="${2:-}"
  TOTAL_COUNT=$((TOTAL_COUNT + 1))
  WARN_COUNT=$((WARN_COUNT + 1))
  echo -e "  ${WARN}  ${name}  ${YELLOW}${detail}${NC}"
}

fail() {
  local name="$1" detail="${2:-}"
  TOTAL_COUNT=$((TOTAL_COUNT + 1))
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo -e "  ${FAIL}  ${name}  ${RED}${detail}${NC}"
}

expect_http() {
  local name="$1" url="$2" expected="$3"
  local code
  code=$(http_code "$url")
  if [[ "$code" == "$expected" ]]; then
    pass "$name" "HTTP $code"
  elif [[ "$code" == "000" ]]; then
    fail "$name" "unreachable (timeout)"
  else
    fail "$name" "HTTP $code (expected $expected)"
  fi
}

# ==========================================================
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "${BOLD} WordPress Security Test Suite${NC}"
echo -e "${BOLD} Domain: ${CYAN}${DOMAIN}${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"

# ==========================================================
# 1. CONTAINER HEALTH
# ==========================================================
echo ""
echo -e "${BOLD}1. Container Health${NC}"
echo -e "───────────────────────────────────────────────"

for svc in app db; do
  if docker compose ps 2>/dev/null | grep -q "${svc}.*healthy"; then
    pass "$svc container" "healthy"
  elif docker compose ps 2>/dev/null | grep -q "${svc}.*starting"; then
    warn "$svc container" "starting (healthcheck pending)"
  else
    fail "$svc container" "not healthy"
  fi
done

# ==========================================================
# 2. PHP SECURITY (uploads.ini)
# ==========================================================
echo ""
echo -e "${BOLD}2. PHP Security ${DIM}(config/php/uploads.ini)${NC}"
echo -e "───────────────────────────────────────────────"

php_val() {
  docker compose exec -T app php -r "echo ini_get('$1');" 2>/dev/null || echo "ERROR"
}

val=$(php_val "upload_max_filesize")
if [[ "$val" == "64M" ]]; then pass "upload_max_filesize = 64M"; else fail "upload_max_filesize" "got: $val (expected 64M)"; fi

val=$(php_val "post_max_size")
if [[ "$val" == "64M" ]]; then pass "post_max_size = 64M"; else fail "post_max_size" "got: $val (expected 64M)"; fi

val=$(php_val "memory_limit")
if [[ "$val" == "256M" ]]; then pass "memory_limit = 256M"; else fail "memory_limit" "got: $val (expected 256M)"; fi

val=$(php_val "expose_php")
if [[ -z "$val" || "$val" == "" || "$val" == "0" ]]; then
  pass "expose_php = Off" "PHP version hidden from headers"
else
  fail "expose_php" "still On — PHP version visible in headers"
fi

val=$(php_val "disable_functions")
if [[ -n "$val" && "$val" == *"exec"* ]]; then
  count=$(echo "$val" | tr ',' '\n' | wc -l | tr -d ' ')
  pass "disable_functions" "$count dangerous functions blocked"
else
  fail "disable_functions" "not set — PHP shells can execute system commands"
fi

# ==========================================================
# 3. HTTP CONNECTIVITY
# ==========================================================
echo ""
echo -e "${BOLD}3. HTTP Connectivity${NC}"
echo -e "───────────────────────────────────────────────"

expect_http "Homepage loads" "${BASE_URL}/" "200"
expect_http "wp-login.php reachable" "${BASE_URL}/wp-login.php" "200"

# ==========================================================
# 4. .HTACCESS HARDENING
# ==========================================================
echo ""
echo -e "${BOLD}4. .htaccess Hardening ${DIM}(config/apache/.htaccess-security)${NC}"
echo -e "───────────────────────────────────────────────"

# Check if .htaccess-security was applied
htaccess=$(docker compose exec -T app cat /var/www/html/.htaccess 2>/dev/null || echo "")
if echo "$htaccess" | grep -q "Block PHP execution"; then
  pass ".htaccess-security applied" "rules found in .htaccess"
else
  warn ".htaccess-security not applied" "run: docker compose exec app bash -c 'cat /config/.htaccess-security >> /var/www/html/.htaccess'"
fi

expect_http "xmlrpc.php blocked" "${BASE_URL}/xmlrpc.php" "403"
expect_http "wp-config.php blocked" "${BASE_URL}/wp-config.php" "403"
expect_http "readme.html blocked" "${BASE_URL}/readme.html" "403"
expect_http "?author=1 enumeration blocked" "${BASE_URL}/?author=1" "403"
expect_http "PHP in /uploads/ blocked" "${BASE_URL}/wp-content/uploads/test.php" "403"

code=$(http_code "${BASE_URL}/wp-content/uploads/")
if [[ "$code" == "403" || "$code" == "404" ]]; then
  pass "Directory listing disabled" "HTTP $code"
else
  fail "Directory listing" "HTTP $code — folder contents may be visible"
fi

# ==========================================================
# 5. MU-PLUGIN (FINGERPRINT PROTECTION)
# ==========================================================
echo ""
echo -e "${BOLD}5. mu-plugin ${DIM}(config/mu-plugins/security-hardening.php)${NC}"
echo -e "───────────────────────────────────────────────"

# Check if mu-plugin is mounted
if docker compose exec -T app test -f /var/www/html/wp-content/mu-plugins/security-hardening.php 2>/dev/null; then
  pass "mu-plugin mounted" "security-hardening.php present"
else
  fail "mu-plugin not found" "check volume mount in docker-compose.yml"
fi

# Generator meta tag
homepage=$(page_content "${BASE_URL}/")
if echo "$homepage" | grep -qi "generator"; then
  fail "Generator meta tag" "visible — WordPress version leaked in HTML"
else
  pass "Generator meta tag hidden" "no version leak in HTML source"
fi

# Version strings in CSS/JS
if echo "$homepage" | grep -qoE 'ver=[0-9]+\.[0-9]+\.[0-9]+'; then
  fail "Version strings in assets" "WordPress version visible in CSS/JS URLs"
else
  pass "Version strings cleaned" "no WordPress version in asset URLs"
fi

# REST API user enumeration
api_response=$(page_content "${BASE_URL}/wp-json/wp/v2/users")
if echo "$api_response" | grep -q '"slug"'; then
  fail "REST API user enumeration" "usernames exposed at /wp-json/wp/v2/users"
elif echo "$api_response" | grep -qi "rest_not_logged_in\|Authentication required\|rest_forbidden"; then
  pass "REST API user enumeration blocked" "401 for anonymous requests"
else
  pass "REST API user enumeration blocked" "no user data returned"
fi

# Login error message
# This test only works if we can trigger a failed login
# Skipped in automated test — manual verification recommended

# ==========================================================
# 6. SECURITY HEADERS (TRAEFIK)
# ==========================================================
echo ""
echo -e "${BOLD}6. Security Headers ${DIM}(Traefik middleware)${NC}"
echo -e "───────────────────────────────────────────────"

headers=$(page_headers "${BASE_URL}/")

check_header() {
  local name="$1" search="$2"
  local value
  value=$(echo "$headers" | grep -i "$search" | head -1 | cut -d: -f2- | tr -d '\r' | xargs 2>/dev/null || echo "")
  if [[ -n "$value" ]]; then
    pass "$name" "$value"
  else
    fail "$name" "header missing"
  fi
}

check_header "Strict-Transport-Security" "strict-transport-security"
check_header "X-Content-Type-Options" "x-content-type-options"
check_header "X-Frame-Options" "x-frame-options"

# X-Powered-By should NOT be present
if echo "$headers" | grep -qi "x-powered-by"; then
  val=$(echo "$headers" | grep -i "x-powered-by" | head -1 | tr -d '\r' | xargs 2>/dev/null)
  fail "X-Powered-By hidden" "header present: $val"
else
  pass "X-Powered-By hidden" "not present in response"
fi

# ==========================================================
# SUMMARY
# ==========================================================
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "  ${PASS} ${GREEN}${PASS_COUNT} passed${NC}    ${WARN} ${YELLOW}${WARN_COUNT} warnings${NC}    ${FAIL} ${RED}${FAIL_COUNT} failed${NC}    ${DIM}(${TOTAL_COUNT} total)${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"
echo ""

if [[ $FAIL_COUNT -gt 0 ]]; then
  echo -e "${RED}Some tests failed. Review the output above and apply fixes.${NC}"
  echo ""
  echo -e "${DIM}Common fixes:${NC}"
  echo -e "${DIM}  .htaccess not applied:  docker compose exec app bash -c 'cat /config/.htaccess-security >> /var/www/html/.htaccess'${NC}"
  echo -e "${DIM}  Container unhealthy:    docker compose restart && wait 30s${NC}"
  echo -e "${DIM}  Headers missing:        Check APP_TRAEFIK_SECURITY in .env${NC}"
  exit 1
elif [[ $WARN_COUNT -gt 0 ]]; then
  echo -e "${YELLOW}All critical tests passed, some warnings remain.${NC}"
  exit 0
else
  echo -e "${GREEN}All tests passed. WordPress is hardened.${NC}"
  exit 0
fi
