# Verification — Port the KB-grounded Course Assistant + Bedrock KB

Iteration: FIRST (no `review.json` present at start; only `design-review.json`).
All offline verification was run from the repo root. AWS-dependent integration
(KB create + ingestion, CloudFront `/assistant*` → Function URL via OAC,
end-to-end grounded answer) cannot be verified offline and is validated only on
a real deploy.

## Results

### 1. Assistant unit tests — ALL PASS
```
cd deploy/assistant && ORIGIN_SECRET=testsecret python3 test_handler.py
```
Output ended with `ALL PASS` (11 cases: grounded_answer, quiz_attempt_refused_no_converse,
quiz_attempt_phrase_refused, out_of_scope_empty_retrieval, missing_message,
bad_json, wrong_origin_secret, converse_raises, kb_retrieval_raises,
not_configured, history_included_in_messages). The grounded case asserts THIS
repo's S3-URI↔label contract:
`s3://my-bucket/modules/MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md`
→ `Module 3 — Security and Identity Management`, and `s3://my-bucket/docs/lab.md`
→ `Hands-on Lab — Enhance and Scale Agents`.

(The judge was NOT KB-upgraded — design §6 DECISION = SKIP — so there are no new
judge tests to run.)

### 2. Python `ast.parse` — all parse
`deploy/assistant/handler.py`, `deploy/assistant/test_handler.py`,
`slides/serve_with_judge.py` → each parsed OK.

### 3. `bash -n` — no syntax errors
`deploy/kb/build_corpus.sh` → ok. `deploy/agc-slides-deploy.sh` → ok.

### 4. cfn-lint + YAML well-formedness — parse clean
cfn-lint 1.56.0:
- `deploy/agc-slides-root.yaml` → exit 0.
- `deploy/agc-slides-assistant.yaml` → exit 4 (W1020 Fn::Sub-no-vars; IDENTICAL
  to the existing `agc-slides-judge.yaml` and the reference `assistant.yaml`).
- `deploy/kb/kb.yaml` → exit 4 (W3005 redundant DependsOn; IDENTICAL to the
  reference `kb/kb.yaml`).
- `deploy/agc-slides-cloudfront.yaml` → exit 4 (W3045 legacy AccessControl;
  pre-existing on the log bucket, unrelated to the assistant additions).
All four also loaded cleanly via a PyYAML loader that ignores the CFN
short-tags. Warnings-only (exit 4) is treated as non-fatal per the plan, and
every warning is pre-existing/parity, not introduced by this port.

### 5. build_corpus.sh against a temp dir — contract holds
Ran `bash deploy/kb/build_corpus.sh "$TMP"` and asserted:
- 6 `*_InstructorDeck.md` under `modules/` (M01–M06).
- `docs/lab.md` present.
- zero `*_KnowledgeCheck.md` / `*.md.js` anywhere.
- `>= 7` `.md` files total.
- every staged module basename matches the handler's `_MODULE_KEY_RE`.
Temp dir removed afterward.

### 6. slides/index.html widget — valid, additive
- `html.parser` parsed the file without exception.
- exactly one `</body>` and one `</style>`.
- `caLauncher`, `caPanel`, `agc-assistant-history`, `/assistant` all present.
- node v25.6.1 `node --check` on the extracted IIFE → JS syntax OK (temp file
  removed).
- existing page content preserved (added before `</style>` and before
  `</body>`; the `git diff` shows only insertions).

### Judge untouched (design §6)
`git status --porcelain deploy/judge/handler.py deploy/agc-slides-judge.yaml`
is empty (no changes). The root `JudgeStack` still passes only `ProjectPrefix`,
`JudgeModelId`, `OriginSecret`, `CloudFrontDistributionArn`.

## Not verifiable offline (requires AWS)
- KB stack create + ingestion to COMPLETE (embedding dimension coupling).
- CloudFront `/assistant*` → Function URL via OAC with x-origin-secret.
- End-to-end grounded answer + sources.
These are validated only on a real deploy, in the order
`./agc-slides-deploy.sh kb` → `./agc-slides-deploy.sh`.
