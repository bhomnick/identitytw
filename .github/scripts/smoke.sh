#!/usr/bin/env bash
# Verifies a deployed site and/or API by fetching real pages.
#
#   .github/scripts/smoke.sh --site https://identity.tw --api https://v.identity.tw
#
# Each check retries (SMOKE_RETRIES, default 10, six seconds apart) so a deploy
# that is still propagating does not fail the job. Exits non-zero if any check
# fails.
set -euo pipefail

SITE=""
API=""
while [ $# -gt 0 ]; do
  case "$1" in
    --site) SITE="${2%/}"; shift 2 ;;
    --api)  API="${2%/}";  shift 2 ;;
    *) echo "usage: $0 [--site URL] [--api URL]" >&2; exit 2 ;;
  esac
done
[ -n "$SITE$API" ] || { echo "usage: $0 [--site URL] [--api URL]" >&2; exit 2; }

failures=0
retries="${SMOKE_RETRIES:-10}"

# check NAME URL EXPECTED_STATUS SUBSTRING
check() {
  local name="$1" url="$2" want="$3" pattern="$4" attempt response code body
  for attempt in $(seq 1 "$retries"); do
    response="$(curl -sS -m 20 -w $'\n%{http_code}' "$url" 2>/dev/null || true)"
    code="${response##*$'\n'}"
    body="${response%$'\n'*}"
    # A plain substring test: piping a large page into grep -q trips pipefail via SIGPIPE.
    if [ "$code" = "$want" ] && [[ "$body" == *"$pattern"* ]]; then
      echo "ok    $name"
      return 0
    fi
    [ "$attempt" -lt "$retries" ] && sleep 6
  done
  echo "FAIL  $name: $url returned HTTP ${code:-none}, expected $want containing: $pattern"
  failures=$((failures + 1))
}

if [ -n "$SITE" ]; then
  echo "site: $SITE"
  check "english index"   "$SITE/"               200 '<html lang="en">'
  check "chinese index"   "$SITE/zh-hant/"       200 '<html lang="zh-Hant">'
  check "providers.json"  "$SITE/providers.json" 200 '"grade"'
  check "sitemap"         "$SITE/sitemap.xml"    200 '<urlset'
  check "stylesheet"      "$SITE/static/site.css" 200 ':root'
  check "script"          "$SITE/static/site.js" 200 'report-search'
  slug="$(curl -sS -m 20 "$SITE/providers.json" 2>/dev/null \
    | python3 -c 'import json, sys, urllib.parse; print(urllib.parse.quote(json.load(sys.stdin)[0]["slug"]))' 2>/dev/null || true)"
  if [ -n "$slug" ]; then
    check "provider page"  "$SITE/providers/$slug/"         200 'criteria-table'
    check "provider (zh)"  "$SITE/zh-hant/providers/$slug/" 200 '<html lang="zh-Hant">'
  else
    echo "FAIL  provider page: could not read a slug from providers.json"
    failures=$((failures + 1))
  fi
  if [ "$SITE" = "https://identity.tw" ]; then
    location="$(curl -sS -m 20 -o /dev/null -w '%{redirect_url}' https://www.identity.tw/ 2>/dev/null || true)"
    if [ "$location" = "https://identity.tw/" ]; then
      echo "ok    www redirect"
    else
      echo "FAIL  www redirect: https://www.identity.tw/ redirected to '${location:-nothing}', expected https://identity.tw/"
      failures=$((failures + 1))
    fi
  fi
fi

if [ -n "$API" ]; then
  echo "api: $API"
  check "valid id"        "$API/?id=A123456789" 200 '"valid": true'
  check "invalid id"      "$API/?id=A123456788" 200 '"valid": false'
  check "legacy arc"      "$API/?id=AB12345677" 200 '"valid": true'
  check "new arc"         "$API/?id=A800000014" 200 '"valid": true'
  check "missing id"      "$API/"               400 'Must provide ID parameter'
fi

if [ "$failures" -gt 0 ]; then
  echo "$failures check(s) failed"
  exit 1
fi
echo "all checks passed"
