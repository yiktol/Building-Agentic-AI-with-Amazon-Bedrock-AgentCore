#!/usr/bin/env bash
#
# Add (idempotently) per-IP rate-based rules to the shared WAF Web ACL that
# protects the agc-slides CloudFront distribution, scoped to the two public
# Bedrock-backed endpoints:
#
#   /assistant*  -> the KB-grounded course assistant Lambda
#   /judge*      -> the knowledge-check judge Lambda
#
# WHY: those two paths are the only public surfaces that invoke Amazon Bedrock,
# so they are the cost/abuse-sensitive ones. The static slides (served from
# private S3 via CloudFront OAC) need no rate limiting. We rate-limit ONLY those
# two URI prefixes with a WAF ScopeDownStatement so the rest of the site — and
# any other resources that share this Web ACL — are unaffected.
#
# The Web ACL is EXTERNALLY managed (the agc-slides CloudFormation only consumes
# its ARN from SSM: ${PARAMETER_PREFIX}/WebApplicationFirewallACLArn). It is NOT
# created by this project's templates, so these rules live here as a committed,
# idempotent script rather than in CloudFormation. The script fetches the ACL's
# current definition, appends the two rules only if absent, and updates with the
# ACL's LockToken (optimistic concurrency) — existing rules are preserved
# verbatim. Re-running is a no-op once the rules exist.
#
# WAF for CloudFront is always global scope in us-east-1, regardless of where
# the rest of the stack lives.
#
# Usage:
#   ./waf-rate-limit.sh                 # resolve the ACL ARN from SSM and apply
#   WEB_ACL_ARN=arn:aws:wafv2:us-east-1:ACCT:global/webacl/NAME/ID ./waf-rate-limit.sh
#   RATE_LIMIT=500 ./waf-rate-limit.sh  # override the per-IP 5-min request limit
#   ./waf-rate-limit.sh --show          # print the current rate rules and exit
#
set -euo pipefail

REGION="us-east-1"                                     # WAF global scope is us-east-1
PARAMETER_PREFIX="${PARAMETER_PREFIX:-/genai/cognito}" # SSM prefix for shared config
SSM_PARAM="${PARAMETER_PREFIX}/WebApplicationFirewallACLArn"
# Per-IP request ceiling over a 5-minute window. 300 is generous for a single
# learner (one /judge call per quiz submit, one /assistant call per chat turn)
# while still stopping scripted abuse. WAF minimum is 100.
RATE_LIMIT="${RATE_LIMIT:-300}"
EVAL_WINDOW_SEC=300

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
err() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; }

command -v aws >/dev/null || { err "aws CLI not found"; exit 1; }
command -v python3 >/dev/null || { err "python3 not found"; exit 1; }

# ---------------------------------------------------- resolve the Web ACL ARN ---
WEB_ACL_ARN="${WEB_ACL_ARN:-}"
if [[ -z "$WEB_ACL_ARN" ]]; then
  log "Resolving Web ACL ARN from SSM ${SSM_PARAM}"
  WEB_ACL_ARN="$(aws ssm get-parameter --name "$SSM_PARAM" --region ap-southeast-1 \
    --query 'Parameter.Value' --output text 2>/dev/null || true)"
fi
[[ -n "$WEB_ACL_ARN" && "$WEB_ACL_ARN" != "None" ]] || { err "could not resolve Web ACL ARN (set WEB_ACL_ARN or the SSM param)"; exit 1; }

# ARN shape: arn:aws:wafv2:us-east-1:ACCT:global/webacl/NAME/ID
ACL_NAME="$(printf '%s' "$WEB_ACL_ARN" | awk -F/ '{print $(NF-1)}')"
ACL_ID="$(printf '%s'   "$WEB_ACL_ARN" | awk -F/ '{print $NF}')"
[[ -n "$ACL_NAME" && -n "$ACL_ID" ]] || { err "could not parse name/id from ARN: $WEB_ACL_ARN"; exit 1; }
log "Web ACL: name=${ACL_NAME} id=${ACL_ID} (scope CLOUDFRONT, region ${REGION})"

SHOW_ONLY=false
[[ "${1:-}" == "--show" ]] && SHOW_ONLY=true

# The whole update is done in Python/boto3 (not aws-cli --cli-input-json): the
# ByteMatchStatement SearchString is a WAF "blob", and the CLI tries to base64-
# decode a string passed there, which rejects a plain path like "/assistant".
# boto3 accepts the raw bytes and encodes the blob correctly.
python3 - "$ACL_NAME" "$ACL_ID" "$REGION" "$RATE_LIMIT" "$EVAL_WINDOW_SEC" "$SHOW_ONLY" <<'PY'
import sys, boto3

acl_name, acl_id, region, limit, window, show_only = sys.argv[1:7]
limit = int(limit); window = int(window); show_only = (show_only == "true")
c = boto3.client("wafv2", region_name=region)

got = c.get_web_acl(Name=acl_name, Scope="CLOUDFRONT", Id=acl_id)
w = got["WebACL"]; lock = got["LockToken"]
rules = list(w["Rules"])

def show():
    found = False
    for r in rules:
        rb = r["Statement"].get("RateBasedStatement")
        if rb:
            found = True
            sd = rb.get("ScopeDownStatement", {}).get("ByteMatchStatement", {})
            s = sd.get("SearchString", b"")
            s = s.decode() if isinstance(s, (bytes, bytearray)) else s
            print(f"  [{r['Priority']}] {r['Name']}: {list(r['Action'])[0]} "
                  f"limit={rb['Limit']}/{rb.get('EvaluationWindowSec', 300)}s "
                  f"key={rb['AggregateKeyType']} {sd.get('PositionalConstraint')} '{s}'")
    if not found:
        print("  (no rate-based rules)")

if show_only:
    print("Current rate-based rules:")
    show()
    sys.exit(0)

existing = {r["Name"] for r in rules}
used_priorities = {r["Priority"] for r in rules}

def next_priority(start):
    p = start
    while p in used_priorities:
        p += 1
    used_priorities.add(p)
    return p

def rate_rule(name, path_prefix):
    return {
        "Name": name,
        "Priority": next_priority(9),
        "Action": {"Block": {}},
        "Statement": {"RateBasedStatement": {
            "Limit": limit,
            "EvaluationWindowSec": window,
            "AggregateKeyType": "IP",
            "ScopeDownStatement": {"ByteMatchStatement": {
                "SearchString": path_prefix.encode("utf-8"),
                "FieldToMatch": {"UriPath": {}},
                "TextTransformations": [{"Priority": 0, "Type": "LOWERCASE"}],
                "PositionalConstraint": "STARTS_WITH"}}}},
        "VisibilityConfig": {"SampledRequestsEnabled": True,
                             "CloudWatchMetricsEnabled": True, "MetricName": name},
    }

added = []
for name, prefix in (("RateLimitAssistant", "/assistant"), ("RateLimitJudge", "/judge")):
    if name in existing:
        print(f"  rule {name} already present; leaving as-is")
    else:
        rules.append(rate_rule(name, prefix))
        added.append(name)

if not added:
    print("Nothing to do: both rate rules already exist.")
    sys.exit(0)

kw = dict(Name=w["Name"], Scope="CLOUDFRONT", Id=w["Id"],
          DefaultAction=w["DefaultAction"], Rules=rules,
          VisibilityConfig=w["VisibilityConfig"], LockToken=lock)
if w.get("Description"):
    kw["Description"] = w["Description"]
for opt in ("CustomResponseBodies", "CaptchaConfig", "ChallengeConfig", "TokenDomains"):
    if opt in w:
        kw[opt] = w[opt]

c.update_web_acl(**kw)
print(f"Added: {', '.join(added)} (limit={limit}/{window}s per IP). Current rate rules:")
# Re-read so the printed state is authoritative.
rules = c.get_web_acl(Name=acl_name, Scope="CLOUDFRONT", Id=acl_id)["WebACL"]["Rules"]
show()
PY

log "Done."
