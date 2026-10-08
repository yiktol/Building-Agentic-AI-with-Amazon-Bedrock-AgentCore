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

# --- Project-level Knowledge Base retrieval (additive, fail-open) -----------
# When KNOWLEDGE_BASE_ID is empty (the default), NO KB client is created and the
# retrieval/prompt-assembly path is byte-identical to the pre-KB handler: the
# empty path never imports a bedrock-agent-runtime client and never changes the
# single-element `system` list passed to converse.
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
    (never from chunk content), so this helper cannot leak option text."""
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
    highest relevance wins), and caps to the top distinct sources."""
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
    inside the converse/Lambda budget; retrieval always fails open."""
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


# Grounding note appended to CHOICE_SYSTEM only when retrieval returns context.
CHOICE_KB_NOTE = (
    "Use the course context below to ground your explanation; the expert "
    "rationale remains authoritative. Do not contradict the rationale, and if "
    "the context is irrelevant, ignore it. The wrong-answer no-leak rule above "
    "still applies: never reveal, name, quote, or describe the correct option."
)


def _retrieve_context(prompt, pick):
    """Retrieve course context for the pick, returning (context_text, sources).

    FAIL-OPEN: returns ("", []) on ANY error / empty / malformed result, so
    retrieval can never change a response's status code or body relative to the
    non-KB path. `sources` are filename-derived citation dicts mapped from the
    retrieval result locations (never from chunk content)."""
    try:
        # Independent caps so the picked option always contributes to the query
        # even when the prompt is long (combined <= ~1001 chars).
        query = (str(prompt)[:700] + " " + str(pick)[:300]).strip()
        resp = _get_kb_client().retrieve(
            knowledgeBaseId=_KB_ID,
            retrievalQuery={"text": query},
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
            print("[kb] INFO empty retrieval results")
            return "", []
        context_text = ("\n---\n".join(chunks))[:KB_CONTEXT_CAP]
        return context_text, _map_sources(results)
    except Exception as e:
        print(f"[kb] WARN retrieval failed: {type(e).__name__}")
        return "", []


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


# --- shared leak-guard primitives (imported by eval_judge.py) ---------------
# SINGLE SOURCE OF TRUTH (FR6.4): eval_judge.py imports exactly these helpers +
# constants so the harness oracle and the Lambda's runtime decision are the
# SAME code — no reimplemented normalization.
#
# FIX 3 — conservative, safe-WITHOUT-tuning thresholds:
#   NGRAM_N is the PRIMARY verbatim-span guard (consecutive content-token span);
#   OVERLAP_THRESHOLD is ADVISORY/SECONDARY (near-verbatim ratio only).
#   FAIL-SAFE direction is DOWN: lowering NGRAM_N and/or OVERLAP_THRESHOLD
#   over-blocks (safe). G1 "no wrong-pick answer leak" is a HARD INVARIANT, not
#   a tunable-later knob. Any UPWARD tuning must be validated against the
#   eval_judge.py --live Haiku run (NOT mock output); the mocked CI test asserts
#   mechanism/shape only. The shipped NGRAM_N=4 is the conservative default.
_STOPWORDS = {
    "a", "an", "the", "of", "to", "is", "are", "and", "or", "in",
    "on", "for", "that", "this", "it", "as", "by", "with",
}

OVERLAP_THRESHOLD = 0.85   # SECONDARY/advisory near-verbatim ratio (eval-tuned)
NGRAM_N = 4                # PRIMARY verbatim consecutive-content-token span

_VERDICT_WORDS = {"answer", "correct", "right", "option", "choice"}


def _normalize(s):
    """lowercase, collapse whitespace runs, strip. (shared with eval oracle)"""
    return re.sub(r"\s+", " ", str(s).lower()).strip()


def _tokens(s):
    """ordered [a-z0-9]+ tokens (shared with eval oracle)."""
    return re.findall(r"[a-z0-9]+", str(s).lower())


def _content_tokens(s):
    """_tokens(s) with _STOPWORDS removed, order preserved (shared)."""
    return [t for t in _tokens(s) if t not in _STOPWORDS]


def _parse_answer(answer):
    """'<L>. <text>' -> (answer_letter_upper, answer_text); ('', answer) when
    there is no '. ' separator (shared with eval oracle)."""
    s = str(answer)
    idx = s.find(". ")
    if idx == -1:
        return "", s
    letter = s[:idx].strip().upper()
    text = s[idx + 2:]
    return letter, text


def _leak_guard(explanation, answer, correct):
    """True iff `explanation` leaks the correct option on a WRONG pick.

    No-op (returns False) unless `correct is False`. Pure function of its three
    args — never touches the KB, env, or request beyond `answer` — so it runs
    identically on the KB and non-KB paths (FR4.4).

    SUPERSET-SAFE (FIX 2): the guard must return False for ANY explanation the
    pre-change handler would have returned 200 for, UNLESS a GENUINE leak is
    present. "Byte-identical to today" is scoped to retrieval + prompt
    assembly only — this guard now gates wrong-pick 200s, so the response path
    is NOT claimed byte-identical. The two FIX-2 tests in test_handler.py
    enforce the non-regression (existing wrong-pick still 200; empty-letter
    wrong-pick 200)."""
    if correct is not False:
        return False

    answer_letter, answer_text = _parse_answer(answer)
    expl_raw = str(explanation)
    expl_norm = _normalize(expl_raw)
    expl_tokens = _tokens(expl_raw)
    expl_content = _content_tokens(expl_raw)

    # Rule 1 — letter-as-answer (explicit option-reference forms ONLY).
    # FIX 1: guard ALL answer_letter rules behind `if answer_letter:` — a
    # letterless answer (e.g. "4") must NOT trip on the bare words
    # option/answer/choice.
    if answer_letter:
        L = re.escape(answer_letter)
        letter_patterns = [
            r"\b(option|choice|answer)\s+" + L + r"\b",
            r"\b" + L + r"\s+is\s+(correct|right|the\s+answer)\b",
            r"\(" + L + r"\)",
        ]
        for pat in letter_patterns:
            if re.search(pat, expl_raw, flags=re.I):
                return True

    # Rule 2 — answer-text overlap (SECONDARY, near-verbatim restatement only).
    answer_content = _content_tokens(answer_text)
    if len(answer_content) >= 3:
        expl_content_set = set(expl_content)
        answer_set = set(answer_content)
        overlap = len(expl_content_set & answer_set) / len(answer_set)
        if overlap >= OVERLAP_THRESHOLD:
            return True

    # Rule 3 — verbatim n-gram / short-answer containment (PRIMARY verbatim).
    if len(answer_content) < 3:
        # Short answers (e.g. "4", "Amazon S3"): leak only when EVERY content
        # token appears as a whole normalized token AND at least one is adjacent
        # to a verdict word. FIX 1: this verdict-adjacency letter path is only
        # taken when answer_letter is non-empty — a bare "4" with no verdict
        # word nearby does NOT trip.
        if answer_letter and answer_content:
            expl_set = set(expl_tokens)
            if all(tok in expl_set for tok in answer_content):
                for tok in answer_content:
                    adj = (
                        r"\b(answer|correct|right|option|choice)\s+\w*\s*"
                        + re.escape(tok) + r"\b"
                    )
                    adj2 = (
                        r"\b" + re.escape(tok)
                        + r"\s+is\s+(correct|right|the\s+answer)\b"
                    )
                    if re.search(adj, expl_norm) or re.search(adj2, expl_norm):
                        return True
    else:
        # Longer answers (>= 3 content tokens): leak if any NGRAM_N consecutive
        # content tokens of answer_text appear verbatim as consecutive whole
        # tokens in the explanation.
        if len(expl_content) >= NGRAM_N:
            expl_ngrams = {
                tuple(expl_content[i:i + NGRAM_N])
                for i in range(len(expl_content) - NGRAM_N + 1)
            }
            for i in range(len(answer_content) - NGRAM_N + 1):
                if tuple(answer_content[i:i + NGRAM_N]) in expl_ngrams:
                    return True

    # Rule 4 — explicit reveal phrases.
    reveal_phrases = (
        "the correct answer", "the right option", "the right answer",
        "you should have picked", "the answer is", "correct option is",
    )
    for phrase in reveal_phrases:
        if phrase in expl_norm:
            return True

    return False


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
        # Additive KB grounding (fail-open). When _KB_ID is empty, no retrieval
        # happens and `system` stays byte-identical to [{"text": CHOICE_SYSTEM}].
        context_block, sources = _retrieve_context(prompt, pick) if _KB_ID else ("", [])
        system_text = CHOICE_SYSTEM
        if context_block:
            system_text = (
                CHOICE_SYSTEM + "\n\n" + CHOICE_KB_NOTE + "\n\n" + context_block
            )
        try:
            out = _bedrock.converse(
                modelId=MODEL_ID,
                system=[{"text": system_text}],
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
        # No-leak guard: on a WRONG pick only, block any explanation that reveals
        # the correct option. This is the ONE place we fail CLOSED (G1 outranks
        # availability on a wrong pick): an internal guard exception -> 502. The
        # front-end treats any non-200 as "use the local hint" (safe fallback),
        # so tripping degrades gracefully with zero front-end change.
        if correct is False:
            try:
                tripped = _leak_guard(explanation, answer, correct)
            except Exception:
                tripped = True
            if tripped:
                return _resp(502, {"error": "judge guard tripped"})
        return _resp(200, {"mode": "choice", "explanation": explanation, "model": MODEL_ID, "sources": sources})

    return _resp(400, {"error": f"unsupported mode: {mode}"})
