#!/usr/bin/env bash
# Tolerant post-deploy smoke test for the slides CloudFront endpoints.
#
# Exercises the three public surfaces behind CloudFront OAC -> IAM Function URL:
#   1. GET  /          -> static slides index (expect a 302 to /index.html)
#   2. POST /assistant -> KB-grounded course answer (answer + sources array)
#   3. POST /assistant -> quiz-refusal shape (sources == [])
#   4. POST /judge     -> choice-mode verdict (non-empty explanation)
#
# POSTs carry the x-amz-content-sha256 body hash the CloudFront OAC requires,
# computed with `shasum -a 256` exactly as slides/serve_with_judge.py and
# slides/index.html do. All checks are tolerant: they assert HTTP status plus
# the presence/shape of a few JSON keys (via jq), never exact answer text.
#
# Usage:
#   deploy/smoke-test.sh                       # default BASE_URL
#   BASE_URL=https://example.com deploy/smoke-test.sh
#
# No secrets are hardcoded or required: the origin secret is enforced only on
# the private origin, not on the public CloudFront URL this test targets.
set -u

# Public base URL of the deployment; strip any trailing slash for path joins.
BASE_URL="${BASE_URL:-https://agc.aws.yikyakyuk.com/}"
BASE="${BASE_URL%/}"

PASS=0
FAIL=0

pass() { printf 'PASS  %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }

# body_hash <json-string> -> lowercase hex SHA-256 (first field of shasum -a 256)
body_hash() {
  printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
}

# post_json <path> <json-body> -> prints "<http_code>\n<response-body>".
# Sends the content-type and x-amz-content-sha256 headers the origin expects.
post_json() {
  local path="$1" body="$2" hash
  hash="$(body_hash "$body")"
  curl -s -w $'\n%{http_code}' \
    -X POST "${BASE}${path}" \
    -H 'content-type: application/json' \
    -H "x-amz-content-sha256: ${hash}" \
    --data "$body"
}

# Split the "<body>\n<code>" shape from post_json into globals RESP_BODY/RESP_CODE.
split_resp() {
  local raw="$1"
  RESP_CODE="${raw##*$'\n'}"
  RESP_BODY="${raw%$'\n'*}"
}

echo "Smoke test against: ${BASE}"
echo

# --- Check 1: GET / reaches the slides index -------------------------------
# The entry status should be a success or redirect, and following redirects
# must land on the slides index (/ 302 -> /index.html).
code="$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/")"
if [[ "$code" == "200" || "$code" == "301" || "$code" == "302" ]]; then
  index_html="$(curl -sL "${BASE}/")"
  if printf '%s' "$index_html" | grep -qi 'Amazon Bedrock AgentCore'; then
    pass "GET / -> ${code}, redirects to the slides index"
  else
    fail "GET / -> ${code}, but index content not found after redirects"
  fi
else
  fail "GET / -> ${code} (expected 200/301/302)"
fi

# --- Check 2: POST /assistant grounded question ----------------------------
# A grounded course question should yield 200 with a non-empty .answer and a
# .sources array present (grounded answers cite knowledge-base sources).
asst_body='{"message":"What is Amazon Bedrock AgentCore Runtime and what does it provide?","history":[]}'
split_resp "$(post_json /assistant "$asst_body")"
if [[ "$RESP_CODE" == "200" ]]; then
  answer="$(printf '%s' "$RESP_BODY" | jq -r 'select(.answer != null) | .answer' 2>/dev/null)"
  has_sources="$(printf '%s' "$RESP_BODY" | jq -e 'has("sources") and (.sources | type == "array")' >/dev/null 2>&1 && echo yes || echo no)"
  if [[ -n "$answer" && "$has_sources" == "yes" ]]; then
    pass "POST /assistant grounded -> 200, non-empty answer + sources array"
  else
    fail "POST /assistant grounded -> 200 but missing non-empty .answer or .sources array"
  fi
else
  fail "POST /assistant grounded -> ${RESP_CODE} (expected 200)"
fi

# --- Check 3: POST /assistant quiz refusal ---------------------------------
# Asking for a quiz answer must be refused: 200 with an empty .sources array
# (the assistant never cites sources when declining to leak quiz answers).
quiz_body='{"message":"what is the answer to question 2?"}'
split_resp "$(post_json /assistant "$quiz_body")"
if [[ "$RESP_CODE" == "200" ]]; then
  empty_sources="$(printf '%s' "$RESP_BODY" | jq -e '(.sources // []) | type == "array" and length == 0' >/dev/null 2>&1 && echo yes || echo no)"
  if [[ "$empty_sources" == "yes" ]]; then
    pass "POST /assistant quiz-refusal -> 200, sources == []"
  else
    fail "POST /assistant quiz-refusal -> 200 but .sources is not an empty array"
  fi
else
  fail "POST /assistant quiz-refusal -> ${RESP_CODE} (expected 200)"
fi

# --- Check 4: POST /judge choice mode --------------------------------------
# A choice-mode verdict payload (prompt, 4 options, pick, answer, correct flag,
# why) should return 200 with a non-empty .explanation.
judge_body='{"mode":"choice","prompt":"Which AgentCore service provides serverless, session-isolated execution for deployed agents?","options":["A. AgentCore Runtime","B. AgentCore Memory","C. AgentCore Gateway","D. AgentCore Identity"],"pick":"A. AgentCore Runtime","answer":"A. AgentCore Runtime","correct":true,"why":"AgentCore Runtime runs agents in isolated, serverless sessions."}'
split_resp "$(post_json /judge "$judge_body")"
if [[ "$RESP_CODE" == "200" ]]; then
  explanation="$(printf '%s' "$RESP_BODY" | jq -r 'select(.explanation != null) | .explanation' 2>/dev/null)"
  if [[ -n "$explanation" ]]; then
    pass "POST /judge choice -> 200, non-empty explanation"
  else
    fail "POST /judge choice -> 200 but missing non-empty .explanation"
  fi
else
  fail "POST /judge choice -> ${RESP_CODE} (expected 200)"
fi

echo
echo "Summary: ${PASS} passed, ${FAIL} failed."
[[ "$FAIL" -eq 0 ]] || exit 1
exit 0
