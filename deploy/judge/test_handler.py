"""Unit tests for the judge Lambda handler. Bedrock + KB are fully mocked
(no AWS).

Run:  cd deploy/judge && ORIGIN_SECRET=testsecret python3 test_handler.py

Covers the 14 design cases (judge-kb-design.md section 6): correct pick (200);
wrong pick with no leak (200); wrong-pick non-regression after the guard (200);
letterless wrong pick with a bare verdict word (200); a leaking wrong pick that
trips the guard (502); KB retrieval failing OPEN on a correct pick (200, empty
sources); missing choice context (400); bad JSON body (400); wrong
x-origin-secret when ORIGIN_SECRET is set (403); converse raising (502); the
empty-KB byte-identical-to-today invariant (200, system == [{CHOICE_SYSTEM}],
no KB client); sources parsed + mapped to THIS repo's 6-module labels; labels
never derived from chunk content; and a wrong-pick leak still 502 on the KB
path with no sources key in the error body.
"""
import json
import os
import sys

import handler


class _FakeBedrock:
    """Stand-in for the module-level boto3 bedrock-runtime client.

    When `raise_exc`, converse() raises. Otherwise it records the converse
    kwargs into `record` (if a dict is supplied) and returns a canned text."""

    def __init__(self, text=None, raise_exc=False, record=None):
        self._text = text
        self._raise = raise_exc
        self._record = record

    def converse(self, **kwargs):
        if self._record is not None:
            self._record["kwargs"] = kwargs
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
    """Enable the KB path with a stubbed client; returns nothing (mutates
    module state the same way the tests swap `handler._bedrock`)."""
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


# 1 -------------------------------------------------------------------------
def test_correct_pick():
    # Correct pick, affirming explanation JSON -> 200, non-empty explanation,
    # mode == "choice". KB disabled.
    _disable_kb()
    handler._bedrock = _FakeBedrock(
        text=json.dumps(
            {"explanation": "Yes, that is right. Great reasoning on this one."}
        )
    )
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "pick": "4",
            "answer": "4",
            "correct": True,
            "why": "Basic arithmetic: two plus two equals four.",
            "attempt": 1,
        }
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 200, res
    out = json.loads(res["body"])
    assert out["explanation"].strip(), out
    assert out["mode"] == "choice", out


# 2 -------------------------------------------------------------------------
def test_wrong_pick_no_leak():
    # Wrong pick, canned nudge that never names the correct option "4" -> 200.
    _disable_kb()
    handler._bedrock = _FakeBedrock(
        text=json.dumps(
            {
                "explanation": (
                    "Not quite — think again about how addition combines the two "
                    "numbers before settling on a value."
                )
            }
        )
    )
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "pick": "5",
            "answer": "4",
            "correct": False,
            "why": "Basic arithmetic: two plus two equals four.",
            "attempt": 1,
        }
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 200, res
    out = json.loads(res["body"])
    expl = out["explanation"]
    assert expl.strip(), out
    # Correct option text / letter must not appear in the explanation.
    assert "4" not in expl, expl
    assert "B" not in expl, expl


# 3 -------------------------------------------------------------------------
def test_wrong_pick_still_200_after_guard():
    # Non-regression: a lettered wrong pick with a clean nudge that does NOT
    # name/quote the correct option must STILL return 200 (guard must not trip
    # on a safe nudge).
    _disable_kb()
    handler._bedrock = _FakeBedrock(
        text=json.dumps(
            {
                "explanation": (
                    "Not quite — reconsider how the pieces fit together before "
                    "settling on a conclusion about the whole system."
                )
            }
        )
    )
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "Which illustrates the fallacy of composition?",
            "options": [
                "A. Assuming a snippet writer manages whole projects",
                "B. Using external APIs to extend an LLM",
                "C. Breaking a task into subtasks",
                "D. Prompt engineering for desired outputs",
            ],
            "pick": "B. Using external APIs to extend an LLM",
            "answer": "A. Assuming a snippet writer manages whole projects",
            "correct": False,
            "why": "Composition fallacy: parts working does not imply the whole works.",
            "attempt": 1,
        }
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 200, res
    out = json.loads(res["body"])
    assert out["explanation"].strip(), out


# 4 -------------------------------------------------------------------------
def test_empty_letter_wrong_pick_200():
    # Non-regression: a letterless answer ("4", empty answer_letter) on a wrong
    # pick with a mock nudge containing a bare verdict word ("option") must
    # return 200 — the letter rules are SKIPPED on an empty letter.
    _disable_kb()
    handler._bedrock = _FakeBedrock(
        text=json.dumps(
            {
                "explanation": (
                    "Not quite — think about which option makes sense when you "
                    "combine the two numbers before you decide."
                )
            }
        )
    )
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "pick": "5",
            "answer": "4",
            "correct": False,
            "why": "Basic arithmetic: two plus two equals four.",
            "attempt": 1,
        }
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 200, res
    out = json.loads(res["body"])
    assert out["explanation"].strip(), out


# 5 -------------------------------------------------------------------------
def test_guard_trips_on_leak():
    # A crafted explanation that names the correct option on a wrong pick must
    # trip the guard -> 502 (front-end then falls back to the local hint).
    _disable_kb()
    handler._bedrock = _FakeBedrock(
        text=json.dumps(
            {"explanation": "Not quite. Actually option A is correct here."}
        )
    )
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "Which illustrates the fallacy of composition?",
            "options": [
                "A. Assuming a snippet writer manages whole projects",
                "B. Using external APIs to extend an LLM",
            ],
            "pick": "B. Using external APIs to extend an LLM",
            "answer": "A. Assuming a snippet writer manages whole projects",
            "correct": False,
            "why": "Composition fallacy: parts working does not imply the whole works.",
            "attempt": 1,
        }
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 502, res
    assert "guard tripped" in json.loads(res["body"])["error"], res


# 6 -------------------------------------------------------------------------
def test_kb_fail_open_non_wrong():
    # KB enabled, retrieve() raises, on the NON-wrong path (correct pick):
    # retrieval fails OPEN to empty context -> 200 with sources == []. Unlike
    # the assistant, a raising retrieve() does NOT become a 502.
    handler._bedrock = _FakeBedrock(
        text=json.dumps({"explanation": "Yes, that is right. Nicely done."})
    )
    try:
        _set_kb(raise_exc=True)
        body = json.dumps(
            {
                "mode": "choice",
                "prompt": "What is 2+2?",
                "options": ["3", "4", "5", "6"],
                "pick": "4",
                "answer": "4",
                "correct": True,
                "why": "Basic arithmetic.",
                "attempt": 1,
            }
        )
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 200, res
        out = json.loads(res["body"])
        assert out["explanation"].strip(), out
        assert out["sources"] == [], out
    finally:
        _disable_kb()


# 7 -------------------------------------------------------------------------
def test_missing_context():
    _disable_kb()
    handler._bedrock = _FakeBedrock(text=json.dumps({"explanation": "x"}))
    body = json.dumps(
        {"mode": "choice", "prompt": "", "pick": "", "answer": "", "why": "x"}
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 400, res
    assert "missing choice context" in json.loads(res["body"])["error"], res


# 8 -------------------------------------------------------------------------
def test_bad_json():
    res = handler.handler(_event("{not json", headers=_secret_headers()), None)
    assert res["statusCode"] == 400, res
    assert "invalid JSON" in json.loads(res["body"])["error"], res


# 9 -------------------------------------------------------------------------
def test_wrong_origin_secret():
    if not _SECRET:
        print("  skip: test_wrong_origin_secret (ORIGIN_SECRET not set)")
        return
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "Q",
            "pick": "a",
            "answer": "b",
            "why": "w",
        }
    )
    res = handler.handler(
        _event(body, headers={"x-origin-secret": "WRONG"}), None
    )
    assert res["statusCode"] == 403, res
    assert json.loads(res["body"])["error"] == "forbidden", res


# 10 ------------------------------------------------------------------------
def test_converse_raises():
    _disable_kb()
    handler._bedrock = _FakeBedrock(raise_exc=True)
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "What is 2+2?",
            "options": ["3", "4"],
            "pick": "3",
            "answer": "4",
            "correct": False,
            "why": "two plus two is four",
        }
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 502, res
    assert "judge unavailable" in json.loads(res["body"])["error"], res


# 11 ------------------------------------------------------------------------
def test_empty_kb_identical_to_today():
    # The section 4 invariant: with the KB disabled, the converse `system` is
    # byte-identical to [{"text": CHOICE_SYSTEM}] and no KB client is created.
    _disable_kb()
    record = {}
    handler._bedrock = _FakeBedrock(
        text=json.dumps({"explanation": "Yes, that is right."}),
        record=record,
    )
    body = json.dumps(
        {
            "mode": "choice",
            "prompt": "What is 2+2?",
            "options": ["3", "4"],
            "pick": "4",
            "answer": "4",
            "correct": True,
            "why": "Basic arithmetic.",
            "attempt": 1,
        }
    )
    res = handler.handler(_event(body, headers=_secret_headers()), None)
    assert res["statusCode"] == 200, res
    out = json.loads(res["body"])
    assert out["sources"] == [], out
    assert record["kwargs"]["system"] == [{"text": handler.CHOICE_SYSTEM}], record
    assert handler._kb_client is None, "no KB client must be created on empty KB"


# 12 ------------------------------------------------------------------------
def test_sources_parsed_and_mapped():
    # KB enabled: retrieve() returns an MLAGAC module deck + the lab; both map
    # to THIS repo's 6-module labels (matching the assistant), order preserved.
    handler._bedrock = _FakeBedrock(
        text=json.dumps({"explanation": "Yes, that is right. Nicely done."})
    )
    try:
        _set_kb(results=[
            _s3_result(
                "s3://my-bucket/modules/"
                "MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md",
                text="A. a leaking option string that must never appear",
            ),
            _s3_result("s3://my-bucket/docs/lab.md"),
        ])
        body = json.dumps({
            "mode": "choice",
            "prompt": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "pick": "4",
            "answer": "4",
            "correct": True,
            "why": "Basic arithmetic.",
            "attempt": 1,
        })
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 200, res
        out = json.loads(res["body"])
        assert out["sources"] == [
            {"label": "Module 3 \u2014 Security and Identity Management", "module": 3},
            {"label": "Hands-on Lab \u2014 Enhance and Scale Agents", "module": None},
        ], out
    finally:
        _disable_kb()


# 13 ------------------------------------------------------------------------
def test_source_label_never_from_content_text():
    # Labels derive ONLY from the key, never from content.text. A result whose
    # content.text looks like an option must yield only the key-derived label.
    leak = "The correct option is C. Agentic Memory Implementation"
    mapped = handler._map_sources([
        _s3_result(
            "s3://b/modules/MLAGAC-10-EN-M05-AgenticMemory_InstructorDeck.md",
            text=leak,
        ),
    ])
    assert mapped == [
        {"label": "Module 5 \u2014 Agentic Memory Implementation", "module": 5},
    ], mapped
    # No fragment of the content text leaked into the label.
    assert leak not in mapped[0]["label"], mapped
    # A result with a missing/odd location is skipped (fail-open to no-source).
    assert handler._map_sources([{"content": {"text": leak}}]) == []
    assert handler._map_sources([{"location": {"s3Location": {}}}]) == []
    # An unknown key maps to no source.
    assert handler._source_label("s3://b/misc/unknown.md") is None
    assert handler._source_label(None) is None


# 14 ------------------------------------------------------------------------
def test_wrong_pick_leak_still_502_with_kb():
    # KB enabled + a leaking explanation on a wrong pick -> guard trips 502,
    # and the 502 body carries NO sources key (the error IS the whole response).
    handler._bedrock = _FakeBedrock(
        text=json.dumps(
            {"explanation": "Not quite. Actually option A is correct here."}
        )
    )
    try:
        _set_kb(results=[
            _s3_result("s3://b/modules/MLAGAC-10-EN-M02-Runtime_InstructorDeck.md"),
        ])
        body = json.dumps({
            "mode": "choice",
            "prompt": "Which illustrates the fallacy of composition?",
            "options": [
                "A. Assuming a snippet writer manages whole projects",
                "B. Using external APIs to extend an LLM",
            ],
            "pick": "B. Using external APIs to extend an LLM",
            "answer": "A. Assuming a snippet writer manages whole projects",
            "correct": False,
            "why": "Composition fallacy.",
            "attempt": 1,
        })
        res = handler.handler(_event(body, headers=_secret_headers()), None)
        assert res["statusCode"] == 502, res
        out = json.loads(res["body"])
        assert "guard tripped" in out["error"], out
        assert "sources" not in out, out
    finally:
        _disable_kb()


def main():
    if not _SECRET:
        print(
            "WARNING: ORIGIN_SECRET not set; the 403 case is skipped. "
            "Run with ORIGIN_SECRET=testsecret for full coverage."
        )
    tests = [
        ("correct_pick", test_correct_pick),
        ("wrong_pick_no_leak", test_wrong_pick_no_leak),
        ("wrong_pick_still_200_after_guard", test_wrong_pick_still_200_after_guard),
        ("empty_letter_wrong_pick_200", test_empty_letter_wrong_pick_200),
        ("guard_trips_on_leak", test_guard_trips_on_leak),
        ("kb_fail_open_non_wrong", test_kb_fail_open_non_wrong),
        ("missing_context", test_missing_context),
        ("bad_json", test_bad_json),
        ("wrong_origin_secret", test_wrong_origin_secret),
        ("converse_raises", test_converse_raises),
        ("empty_kb_identical_to_today", test_empty_kb_identical_to_today),
        ("sources_parsed_and_mapped", test_sources_parsed_and_mapped),
        ("source_label_never_from_content_text", test_source_label_never_from_content_text),
        ("wrong_pick_leak_still_502_with_kb", test_wrong_pick_leak_still_502_with_kb),
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
