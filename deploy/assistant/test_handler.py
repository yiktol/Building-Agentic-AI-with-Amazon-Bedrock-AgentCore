"""Unit tests for the course-assistant Lambda handler. Bedrock + KB are fully
mocked (no AWS).

Run:  cd deploy/assistant && ORIGIN_SECRET=testsecret python3 test_handler.py

Covers: (a) grounded answer with mapped sources (200); (b) quiz attempt refused
WITHOUT calling converse, no answer leaked, sources == [] (200); (c) out-of-
scope question with empty retrieval -> redirect-style answer, sources == []
(200); (d) missing message (400); (e) wrong x-origin-secret when ORIGIN_SECRET
set (403); (f) a mocked converse raising an exception (502); (g) empty
KNOWLEDGE_BASE_ID -> assistant not configured (503).
"""
import json
import os
import sys

import handler


class _FakeBedrock:
    """Stand-in for the module-level boto3 bedrock-runtime client.

    When `raise_exc`, converse() raises. Otherwise it sets `record['called']`
    (if a dict is supplied) and returns a canned text answer."""

    def __init__(self, text=None, raise_exc=False, record=None):
        self._text = text
        self._raise = raise_exc
        self._record = record

    def converse(self, **kwargs):
        if self._record is not None:
            self._record["called"] = True
        if self._raise:
            raise RuntimeError("simulated Bedrock failure")
        return {"output": {"message": {"content": [{"text": self._text}]}}}


class _FakeKbClient:
    """retrieve() stub returning a caller-supplied retrievalResults list."""

    def __init__(self, results=None, raise_exc=False):
        self._results = results if results is not None else []
        self._raise = raise_exc

    def retrieve(self, **kwargs):
        if self._raise:
            raise RuntimeError("simulated KB failure")
        return {"retrievalResults": self._results}


def _s3_result(uri, text="context chunk"):
    """Build a retrieve() result with an s3Location URI and benign content."""
    return {"content": {"text": text}, "location": {"s3Location": {"uri": uri}}}


def _set_kb(results=None, raise_exc=False, kb_id="FAKEKBID1234"):
    """Enable the KB path with a stubbed client (mutates module state the same
    way the judge test swaps handler._bedrock)."""
    handler._KB_ID = kb_id
    handler._kb_client = _FakeKbClient(results=results, raise_exc=raise_exc)


def _disable_kb():
    handler._KB_ID = ""
    handler._kb_client = None


_SECRET = os.environ.get("ORIGIN_SECRET", "")


def _event(body, headers=None, b64=False):
    ev = {
        "requestContext": {"http": {"method": "POST"}},
        "body": body,
        "isBase64Encoded": b64,
    }
    if headers is not None:
        ev["headers"] = headers
    elif _SECRET:
        ev["headers"] = {"x-origin-secret": _SECRET}
    return ev


def _secret_headers(extra=None):
    h = {"x-origin-secret": _SECRET} if _SECRET else {}
    if extra:
        h.update(extra)
    return h


def _run(name, fn):
    fn()
    print(f"  ok: {name}")


def test_grounded_answer():
    # (a) retrieve() returns a module deck + the lab; converse returns a plain
    # answer. Assert 200, non-empty answer, sources mapped to the right labels.
    handler._bedrock = _FakeBedrock(
        text="Identity management secures agents with scoped credentials."
    )
    try:
        _set_kb(results=[
            _s3_result(
                "s3://my-bucket/modules/"
                "MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md",
                text="Security and identity scope agent access and credentials.",
            ),
            _s3_result("s3://my-bucket/docs/lab.md"),
        ])
        body = json.dumps({"message": "How does AgentCore handle identity?"})
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 200, res
        out = json.loads(res["body"])
        assert out["answer"].strip(), out
        assert out["sources"] == [
            {"label": "Module 3 \u2014 Security and Identity Management", "module": 3},
            {"label": "Hands-on Lab \u2014 Enhance and Scale Agents", "module": None},
        ], out
    finally:
        _disable_kb()


def test_quiz_attempt_refused_no_converse():
    # (b) A pasted multiple-choice question must be refused WITHOUT calling
    # converse; sources == [] and no quiz answer in the refusal.
    record = {"called": False}
    handler._bedrock = _FakeBedrock(raise_exc=True, record=record)
    try:
        _set_kb(results=[_s3_result("s3://b/docs/lab.md")])
        body = json.dumps({
            "message": (
                "Which option is correct?\n"
                "A. Assuming a snippet writer manages whole projects\n"
                "B. Using external APIs to extend an LLM\n"
                "C. Breaking a task into subtasks\n"
            )
        })
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 200, res
        out = json.loads(res["body"])
        assert out["sources"] == [], out
        assert record["called"] is False, "converse must NOT be called on a quiz attempt"
        # The refusal must not hand over an option letter as the answer.
        low = out["answer"].lower()
        assert "the answer is" not in low, out
        assert "correct option" not in low, out
    finally:
        _disable_kb()


def test_quiz_attempt_phrase_refused():
    # (b') The phrase form ("what is the answer to question N") must also refuse
    # without calling converse.
    record = {"called": False}
    handler._bedrock = _FakeBedrock(raise_exc=True, record=record)
    try:
        _set_kb(results=[_s3_result("s3://b/docs/lab.md")])
        body = json.dumps({"message": "what is the answer to question 2?"})
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 200, res
        out = json.loads(res["body"])
        assert out["sources"] == [], out
        assert record["called"] is False, "converse must NOT be called on a quiz attempt"
    finally:
        _disable_kb()


def test_out_of_scope_empty_retrieval():
    # (c) KB enabled but retrieve() returns no results -> sources == [] and the
    # model is asked to redirect; we assert a non-empty answer + empty sources.
    handler._bedrock = _FakeBedrock(
        text="The course material does not cover that. Try Module 1 to start."
    )
    try:
        _set_kb(results=[])
        body = json.dumps({"message": "What is the capital of France?"})
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 200, res
        out = json.loads(res["body"])
        assert out["answer"].strip(), out
        assert out["sources"] == [], out
    finally:
        _disable_kb()


def test_missing_message():
    # (d) Empty message -> 400 'missing message'. KB enabled so we are sure the
    # missing-message check runs before the config/retrieval paths.
    handler._bedrock = _FakeBedrock(text="x")
    try:
        _set_kb(results=[_s3_result("s3://b/docs/lab.md")])
        res = handler.handler(_event(json.dumps({"message": "   "}),
                                     headers=_secret_headers()), None)
        assert res["statusCode"] == 400, res
        assert "missing message" in json.loads(res["body"])["error"], res
    finally:
        _disable_kb()


def test_bad_json():
    res = handler.handler(_event("{not json", headers=_secret_headers()), None)
    assert res["statusCode"] == 400, res
    assert "invalid JSON" in json.loads(res["body"])["error"], res


def test_wrong_origin_secret():
    if not _SECRET:
        print("  skip: test_wrong_origin_secret (ORIGIN_SECRET not set)")
        return
    # (e) wrong secret -> 403 forbidden.
    body = json.dumps({"message": "What is Module 1 about?"})
    res = handler.handler(
        _event(body, headers={"x-origin-secret": "WRONG"}), None
    )
    assert res["statusCode"] == 403, res
    assert json.loads(res["body"])["error"] == "forbidden", res


def test_converse_raises():
    # (f) a grounded question whose converse() raises -> 502 'assistant unavailable'.
    handler._bedrock = _FakeBedrock(raise_exc=True)
    try:
        _set_kb(results=[_s3_result("s3://b/docs/lab.md")])
        body = json.dumps({"message": "What is covered in the lab?"})
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 502, res
        assert "assistant unavailable" in json.loads(res["body"])["error"], res
    finally:
        _disable_kb()


def test_kb_retrieval_raises():
    # (f') retrieval errors must NOT fail open: a raising retrieve() -> 502.
    handler._bedrock = _FakeBedrock(text="should not be reached")
    try:
        _set_kb(raise_exc=True)
        body = json.dumps({"message": "What is covered in the lab?"})
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 502, res
        assert "assistant unavailable" in json.loads(res["body"])["error"], res
    finally:
        _disable_kb()


def test_not_configured():
    # (g) empty KNOWLEDGE_BASE_ID -> 503 'assistant not configured'.
    handler._bedrock = _FakeBedrock(text="x")
    _disable_kb()
    body = json.dumps({"message": "What is Module 1 about?"})
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 503, res
    assert "assistant not configured" in json.loads(res["body"])["error"], res


def test_history_included_in_messages():
    # Optional history is parsed, capped, and prepended before the current turn.
    captured = {}

    class _CapBedrock:
        def converse(self, **kwargs):
            captured.update(kwargs)
            return {"output": {"message": {"content": [{"text": "ok"}]}}}

    handler._bedrock = _CapBedrock()
    try:
        _set_kb(results=[_s3_result("s3://b/docs/lab.md")])
        hist = [{"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
                {"role": "bogus", "content": ""},  # dropped (empty content)
                42]  # dropped (malformed)
        body = json.dumps({"message": "Tell me about the lab", "history": hist})
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 200, res
        msgs = captured["messages"]
        # 2 valid history turns + current user turn.
        assert len(msgs) == 3, msgs
        assert msgs[0]["role"] == "user", msgs
        assert msgs[1]["role"] == "assistant", msgs
        assert msgs[-1]["content"][0]["text"] == "Tell me about the lab", msgs
    finally:
        _disable_kb()


def main():
    if not _SECRET:
        print(
            "WARNING: ORIGIN_SECRET not set; the 403 case is skipped. "
            "Run with ORIGIN_SECRET=testsecret for full coverage."
        )
    tests = [
        ("grounded_answer", test_grounded_answer),
        ("quiz_attempt_refused_no_converse", test_quiz_attempt_refused_no_converse),
        ("quiz_attempt_phrase_refused", test_quiz_attempt_phrase_refused),
        ("out_of_scope_empty_retrieval", test_out_of_scope_empty_retrieval),
        ("missing_message", test_missing_message),
        ("bad_json", test_bad_json),
        ("wrong_origin_secret", test_wrong_origin_secret),
        ("converse_raises", test_converse_raises),
        ("kb_retrieval_raises", test_kb_retrieval_raises),
        ("not_configured", test_not_configured),
        ("history_included_in_messages", test_history_included_in_messages),
    ]
    for name, fn in tests:
        _run(name, fn)
    print("ALL PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
