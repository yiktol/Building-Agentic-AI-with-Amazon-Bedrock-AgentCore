#!/bin/bash
################################################################################
# build_corpus.sh — assemble the project-level KB corpus staging dir.
#
# Stages (does NOT upload) the course module decks + lab guide into a clean
# staging directory for `aws s3 sync` (upload + ingestion live in the deploy
# script).
#
# Corpus (design §2 / §3.5), re-derived for THIS repo's real filenames:
#   - module decks: md/MLAGAC-*-EN-M0*-*_InstructorDeck.md
#                   EXCLUDING *_KnowledgeCheck.md (one word — this repo's
#                   knowledge-check files, which carry quiz answers)
#   - lab doc: slides/docs/lab.md  (plain .md only; the lab.md.js viewer
#              wrapper is NEVER globbed)
#
# Staging layout (the handler's S3-URI parser expects these keys):
#   modules/MLAGAC-...-M0N-..._InstructorDeck.md   (original basename)
#   docs/lab.md                                    (normalized basename)
#
# Each deck is copied through a line filter that DROPS only slide-image noise
# lines (lstrip().startswith("![")); every other line is preserved verbatim.
# These decks render narration inline as blockquotes under a **Narration:**
# header — there is NO standalone audio-link line, so the reference's audio
# filter is dropped (nothing matches it). The lab doc is copied unmodified.
#
# A POSITIVE provenance allow-list + hard exclusion gates run before the caller
# syncs, so the corpus can never contain a KnowledgeCheck (answers) or a viewer
# wrapper (.md.js).
#
# NOTE: the allow-list matches module numbers M01–M09 (single digit after M0).
# This is a deliberate ceiling: a future M10+ deck would be rejected here and
# must widen the allow-list pattern. The copy glob (M0*) and the handler regex
# (M0?(\d+)) accept more; this gate is the strict provenance floor.
#
# Usage: build_corpus.sh [STAGING_DIR]   (default: deploy/kb/.staging)
################################################################################
set -euo pipefail

# Pin REPO_ROOT from the script's own location so a wrong cwd can never
# silently stage zero files; every corpus glob is absolute off $REPO_ROOT.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

STAGING_DIR="${1:-$REPO_ROOT/deploy/kb/.staging}"

# Fresh staging dir each run (deterministic re-runs).
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/modules" "$STAGING_DIR/docs"

################################################################################
# Decks: md/MLAGAC-*-EN-M0*-*_InstructorDeck.md excluding *_KnowledgeCheck.md,
# with slide-image noise stripped.
################################################################################
staged_modules=0
for deck in "$REPO_ROOT"/md/MLAGAC-*-EN-M0*-*_InstructorDeck.md; do
    [ -f "$deck" ] || continue
    base="$(basename "$deck")"
    # Hard exclusion: KnowledgeCheck decks carry quiz answers.
    case "$base" in
        *_KnowledgeCheck.md) continue ;;
    esac
    # Positive provenance — the source must be an allow-listed
    # MLAGAC-...-M0[1-9]-..._InstructorDeck.md deck. Verified here, at copy time.
    case "$base" in
        MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md) ;;
        *)
            echo "ERROR: deck '$base' is not an allow-listed MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md" >&2
            exit 1 ;;
    esac
    # Drop only slide-image noise lines (lstrip().startswith("![")).
    # startswith semantics (python3), NOT an emoji grep -E regex (that hangs).
    python3 - "$deck" > "$STAGING_DIR/modules/$base" <<'PYEOF'
import sys
src = sys.argv[1]
with open(src, "r", encoding="utf-8") as fh:
    for line in fh:
        if line.lstrip().startswith("!["):
            continue
        sys.stdout.write(line)
PYEOF
    staged_modules=$((staged_modules + 1))
done

################################################################################
# Docs: exactly lab.md (plain .md), verbatim. Source is slides/docs/lab.md;
# it is normalized to the basename lab.md so _DOC_LABELS["lab.md"] resolves it.
################################################################################
doc="$REPO_ROOT/slides/docs/lab.md"
if [ ! -f "$doc" ]; then
    echo "ERROR: required doc missing: $doc" >&2
    exit 1
fi
cp "$doc" "$STAGING_DIR/docs/lab.md"

################################################################################
# Positive provenance allow-list + hard exclusion gates (before sync).
################################################################################

# 1. Every staged modules file MUST match MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md
#    (and the copy loop above already excluded *_KnowledgeCheck.md source decks).
for f in "$STAGING_DIR"/modules/*.md; do
    [ -f "$f" ] || continue
    b="$(basename "$f")"
    case "$b" in
        MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md) ;;
        *)
            echo "ERROR: staged modules file not in allow-list: $b" >&2
            exit 1 ;;
    esac
done

# 2. Every staged docs file MUST be exactly lab.md.
for f in "$STAGING_DIR"/docs/*; do
    [ -e "$f" ] || continue
    b="$(basename "$f")"
    case "$b" in
        lab.md) ;;
        *)
            echo "ERROR: staged docs file not in allow-list: $b" >&2
            exit 1 ;;
    esac
done

# 3a. ADDITIONAL hard gate: zero KnowledgeCheck / .md.js anywhere under staging.
leaked="$(find "$STAGING_DIR" \( -name '*_KnowledgeCheck.md' -o -name '*.md.js' \) )"
if [ -n "$leaked" ]; then
    echo "ERROR: forbidden files staged (KnowledgeCheck or .md.js):" >&2
    echo "$leaked" >&2
    exit 1
fi

# 3b. The lab doc must be present.
if [ ! -f "$STAGING_DIR/docs/lab.md" ]; then
    echo "ERROR: required doc not staged: lab.md" >&2
    exit 1
fi

# 3c. Count floor (>=7 = 6 decks + 1 doc today), NOT ==7, so a future M07 deck
#     grows the corpus and still passes.
total="$(find "$STAGING_DIR" -type f -name '*.md' | wc -l | tr -d ' ')"
if [ "$total" -lt 7 ]; then
    echo "ERROR: staged corpus too small ($total files; expected >= 7)" >&2
    exit 1
fi

################################################################################
# Report for the deploy log.
################################################################################
echo "Staged corpus under: $STAGING_DIR"
echo "  modules decks: $staged_modules"
echo "  total .md files: $total"
echo "Files:"
find "$STAGING_DIR" -type f | sort | sed 's#^#  #'
exit 0
