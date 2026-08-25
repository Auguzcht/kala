#!/usr/bin/env bash
# Fast pre-flight: env vars present + api/worker boot cleanly. Run before
# starting dev so config drift fails fast, before you're 20 minutes into a
# debugging session that turns out to be a missing .env line.
set -uo pipefail   # no -e: we want every section to run and report, not stop at the first failure

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$ROOT_DIR/services/api"
WORKER_DIR="$ROOT_DIR/services/worker"

# Source .env files directly instead of hand-parsing them. This correctly
# handles multi-line quoted values (LTI_TOOL_PRIVATE_KEY_PEM's PEM block) —
# a line-by-line KEY=value parser silently truncates those, since only the
# opening line matches a `KEY=` pattern and every continuation line is
# dropped. `set -a` exports everything the file defines; `set +a` stops.
load_env() {
  local file="$1"
  [ -f "$file" ] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}
load_env "$ROOT_DIR/.env"
load_env "$API_DIR/.env"
load_env "$WORKER_DIR/.env"

API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8000/health}"
AWS_REGION="${AWS_REGION:-ap-southeast-1}"
REQUIRED_VARS="${REQUIRED_VARS:-SUPABASE_URL SUPABASE_SERVICE_KEY SUPABASE_JWT_SECRET AWS_REGION BEDROCK_MODEL_DEFAULT BEDROCK_EMBED_MODEL LTI_ISSUER LTI_CLIENT_ID LMS_REST_CLIENT_ID LMS_REST_CLIENT_SECRET LMS_REST_BASE_URL LTI_AUTH_LOGIN_URL LTI_AUTH_TOKEN_URL LTI_KEYSET_URL LTI_DEPLOYMENT_IDS LTI_TOOL_PRIVATE_KEY_PEM}"

OVERALL_STATUS=0
pass() { echo "  OK   $1"; }
fail() { echo "  FAIL $1"; OVERALL_STATUS=1; }
warn() { echo "  WARN $1"; }

echo "== 0. Required env vars =="
missing=0
for name in $REQUIRED_VARS; do
  value="${!name:-}"
  if [ -z "$value" ]; then
    fail "missing env var: $name"
    missing=1
  fi
done
[ "$missing" -eq 0 ] && pass "required env vars present"

# Sanity-check the PEM specifically: this is the value the old parser used
# to silently truncate, so verify it actually has a BEGIN and END line, not
# just that it's non-empty.
if [ -n "${LTI_TOOL_PRIVATE_KEY_PEM:-}" ]; then
  if echo "$LTI_TOOL_PRIVATE_KEY_PEM" | grep -q "BEGIN RSA PRIVATE KEY" \
     && echo "$LTI_TOOL_PRIVATE_KEY_PEM" | grep -q "END RSA PRIVATE KEY"; then
    pass "LTI_TOOL_PRIVATE_KEY_PEM has both BEGIN and END markers"
  else
    fail "LTI_TOOL_PRIVATE_KEY_PEM looks truncated (missing BEGIN/END marker)"
  fi
fi

echo "== 1. API service =="
if (cd "$API_DIR" && uv run python -c 'from app.main import app; print(app.title)') >/dev/null 2>&1; then
  pass "api imports successfully"
else
  fail "api import check failed"
fi
if curl -fsS --connect-timeout 5 --max-time 15 "$API_HEALTH_URL" >/dev/null 2>&1; then
  pass "api health responds"
else
  fail "api health unreachable: $API_HEALTH_URL (is uvicorn running?)"
fi

echo "== 2. Worker service =="
if (cd "$WORKER_DIR" && uv run python -c 'from app.handler import handler; handler({}, None)') >/dev/null 2>&1; then
  pass "worker handler runs"
else
  fail "worker handler failed"
fi

echo "== 3. Shared env sanity =="
if [ -n "${SUPABASE_URL:-}" ] && [ -n "${SUPABASE_SERVICE_KEY:-}" ] && [ -n "${SUPABASE_JWT_SECRET:-}" ]; then
  pass "supabase env present"
else
  fail "supabase env incomplete"
fi
if [ -n "${LTI_CLIENT_ID:-}" ] && [ -n "${LMS_REST_BASE_URL:-}" ] && [ -n "${LMS_REST_CLIENT_ID:-}" ] && [ -n "${LMS_REST_CLIENT_SECRET:-}" ]; then
  pass "lms/lti env present"
else
  fail "lms/lti env incomplete"
fi

echo "== 4. AWS config =="
if [ -n "${AWS_REGION:-}" ]; then
  pass "aws region set: $AWS_REGION"
else
  fail "aws region missing"
fi

echo
if [ "$OVERALL_STATUS" -eq 0 ]; then
  echo "Done. All checks passed."
else
  echo "Done. One or more checks FAILED — see above. Exiting non-zero so CI/scripts can detect it."
fi
exit "$OVERALL_STATUS"
