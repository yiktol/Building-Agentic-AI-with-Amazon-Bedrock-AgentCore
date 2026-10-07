#!/usr/bin/env python3
"""
Build the self-contained "Building Agentic AI with Amazon Bedrock AgentCore"
slide app from the existing ``md/`` tree.

This mirrors the reference ``Become-an-AWS-AI-Business-Strategist/slides`` app
(reveal.js image decks + speaker notes + optional audio narration), adapted to
this course's ``md/`` layout:

    md/MLAGAC-10-EN-M0N-...InstructorDeck.md     # per-slide narration (## Slide / **Narration:**)
    md/images/M0N/slide-NN.png                   # rendered slide images (full-size)
    md/audio/M0N/slide-NN.mp3                     # Polly narration audio (non-KC slides only)

For each module 1..6 this produces:
    slides/decks/images/M0N/slide-NNN.png        # copied slide PNGs (3-digit)
    slides/decks/audio/mN/slide-<n>.mp3          # copied narration audio (1-based)
    slides/decks/mN.json                         # array of slide objects (image mode)
    slides/decks/mN.js                           # window.DECK_DATA wrapper (file://)

Slide object schema (matches the reference decks/mN.json):
    n, mode="image", native="", image, student, instructor="", time="", audio

``student`` is the slide's verbatim narration taken from its **Narration:**
blockquote -- no rewriting. Audio is present only for non-knowledge-check
slides (knowledge-check slides have no .mp3 and so get audio="").

Usage:
    python3 slides/build_slides.py
    python3 slides/build_slides.py --modules 1,3
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_DIR = os.path.join(REPO_ROOT, "md")
SLIDES_DIR = os.path.join(REPO_ROOT, "slides")
DECKS_DIR = os.path.join(SLIDES_DIR, "decks")
IMAGES_DIR = os.path.join(DECKS_DIR, "images")
AUDIO_DIR = os.path.join(DECKS_DIR, "audio")

MODULES = list(range(1, 7))  # M01..M06

MODULE_TITLES = {
    1: "Foundations of Agentic AI Patterns",
    2: "AgentCore Runtime and Framework Integration",
    3: "Security and Identity Management",
    4: "Tool Integration and AgentCore Gateway",
    5: "Agentic Memory Implementation",
    6: "Production Monitoring and Observability",
}

SLIDE_HEADING_RE = re.compile(r"^##\s+Slide\s+(\d+)(?:\s+—\s+(.*))?$")


def _md_path(module: int) -> str:
    """Find the main (non-knowledge-check) module markdown file for M0N."""
    pat = os.path.join(MD_DIR, f"MLAGAC-10-EN-M{module:02d}-*_InstructorDeck.md")
    hits = [p for p in glob.glob(pat) if "KnowledgeCheck" not in p]
    return hits[0] if hits else ""


def _parse_md(md_path: str):
    """Parse a module markdown file into [{n, heading, notes}].

    Narration is the text in the slide's **Narration:** blockquote: every line
    beginning with '>' after the '**Narration:**' marker, with the leading '> '
    stripped and consecutive quote lines joined by blank lines preserved.
    """
    with open(md_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    slides = []
    i, n_lines = 0, len(lines)
    while i < n_lines:
        m = SLIDE_HEADING_RE.match(lines[i])
        if not m:
            i += 1
            continue
        n = int(m.group(1))
        heading = (m.group(2) or "").strip()
        # Scan this slide block to its **Narration:** marker, then collect quote lines.
        notes_parts = []
        j = i + 1
        in_narr = False
        while j < n_lines:
            cur = lines[j]
            if cur.strip() == "---" or SLIDE_HEADING_RE.match(cur):
                break
            if cur.strip().startswith("**Narration:**"):
                in_narr = True
                j += 1
                continue
            if in_narr:
                s = cur.strip()
                if s.startswith(">"):
                    text = s[1:].strip()
                    # Skip the placeholder for slides without notes.
                    if text and not text.startswith("_(No narration"):
                        notes_parts.append(text)
            j += 1
        notes = "\n\n".join(notes_parts).strip()
        slides.append({"n": n, "heading": heading, "notes": notes})
        i = j
    return slides


def copy_assets(module: int, slides: list) -> tuple[int, int]:
    """Copy slide PNGs (full-size) and audio (non-KC slides) into the app tree."""
    img_src_dir = os.path.join(MD_DIR, "images", f"M{module:02d}")
    audio_src_dir = os.path.join(MD_DIR, "audio", f"M{module:02d}")
    img_dst_dir = os.path.join(IMAGES_DIR, f"M{module:02d}")
    audio_dst_dir = os.path.join(AUDIO_DIR, f"m{module}")
    os.makedirs(img_dst_dir, exist_ok=True)
    os.makedirs(audio_dst_dir, exist_ok=True)
    imgs = auds = 0
    for s in slides:
        n = s["n"]
        src_img = os.path.join(img_src_dir, f"slide-{n:02d}.png")
        if os.path.isfile(src_img):
            shutil.copy2(src_img, os.path.join(img_dst_dir, f"slide-{n:03d}.png"))
            imgs += 1
        src_audio = os.path.join(audio_src_dir, f"slide-{n:02d}.mp3")
        if os.path.isfile(src_audio):
            shutil.copy2(src_audio, os.path.join(audio_dst_dir, f"slide-{n}.mp3"))
            auds += 1
    return imgs, auds


def build_deck_json(module: int, slides: list) -> list:
    audio_src_dir = os.path.join(MD_DIR, "audio", f"M{module:02d}")
    out = []
    for s in slides:
        n = s["n"]
        has_audio = os.path.isfile(os.path.join(audio_src_dir, f"slide-{n:02d}.mp3"))
        out.append({
            "n": n,
            "mode": "image",
            "native": "",
            "image": f"decks/images/M{module:02d}/slide-{n:03d}.png",
            "student": s["notes"],
            "instructor": "",
            "time": "",
            "audio": f"decks/audio/m{module}/slide-{n}.mp3" if has_audio else "",
        })
    return out


def write_outputs(module: int, slides_json: list) -> str:
    os.makedirs(DECKS_DIR, exist_ok=True)
    json_path = os.path.join(DECKS_DIR, f"m{module}.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(slides_json, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    js_path = os.path.join(DECKS_DIR, f"m{module}.js")
    compact = json.dumps(slides_json, ensure_ascii=False, separators=(", ", ": "))
    with open(js_path, "w", encoding="utf-8") as fh:
        fh.write("window.DECK_DATA = window.DECK_DATA || {};\n")
        fh.write(f'window.DECK_DATA["{module}"] = {compact};\n')
    return json_path


def process_module(module: int):
    md_path = _md_path(module)
    if not md_path:
        return {"module": module, "error": f"no markdown found for M{module:02d}"}
    slides = _parse_md(md_path)
    imgs, auds = copy_assets(module, slides)
    slides_json = build_deck_json(module, slides)
    json_path = write_outputs(module, slides_json)
    return {
        "module": module,
        "title": MODULE_TITLES.get(module, ""),
        "slides": len(slides),
        "images": imgs,
        "audio": auds,
        "json": os.path.relpath(json_path, REPO_ROOT),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules", default="")
    args = ap.parse_args()
    want = {int(m.strip()) for m in args.modules.split(",") if m.strip()}
    modules = [m for m in MODULES if not want or m in want]
    if not modules:
        print("No matching modules.", file=sys.stderr)
        sys.exit(1)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    results = []
    for m in modules:
        print(f"Processing Module {m}: {MODULE_TITLES.get(m, '')}")
        results.append(process_module(m))
    print("\nSummary:")
    for r in results:
        if r.get("error"):
            print(f"  m{r['module']}: ERROR {r['error']}")
        else:
            print(f"  m{r['module']}: {r['slides']} slides, {r['images']} images, {r['audio']} audio -> {r['json']}")
    print("\nDone. Open slides/index.html or slides/deck.html?m=<N>.")


if __name__ == "__main__":
    main()
