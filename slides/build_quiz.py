#!/usr/bin/env python3
"""
Validate the "Building Agentic AI with Amazon Bedrock AgentCore" knowledge-check
quizzes (slides/quiz/mN.json + slides/quiz/mN.js).

Each module N has a PAIR of files that MUST carry identical data:
  * slides/quiz/mN.json  — the source-of-truth JSON object.
  * slides/quiz/mN.js    — a wrapper that assigns the SAME object to
                           window.QUIZ_DATA["N"] (so quiz.html works under
                           file:// as well as over HTTP). quiz.html loads the .js
                           first and falls back to fetching the .json.

This read-only validator checks, per module:
  * both files exist and are well-formed (JSON parses; the .js object parses);
  * .js payload deep-equals the .json object (the pair never drifts);
  * top-level shape: module (== N), title, subtitle, intro, questions[];
  * per question: id == "mNq{k}" (k sequential from 1), exactly 4 options,
    0 <= answerIndex <= 3, answer == options[answerIndex] (verbatim),
    answerLetter == "ABCD"[answerIndex], non-empty prompt and why.

It does NOT check question count (modules may legitimately have different
numbers of questions) and makes no judgement about content correctness — it
guards the mechanical invariants a hand-edit can silently break.

Usage:
    python3 slides/build_quiz.py            # validate all quizzes
    python3 slides/build_quiz.py 1 3        # only m1 and m3
"""
import json
import re
import sys
from pathlib import Path

SLIDES_DIR = Path(__file__).resolve().parent
QUIZ_DIR = SLIDES_DIR / "quiz"

# Pull the object literal assigned to window.QUIZ_DATA["N"] out of the .js.
_JS_RE = re.compile(
    r'window\.QUIZ_DATA\[\s*"(?P<n>\d+)"\s*\]\s*=\s*(?P<obj>\{.*\})\s*;?\s*$',
    re.S,
)
_LETTERS = "ABCD"


def parse_js(path: Path, module: int):
    """Return (obj, problems). obj is None when the payload can't be parsed."""
    text = path.read_text(encoding="utf-8")
    m = _JS_RE.search(text)
    if not m:
        return None, [f"{path.name}: could not find window.QUIZ_DATA[\"{module}\"] = {{...}}"]
    if m.group("n") != str(module):
        return None, [f"{path.name}: assigns QUIZ_DATA[\"{m.group('n')}\"], expected \"{module}\""]
    try:
        return json.loads(m.group("obj")), []
    except json.JSONDecodeError as exc:
        return None, [f"{path.name}: embedded object is not valid JSON — {exc}"]


def validate_questions(name: str, module: int, data: dict) -> list:
    problems = []
    for field in ("module", "title", "subtitle", "intro", "questions"):
        if field not in data:
            problems.append(f"{name}: missing top-level field '{field}'")
    if data.get("module") != module:
        problems.append(f"{name}: 'module' is {data.get('module')!r}, expected {module}")
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        problems.append(f"{name}: 'questions' must be a non-empty array")
        return problems
    for k, q in enumerate(questions, start=1):
        where = f"{name} q{k}"
        if not isinstance(q, dict):
            problems.append(f"{where}: not an object"); continue
        qid = q.get("id")
        if qid != f"m{module}q{k}":
            problems.append(f"{where}: id is {qid!r}, expected 'm{module}q{k}'")
        opts = q.get("options")
        if not isinstance(opts, list) or len(opts) != 4:
            problems.append(f"{where}: expected exactly 4 options, got {len(opts) if isinstance(opts, list) else type(opts).__name__}")
            continue
        ai = q.get("answerIndex")
        if not isinstance(ai, int) or not (0 <= ai <= 3):
            problems.append(f"{where}: answerIndex must be 0..3, got {ai!r}"); continue
        if q.get("answer") != opts[ai]:
            problems.append(f"{where}: answer != options[answerIndex]")
        if q.get("answerLetter") != _LETTERS[ai]:
            problems.append(f"{where}: answerLetter is {q.get('answerLetter')!r}, expected '{_LETTERS[ai]}'")
        if not str(q.get("prompt", "")).strip():
            problems.append(f"{where}: empty prompt")
        if not str(q.get("why", "")).strip():
            problems.append(f"{where}: empty why")
    return problems


def process_module(module: int) -> list:
    json_path = QUIZ_DIR / f"m{module}.json"
    js_path = QUIZ_DIR / f"m{module}.js"
    problems = []
    if not json_path.exists():
        problems.append(f"m{module}.json: not found")
    if not js_path.exists():
        problems.append(f"m{module}.js: not found")
    if problems:
        return problems

    try:
        jdata = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{json_path.name}: invalid JSON — {exc}"]

    jsdata, js_problems = parse_js(js_path, module)
    problems.extend(js_problems)

    problems.extend(validate_questions(json_path.name, module, jdata))

    if jsdata is not None and jsdata != jdata:
        problems.append(f"m{module}: .js payload does not match .json (the pair has drifted)")

    if problems:
        return problems

    n = len(jdata["questions"])
    letters = "".join(q["answerLetter"] for q in jdata["questions"])
    print(f"[ok] m{module}: {n} questions, answers {letters}, .js==.json")
    return []


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        modules = [int(a) for a in args]
    else:
        modules = sorted(int(p.stem[1:]) for p in QUIZ_DIR.glob("m*.json"))
    if not modules:
        print("No quizzes found in", QUIZ_DIR); sys.exit(1)
    all_problems = []
    for m in modules:
        all_problems.extend(process_module(m))
    if all_problems:
        print("\n[FAIL] Quiz validation problems:")
        for prob in all_problems:
            print("  -", prob)
        sys.exit(1)
    print("\nAll quizzes valid.")


if __name__ == "__main__":
    main()
