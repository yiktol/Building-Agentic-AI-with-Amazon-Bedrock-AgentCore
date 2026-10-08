"""Course assistant (chatbot) for the AgentCore course.

A SEPARATE Lambda from the quiz judge: invoked behind CloudFront
(same-origin /assistant*), it answers learner questions about course info,
module content, lab content, and agentic-AI best practices, grounded STRICTLY
in the course Knowledge Base. Input {message, history?} -> a KB-grounded
{answer, sources}. It deliberately REFUSES to answer knowledge-check quiz
questions (that is the judge's job) so it can never leak a quiz answer.

Independent of the judge by design: the citation helpers below are COPIED
(never imported) from deploy/judge/handler.py, and the quiz-refusal guard here
is its own code, unrelated to the judge's no-leak guard.
"""
import json
import os
import re
import boto3
from botocore.config import Config

REGION = os.environ.get("BEDROCK_REGION", "ap-southeast-1")
MODEL_ID = os.environ.get(
    "ASSISTANT_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0"
)
ORIGIN_SECRET = os.environ.get("ORIGIN_SECRET", "")
MAX_INPUT = 4000  # cap learner message to bound cost / abuse

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=REGION,
    config=Config(retries={"max_attempts": 2, "mode": "standard"}, read_timeout=25),
)

# --- Project-level Knowledge Base retrieval ---------------------------------
# When KNOWLEDGE_BASE_ID is empty, the assistant is "not configured" and returns
# 503 (it has nothing to ground on). The KB client is created lazily, only when
# _KB_ID is non-empty.
_KB_ID = os.environ.get("KNOWLEDGE_BASE_ID", "").strip()
KB_NUM_RESULTS = int(os.environ.get("KB_NUM_RESULTS", "4"))
KB_CONTEXT_CAP = 3000  # hard cap on the whole injected context block
_kb_client = None  # lazily initialized, ONLY when _KB_ID is non-empty

# Human-readable deck titles keyed by module number. Preferred label source for
# `modules/MLAGAC-...-M0N-..._InstructorDeck.md` keys; the filename-derived
# title is only a fallback when N is not in this map. Derived from this repo's
# 6-module AgentCore course (slides/index.html authoritative titles).
MODULE_TITLES = {
    1: "Foundations of Agentic AI Patterns",
    2: "AgentCore Runtime and Framework Integration",
    3: "Security and Identity Management",
    4: "Tool Integration and AgentCore Gateway",
    5: "Agentic Memory Implementation",
    6: "Production Monitoring and Observability",
}

# docs/* basenames -> fixed labels (module is None: labs/guides are not decks).
_DOC_LABELS = {
    "lab.md": "Hands-on Lab \u2014 Enhance and Scale Agents",
}

_MODULE_KEY_RE = re.compile(
    r"^MLAGAC-\d+-EN-M0?(\d+)-(.+?)_InstructorDeck\.md$", re.I
)

# Cap on the number of distinct citations surfaced to the learner.
_SOURCES_CAP = 3


def _source_label(uri):
    """Map a KB result's S3 URI to {"label": str, "module": int|None}, or None.

    Pure + defensive (fail-open to no-source): a non-string, empty, or
    unparseable/unknown URI returns None. Labels are derived ONLY from the key
    (never from chunk content), so this helper cannot leak option text.

    COPIED verbatim from deploy/judge/handler.py (never imported)."""
    if not isinstance(uri, str) or not uri.strip():
        return None
    # Strip a leading s3:// + bucket segment; accept a bare key too.
    key = uri.strip()
    if key.lower().startswith("s3://"):
        rest = key[5:]
        # drop the bucket (first path segment)
        slash = rest.find("/")
        key = rest[slash + 1:] if slash != -1 else ""
    if not key:
        return None
    base = key.rsplit("/", 1)[-1]
    if not base:
        return None

    m = _MODULE_KEY_RE.match(base)
    if m:
        module_num = int(m.group(1))
        title = MODULE_TITLES.get(module_num)
        if not title:
            # Fall back to the filename-derived title. The [-_]+ character class
            # is a deliberate deviation from the reference's _+ (a dead path for
            # modules 1-6, since MODULE_TITLES always wins there).
            title = re.sub(r"[-_]+", " ", m.group(2)).strip()
        if not title:
            return None
        return {"label": f"Module {module_num} \u2014 {title}", "module": module_num}

    doc_label = _DOC_LABELS.get(base.lower())
    if doc_label:
        return {"label": doc_label, "module": None}

    return None


def _map_sources(results):
    """Map raw retrievalResults to a deduped, capped list of citation dicts.

    Reads ONLY `result["location"]["s3Location"]["uri"]` (defensively), dedupes
    by label preserving first-seen order (retrieve() returns ranked results, so
    highest relevance wins), and caps to the top distinct sources.

    COPIED verbatim from deploy/judge/handler.py (never imported)."""
    sources = []
    seen = set()
    for r in results or []:
        try:
            uri = r["location"]["s3Location"]["uri"]
        except (TypeError, KeyError, IndexError):
            continue
        mapped = _source_label(uri)
        if not mapped:
            continue
        label = mapped["label"]
        if label in seen:
            continue
        seen.add(label)
        sources.append(mapped)
        if len(sources) >= _SOURCES_CAP:
            break
    return sources


def _get_kb_client():
    """Lazy singleton bedrock-agent-runtime client (created only when _KB_ID
    is set). Tight timeouts + single attempt bound retrieval latency well
    inside the converse/Lambda budget.

    COPIED from deploy/judge/handler.py (never imported)."""
    global _kb_client
    if _kb_client is None:
        _kb_client = boto3.client(
            "bedrock-agent-runtime",
            region_name=REGION,
            config=Config(
                retries={"max_attempts": 1, "mode": "standard"},
                read_timeout=3,
                connect_timeout=2,
            ),
        )
    return _kb_client


CORS = {
    "Content-Type": "application/json",
    # Same-origin in production (served under the same CloudFront domain), so a
    # permissive ACAO is harmless and helps local testing. Tighten if needed.
    # COPIED from deploy/judge/handler.py (never imported).
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "content-type,x-origin-secret",
}


# System prompt for the KB-grounded course assistant. Distinct from the judge's
# CHOICE_SYSTEM: this one answers general course questions, strictly from the
# provided course context, and never adjudicates quiz picks.
ASSISTANT_SYSTEM = (
    "You are a helpful assistant for the AWS course 'Building Agentic AI with "
    "Amazon Bedrock AgentCore'. "
    "You answer learner questions about course information, module content, lab "
    "content, and agentic-AI best practices.\n"
    "Answer ONLY from the course context provided below. Do NOT use general "
    "knowledge beyond that context, and do NOT invent facts, module names, or "
    "lab steps. If the course context does not cover the question, say plainly "
    "that the course material does not cover it, then point the learner to the "
    "most relevant module or lab to explore. Keep answers concise and friendly."
)


def _resp(code, body):
    """COPIED verbatim from deploy/judge/handler.py (never imported)."""
    return {"statusCode": code, "headers": CORS, "body": json.dumps(body)}


# --- quiz-refusal guard (assistant-only; UNRELATED to the judge's leak-guard) -
# The assistant must not answer knowledge-check questions. This detector is
# deliberately conservative: over-refusing a quiz paste is acceptable, leaking
# an answer is not. It uses simple regex / substring checks only.
_QUIZ_OPTION_RE = re.compile(r"^\s*[A-F][.)]\s", re.M)
_QUIZ_PHRASES = (
    "which option is correct",
    "what is the answer to question",
    "what's the answer to question",
    "correct answer",
    "knowledge check",
)
_QUIZ_ANSWER_TO_Q_RE = re.compile(r"answer to question\s+\d+", re.I)


def _is_quiz_attempt(message):
    """True iff `message` looks like a pasted knowledge-check question or a
    request to reveal a quiz answer. Conservative on purpose."""
    text = str(message)
    low = text.lower()
    # Two or more pasted multiple-choice option stems (e.g. "A. ...", "B) ...").
    if len(_QUIZ_OPTION_RE.findall(text)) >= 2:
        return True
    for phrase in _QUIZ_PHRASES:
        if phrase in low:
            return True
    if _QUIZ_ANSWER_TO_Q_RE.search(low):
        return True
    return False


# Returned verbatim on a detected quiz attempt. Offers to teach the concept and
# points the learner to the knowledge check WITHOUT revealing any answer.
_QUIZ_REFUSAL = (
    "I can't give away knowledge-check answers \u2014 that's for you to work "
    "through so the practice sticks. I'm happy to explain the underlying "
    "concept, though. Tell me the topic or module you're studying and I'll walk "
    "you through it, then head back to that module's Knowledge check to try the "
    "question again."
)


def _retrieve_context(message):
    """Retrieve course context for `message`, returning (context_text, sources).

    Unlike the judge's fail-open retrieval, this does NOT swallow errors: any
    exception propagates so the handler maps it to 502. When there are zero
    chunks it returns ("", []). `sources` are filename-derived citation dicts
    mapped from the retrieval result locations (never from chunk content)."""
    resp = _get_kb_client().retrieve(
        knowledgeBaseId=_KB_ID,
        retrievalQuery={"text": str(message)[:1000]},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": KB_NUM_RESULTS}
        },
    )
    results = resp.get("retrievalResults") or []
    chunks = []
    for r in results:
        text = (r.get("content") or {}).get("text") or ""
        if text:
            chunks.append(text[:1000])  # per-chunk cap so one can't crowd out
    if not chunks:
        return "", []
    context_text = ("\n---\n".join(chunks))[:KB_CONTEXT_CAP]
    return context_text, _map_sources(results)


def _parse_history(raw):
    """Coerce an optional history list into converse-ready turns.

    Keeps only the last 6 well-formed {role, content} entries; maps role to
    'assistant' when it is 'assistant' else 'user'; truncates each content to
    1000 chars; drops malformed entries."""
    if not isinstance(raw, list):
        return []
    turns = []
    for item in raw[-6:]:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        role = "assistant" if item.get("role") == "assistant" else "user"
        turns.append({"role": role, "content": content[:1000]})
    return turns


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

    message = str(data.get("message", ""))[:MAX_INPUT].strip()
    if not message:
        return _resp(400, {"error": "missing message"})

    history = _parse_history(data.get("history"))

    if not _KB_ID:
        return _resp(503, {"error": "assistant not configured"})

    # Quiz-refusal: never retrieve or call converse on a knowledge-check paste.
    if _is_quiz_attempt(message):
        return _resp(200, {"answer": _QUIZ_REFUSAL, "sources": []})

    try:
        context_block, sources = _retrieve_context(message)
    except Exception as e:
        return _resp(502, {"error": "assistant unavailable", "detail": str(e)[:200]})

    system_text = ASSISTANT_SYSTEM + "\n\nCourse context:\n" + context_block
    messages = [
        {"role": t["role"], "content": [{"text": t["content"]}]} for t in history
    ]
    messages.append({"role": "user", "content": [{"text": message}]})

    try:
        out = _bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": system_text}],
            messages=messages,
            inferenceConfig={"maxTokens": 600, "temperature": 0},
        )
        answer = out["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return _resp(502, {"error": "assistant unavailable", "detail": str(e)[:200]})

    answer = str(answer).strip()
    if not answer:
        return _resp(502, {"error": "assistant returned empty answer"})
    return _resp(200, {"answer": answer[:4000], "sources": sources, "model": MODEL_ID})
