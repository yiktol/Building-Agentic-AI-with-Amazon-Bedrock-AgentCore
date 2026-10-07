#!/usr/bin/env python3
"""
Validate the "Building Agentic AI with Amazon Bedrock AgentCore" slide decks
(slides/decks/mN.json).

Checks schema, valid modes, sequential slide objects, and that every referenced
local image exists on disk. Additionally verifies that whenever a slide declares
a non-empty `audio` path, that audio file exists on disk. Read-only.

Note: slide `n` values are the ORIGINAL .pptx slide numbers and may contain gaps
where knowledge-check slides were removed, so numbering is checked for strictly
increasing order rather than a contiguous 1..N run.

Usage:
    python3 slides/build_decks.py            # validate all decks
    python3 slides/build_decks.py 1 3        # only m1 and m3
"""
import json
import sys
from collections import Counter
from pathlib import Path

SLIDES_DIR = Path(__file__).resolve().parent
DECKS_DIR = SLIDES_DIR / "decks"

REQUIRED = {"n", "mode"}
VALID_MODES = {"native", "image"}


def validate_deck(path: Path, slides: list) -> list:
    problems = []
    if not isinstance(slides, list) or not slides:
        return [f"{path.name}: expected a non-empty JSON array"]
    for i, s in enumerate(slides, start=1):
        where = f"{path.name} slide #{i}"
        if not isinstance(s, dict):
            problems.append(f"{where}: not an object"); continue
        missing = REQUIRED - s.keys()
        if missing:
            problems.append(f"{where}: missing fields {sorted(missing)}")
        mode = s.get("mode")
        if mode not in VALID_MODES:
            problems.append(f"{where}: mode must be one of {sorted(VALID_MODES)}")
        if mode == "native" and not s.get("native"):
            problems.append(f"{where}: mode 'native' but 'native' HTML is empty")
        if mode == "image":
            img = s.get("image", "")
            if not img:
                problems.append(f"{where}: mode 'image' but 'image' path is empty")
            elif not (SLIDES_DIR / img).exists():
                problems.append(f"{where}: image not found on disk: {img}")
        audio = s.get("audio", "")
        if audio and not (SLIDES_DIR / audio).exists():
            problems.append(f"{where}: audio not found on disk: {audio}")
    nums = [s.get("n") for s in slides if isinstance(s, dict)]
    if any(b <= a for a, b in zip(nums, nums[1:])):
        problems.append(f"{path.name}: slide numbers not strictly increasing (got {nums})")
    return problems


def process_deck(path: Path) -> list:
    try:
        slides = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path.name}: invalid JSON — {exc}"]
    problems = validate_deck(path, slides)
    if problems:
        return problems
    modes = Counter(s.get("mode") for s in slides)
    mode_note = " ".join(f"{k}:{v}" for k, v in sorted(modes.items()))
    with_audio = sum(1 for s in slides if s.get("audio"))
    print(f"[ok] {path.name}: {len(slides)} slides ({mode_note}), {with_audio} with audio")
    return []


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        modules = [int(a) for a in args]
    else:
        modules = sorted(int(p.stem[1:]) for p in DECKS_DIR.glob("m*.json"))
    if not modules:
        print("No decks found in", DECKS_DIR); sys.exit(1)
    all_problems = []
    for m in modules:
        path = DECKS_DIR / f"m{m}.json"
        if not path.exists():
            all_problems.append(f"{path.name}: not found"); continue
        all_problems.extend(process_deck(path))
    if all_problems:
        print("\n[FAIL] Deck validation problems:")
        for prob in all_problems:
            print("  -", prob)
        sys.exit(1)
    print("\nAll decks valid.")


if __name__ == "__main__":
    main()
