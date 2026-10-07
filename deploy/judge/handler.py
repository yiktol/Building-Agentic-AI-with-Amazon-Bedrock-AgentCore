"""AI judge for the AgentCore course knowledge-check quiz.

Follows the reference pattern from
`Become-an-AWS-AI-Business-Strategist/deploy/judge/handler.py`: invoked behind
CloudFront (same-origin /judge*), it coaches a learner's multiple-choice answer
using Amazon Bedrock (Claude Haiku 4.5) and returns a compact {explanation}.
Designed to fail closed on bad input; the front-end treats any non-200 as "fall
back to the built-in hint", so the quiz never gets stuck waiting on the judge.

Mode: "choice" (the reference's Socratic multiple-choice coach), extended to
also affirm a CORRECT pick. On a WRONG pick it NEVER reveals, names, or
describes the correct option — the learner retries until they get it right.
"""
import json
import os
import re
import boto3
from botocore.config import Config

REGION = os.environ.get("BEDROCK_REGION", "ap-southeast-1")
MODEL_ID = os.environ.get(
    "JUDGE_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0"
)
ORIGIN_SECRET = os.environ.get("ORIGIN_SECRET", "")
MAX_INPUT = 4000  # cap learner + prompt text to bound cost / abuse

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=REGION,
    config=Config(retries={"max_attempts": 2, "mode": "standard"}, read_timeout=25),
)

CORS = {
    "Content-Type": "application/json",
    # Same-origin in production (served under the same CloudFront domain), so a
    # permissive ACAO is harmless and helps local testing. Tighten if needed.
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "content-type,x-origin-secret",
}

# --- Choice-coaching mode ---
# Coaches a learner's multiple-choice pick on a knowledge check. Mirrors the
# reference CHOICE mode (Socratic, never reveal the answer on a wrong pick), and
# additionally affirms a CORRECT pick. Because the learner retries until correct,
# a wrong-answer response must NOT reveal, name, quote, or describe the right
# option.
CHOICE_SYSTEM = (
    "You are an encouraging, Socratic teaching assistant in an AWS course, "
    "'Building Agentic AI with Amazon Bedrock AgentCore'. A learner answered a "
    "multiple-choice knowledge-check question and will keep trying until they "
    "get it right.\n"
    "If the learner's pick was CORRECT: confirm it clearly and confidently, then "
    "explain concisely (2-4 sentences) WHY that option is right, grounded in the "
    "rationale. Treat it as the definitive right answer. Do NOT hedge, cast "
    "doubt, or walk it back: never use words like 'however', 'but', 'although', "
    "'that said', 'reconsider', or 'you may have', and never suggest they "
    "re-examine their choice or that it might be wrong. Stay fully affirming.\n"
    "If the learner's pick was WRONG: in 1-3 encouraging sentences explain why "
    "THAT choice is not the best answer and what consideration it overlooks, "
    "nudging their thinking. CRITICAL for wrong answers: do NOT reveal, name, "
    "quote, or describe the correct option, and do not say which option is "
    "right — help them reconsider, not look it up.\n"
    "Ground everything in the expert rationale; do not invent facts. Respond "
    "with ONLY a compact JSON object, no prose, no code fences."
)

CHOICE_TEMPLATE = """Question:
{prompt}

Options:
{options}

The learner picked: "{pick}"
Was the pick correct? {correct}
This is attempt number {attempt}. Options they have already ruled out: {tried}

(For your reasoning only — if the pick was WRONG, NEVER reveal or name this) The correct option is "{answer}", because: {why}

Return ONLY this JSON shape (if the pick was wrong, do not mention the correct option anywhere):
{{"explanation":"If correct: 2-4 sentences that confidently confirm it is the right answer and explain why — no hedging, no 'however', no doubt. If wrong: 1-3 sentences, second person, why the pick is not the best choice and what to reconsider — WITHOUT naming the correct option"}}"""


def _resp(code, body):
    return {"statusCode": code, "headers": CORS, "body": json.dumps(body)}


def _clean_json(text):
    """Strip code fences and parse the first JSON object in the text."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I | re.M).strip()
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        t = m.group(0)
    return json.loads(t)


def handler(event, context):
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "POST"
    )
    if method == "OPTIONS":
        return _resp(200, {"ok": True})

    # Defense-in-depth: verify the secret header CloudFront injects (the browser
    # never sees it). Only enforced when ORIGIN_SECRET is configured.
    if ORIGIN_SECRET:
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        if headers.get("x-origin-secret") != ORIGIN_SECRET:
            return _resp(403, {"error": "forbidden"})

    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode("utf-8")
        data = json.loads(body)
    except Exception:
        return _resp(400, {"error": "invalid JSON body"})

    # The quiz front-end sends mode "choice" (reference-compatible); accept the
    # alias "quiz" too for convenience.
    mode = str(data.get("mode", "choice")).lower().strip()
    prompt = str(data.get("prompt", ""))[:MAX_INPUT]
    why = str(data.get("why", ""))[:MAX_INPUT]

    if mode in ("choice", "quiz"):
        options = data.get("options") or []
        if isinstance(options, list):
            options_txt = "\n".join(f"- {str(o)[:300]}" for o in options[:8])
        else:
            options_txt = str(options)[:MAX_INPUT]
        pick = str(data.get("pick", "")).strip()[:400]
        answer = str(data.get("answer", "")).strip()[:400]
        correct = data.get("correct")
        correct_txt = "yes" if correct is True else ("no" if correct is False else "unknown")
        try:
            attempt = int(data.get("attempt", 1))
        except Exception:
            attempt = 1
        tried = data.get("tried") or []
        if isinstance(tried, list) and tried:
            tried_txt = "; ".join(str(t)[:200] for t in tried[:8])
        else:
            tried_txt = "(none yet)"
        if not prompt or not pick or not answer:
            return _resp(400, {"error": "missing choice context"})
        user = CHOICE_TEMPLATE.format(
            prompt=prompt, options=options_txt, pick=pick,
            correct=correct_txt, attempt=attempt, tried=tried_txt,
            answer=answer, why=why,
        )
        try:
            out = _bedrock.converse(
                modelId=MODEL_ID,
                system=[{"text": CHOICE_SYSTEM}],
                messages=[{"role": "user", "content": [{"text": user}]}],
                inferenceConfig={"maxTokens": 320, "temperature": 0},
            )
            raw = out["output"]["message"]["content"][0]["text"]
            parsed = _clean_json(raw)
        except Exception as e:
            return _resp(502, {"error": "judge unavailable", "detail": str(e)[:200]})
        explanation = str(parsed.get("explanation", "")).strip()[:800]
        if not explanation:
            return _resp(502, {"error": "judge returned empty explanation"})
        return _resp(200, {"mode": "choice", "explanation": explanation, "model": MODEL_ID})

    return _resp(400, {"error": f"unsupported mode: {mode}"})
