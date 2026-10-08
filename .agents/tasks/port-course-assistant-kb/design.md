# Design — Port the KB-grounded Course Assistant into `agc-slides`

## Overview

This design ports the "course assistant" pattern (a Knowledge-Base-grounded Q&A
chatbot) and its backing Amazon Bedrock Knowledge Base from the reference repo
(`temp/agentic-ai-foundations`) into the target repo
(`Building-Agentic-AI-with-Amazon-Bedrock-AgentCore`), matching the target's
existing `agc` conventions. The target already ships a working **older** judge
Lambda (no KB grounding), a CloudFront distribution with a `/judge*` behavior +
Lambda-OAC origin, a private S3 content bucket, and an `agc-slides-root.yaml`
that nests `ContentBucketStack`, `JudgeStack`, and `CloudFrontDistributionStack`
by S3 URL under short remote names (`s3.yaml`, `judge.yaml`, `cloudfront.yaml`).

The port adds, parallel to the judge:

1. A new **assistant Lambda** (`agc-course-assistant`) that answers learner
   questions grounded strictly in the course KB, refuses quiz pastes, and cites
   sources.
2. A new **Bedrock Knowledge Base** deployed as a **sibling** stack
   (`agc-slides-kb`, *not* nested in the root) whose corpus is this repo's
   `md/` decks + the lab doc.
3. A new `AssistantStack` nested in the root parallel to `JudgeStack`, reusing
   the single shared `OriginSecret`, the self-referential distribution ARN, and
   threading the KB params through.
4. A `/assistant*` CloudFront behavior + assistant Function-URL origin.
5. A front-end chat widget in `slides/index.html` and a `/assistant` proxy in
   `slides/serve_with_judge.py`.

The KB wiring is **gated**: the assistant renders a 503 "not configured" until a
KB id is threaded in, which happens only after the KB stack exists *and* its
ingestion sentinel reads `COMPLETE:<kbid>`. This mirrors the reference exactly.

**Technology stack (locked):** Python 3.12 Lambda (`handler.handler`), boto3
`bedrock-runtime` (`converse`) + `bedrock-agent-runtime` (`retrieve`); Bedrock
model `global.anthropic.claude-haiku-4-5-20251001-v1:0`; embeddings
`cohere.embed-english-v3` (1024-dim) on S3 Vectors; CloudFormation (YAML),
nested + one sibling stack; bash deploy script; region `ap-southeast-1`;
`ProjectPrefix=agc`. No new runtime dependencies beyond boto3 (bundled in the
Lambda runtime). The front-end stays dependency-free vanilla JS.

---

## 1. The real target corpus and the derived handler maps

### 1.1 Actual `md/` filenames (this repo)

The target course is a **6-module AgentCore course** (NOT the reference's
8-module course). The real files under `md/` are:

```
MLAGAC-10-EN-M01-Foundations_InstructorDeck.md
MLAGAC-10-EN-M01-Foundations_InstructorDeck_KnowledgeCheck.md
MLAGAC-10-EN-M02-Runtime_InstructorDeck.md
MLAGAC-10-EN-M02-Runtime_InstructorDeck_KnowledgeCheck.md
MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md
MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck_KnowledgeCheck.md
MLAGAC-10-EN-M04-ToolsAndGateway_InstructorDeck.md
MLAGAC-10-EN-M04-ToolsAndGateway_InstructorDeck_KnowledgeCheck.md
MLAGAC-10-EN-M05-Memory_InstructorDeck.md
MLAGAC-10-EN-M05-Memory_InstructorDeck_KnowledgeCheck.md
MLAGAC-10-EN-M06-DeploymentObservablity_InstructorDeck.md
MLAGAC-10-EN-M06-DeploymentObservablity_InstructorDeck_KnowledgeCheck.md
MLAGAC-10-EN-Lab-EnhanceAndScaleAgents.md
```

Plus `slides/docs/lab.md` (identical content to the Lab deck; also a corpus
doc). Note the differences from the reference that the port MUST account for:

- Filename stem is `MLAGAC-10-EN-M0N-<Name>_InstructorDeck.md`, **not**
  `Module_0N_..._InstructorDeck.md`.
- Knowledge-check files end `..._KnowledgeCheck.md` (one word, no underscore
  between "Knowledge" and "Check") — the reference used `_Knowledge_Check.md`.
- There is one Lab deck (`...-Lab-EnhanceAndScaleAgents.md`) and no
  `lab1/lab2/qs-student-guide` docs.

### 1.2 Human-readable titles (`MODULE_TITLES`)

Derived from `slides/index.html`'s module list (the authoritative course-facing
titles), keyed by module number:

```python
MODULE_TITLES = {
    1: "Foundations of Agentic AI Patterns",
    2: "AgentCore Runtime and Framework Integration",
    3: "Security and Identity Management",
    4: "Tool Integration and AgentCore Gateway",
    5: "Agentic Memory Implementation",
    6: "Production Monitoring and Observability",
}
```

### 1.3 Doc labels (`_DOC_LABELS`)

The non-module corpus doc is the lab. Keyed by the **basename as staged** (see
§2 for the staging contract):

```python
_DOC_LABELS = {
    "lab.md": "Hands-on Lab — Enhance and Scale Agents",
}
```

### 1.4 Module key regex (`_MODULE_KEY_RE`)

Must match this repo's real staged module basenames (see §2 — modules are staged
under their original `MLAGAC-...` basenames). The regex captures the module
number from `M0N` and a trailing descriptive segment:

```python
_MODULE_KEY_RE = re.compile(
    r"^MLAGAC-\d+-EN-M0?(\d+)-(.+?)_InstructorDeck\.md$", re.I
)
```

- Group 1 = module number (`01`→1 … `06`→6), consumed by `MODULE_TITLES`.
- Group 2 = the `<Name>` stem (e.g. `Foundations`, `SecurityAndIdentity`), used
  only as a fallback title when a module number is somehow absent from
  `MODULE_TITLES` (it never is for 1–6, so the map always wins). The fallback
  applies `re.sub(r"[_-]+", " ", group2)` then a space-split camel-case
  softening is **not** attempted — the map is authoritative; the fallback is a
  defensive last resort only.

The Lab deck basename (`MLAGAC-10-EN-Lab-EnhanceAndScaleAgents.md`) does **not**
match `_MODULE_KEY_RE` (no `M0N`), so it falls through to the `_DOC_LABELS`
lookup. To make that lookup succeed it is staged as `docs/lab.md` (§2), so
`_DOC_LABELS["lab.md"]` resolves it. This is the single reason the staging
basename for the lab is normalized to `lab.md`.

Everything else about `_source_label` / `_map_sources` is copied **verbatim**
from the reference (strip `s3://bucket/`, take basename, cap `_SOURCES_CAP=3`,
dedupe by label preserving rank order). Only the three maps/regex above change.

---

## 2. Corpus staging layout and the S3-URI ↔ handler contract

This is the single most error-prone coupling: the keys `build_corpus.sh` writes
to S3 MUST be parseable by the handler's `_source_label`. **Chosen contract,
stated explicitly:**

```
s3://<datasource-bucket>/
  modules/MLAGAC-10-EN-M01-Foundations_InstructorDeck.md
  modules/MLAGAC-10-EN-M02-Runtime_InstructorDeck.md
  modules/MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md
  modules/MLAGAC-10-EN-M04-ToolsAndGateway_InstructorDeck.md
  modules/MLAGAC-10-EN-M05-Memory_InstructorDeck.md
  modules/MLAGAC-10-EN-M06-DeploymentObservablity_InstructorDeck.md
  docs/lab.md
```

Rules of the contract:

- **Modules** keep their original `MLAGAC-...InstructorDeck.md` basename under a
  `modules/` prefix. `_source_label` ignores the prefix (it takes the basename
  via `key.rsplit("/", 1)[-1]`), then `_MODULE_KEY_RE` matches that basename.
- **Lab** is copied to `docs/lab.md` (basename normalized to `lab.md`). The
  source for `docs/lab.md` is `slides/docs/lab.md` (already present and
  identical to the `md/` Lab deck). Using the slides copy keeps a single staging
  source for the doc and avoids renaming the long `md/` Lab filename.
- **Knowledge-check files are NEVER staged** (they contain quiz answers; the
  assistant must never ground on them). This is enforced by both a copy-time
  allow-list and a post-stage hard gate (§3, build_corpus.sh).
- The handler reads **only** `result["location"]["s3Location"]["uri"]`, strips
  `s3://` + bucket, and matches the basename. Prefixes (`modules/`, `docs/`) are
  cosmetic for the handler but keep the bucket organized and the gates simple.

Agreement check (must hold, verified by the unit test in §3):
`s3://b/modules/MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md`
→ `_MODULE_KEY_RE` matches `M03` → `MODULE_TITLES[3]` →
`{"label": "Module 3 — Security and Identity Management", "module": 3}`.
`s3://b/docs/lab.md` → no module match → `_DOC_LABELS["lab.md"]` →
`{"label": "Hands-on Lab — Enhance and Scale Agents", "module": None}`.

---

## 3. Files to create / edit

All new local template files follow the `agc-slides-<name>.yaml` convention and
are staged to S3 under the SHORT remote name the root template references.

### 3.1 `deploy/assistant/handler.py` (CREATE)

Port of the reference assistant handler. Copy verbatim **except**:

- Replace `MODULE_TITLES`, `_DOC_LABELS`, `_MODULE_KEY_RE` with the §1 values.
- Change `SESSION_KEY`-adjacent copy only in the front-end, not here.
- Update the two user-facing strings that name the course:
  - `ASSISTANT_SYSTEM` course name →
    `"Building Agentic AI with Amazon Bedrock AgentCore"`.
  - Keep the quiz-refusal guard (`_is_quiz_attempt`, `_QUIZ_REFUSAL`) verbatim —
    it is pure regex/substring and course-agnostic.

Behavior (unchanged from reference):
- Env: `BEDROCK_REGION`, `ASSISTANT_MODEL_ID`
  (`global.anthropic.claude-haiku-4-5-20251001-v1:0`), `ORIGIN_SECRET`,
  `KNOWLEDGE_BASE_ID`, optional `KB_NUM_RESULTS` (default 4).
- `_KB_ID` empty ⇒ 503 "assistant not configured".
- Retrieval is **fail-closed** (unlike the judge): any `retrieve`/`converse`
  exception ⇒ 502 (the front-end treats non-200 as a soft failure).
- Quiz paste ⇒ 200 with the refusal text and `sources: []`, WITHOUT calling
  `converse`.

### 3.2 `deploy/assistant/test_handler.py` (CREATE)

Port of the reference tests, Bedrock + KB fully mocked, run with
`cd deploy/assistant && ORIGIN_SECRET=testsecret python3 test_handler.py`.
Change the fixtures so the S3 URIs and expected labels use THIS repo's contract:

- `test_grounded_answer` uses
  `s3://my-bucket/modules/MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md`
  and `s3://my-bucket/docs/lab.md`, expecting
  `[{"label": "Module 3 — Security and Identity Management", "module": 3},
    {"label": "Hands-on Lab — Enhance and Scale Agents", "module": None}]`.
- All other S3 fixtures (`s3://b/docs/lab1.md` etc.) are replaced with
  `s3://b/docs/lab.md`.
- Keep every status-code case: 200 grounded, 200 quiz-refusal (no converse),
  200 empty-retrieval redirect, 400 missing message, 400 bad JSON, 403 wrong
  secret, 502 converse raises, 502 retrieval raises, 503 not configured, and
  history-included.

This test is the executable guard that §2's contract holds; CI/local run must
print `ALL PASS`.

### 3.3 `deploy/agc-slides-assistant.yaml` (CREATE; staged as `assistant.yaml`)

Port of the reference `assistant.yaml` with `agc` naming:

- `ProjectPrefix` default `agc`.
- `AssistantFunction` FunctionName `!Sub "${ProjectPrefix}-course-assistant"`;
  role `!Sub "${ProjectPrefix}-course-assistant-role"`.
- Parameters: `AssistantModelId`
  (`global.anthropic.claude-haiku-4-5-20251001-v1:0`), `OriginSecret`,
  `ReservedConcurrency` (default 3), `CloudFrontDistributionArn` (default ""),
  `KnowledgeBaseId` (default ""), `KnowledgeBaseArn` (default ""),
  `EmbeddingModelId` (default `cohere.embed-english-v3`).
- `Conditions`: `HasDistributionArn`, `HasKnowledgeBase`.
- Base `BedrockInvoke` policy (fan-out foundation-model + inference-profile
  ARNs) is byte-identical to the judge's and the reference assistant's.
- Separate conditional `AssistantKbPolicy` (`Condition: HasKnowledgeBase`)
  granting `bedrock:Retrieve` on `KnowledgeBaseArn` + `bedrock:InvokeModel` on
  the embedding model — so the base role is identical when KB is empty.
- Function URL `AuthType: AWS_IAM`, `InvokeMode: BUFFERED`, CORS POST +
  `content-type,x-origin-secret`.
- Two `AWS::Lambda::Permission` resources (`InvokeFunctionUrl` +
  `InvokeFunction`) scoped by `aws:SourceArn` when the dist ARN is set, else
  `SourceAccount`.
- Inline 503 stub `ZipFile` ("assistant code not yet published"); real code is
  published by the deploy script.
- Outputs: `AssistantFunctionName` (+ Export), `AssistantFunctionUrl`,
  `AssistantFunctionUrlDomain` (= `!Select [2, !Split ["/", FunctionUrl]]`, +
  Export).

### 3.4 `deploy/kb/kb.yaml` (CREATE; SIBLING stack, not staged/nested)

Port of the reference `kb/kb.yaml`, `ProjectPrefix` default `agc`:

- `DataSourceBucket` `!Sub "${ProjectPrefix}-kb-datasource-${AWS::AccountId}"`.
- S3 Vectors bucket `${ProjectPrefix}-kb-vectors-${AWS::AccountId}`, index
  `${ProjectPrefix}-kb-index`, `Dimension: 1024`, `DistanceMetric: cosine`,
  `MetadataConfiguration.NonFilterableMetadataKeys` = the four Bedrock-managed
  keys (verbatim — avoids the 2048-byte filterable-metadata ingestion failure).
- `KnowledgeBaseRole` `${ProjectPrefix}-kb-role` with the three scoped inline
  policies (foundation-model invoke on `EmbeddingModelId`, S3 data-source
  get/list, S3 Vectors put/get/delete/query/getIndex).
- `KnowledgeBase` `${ProjectPrefix}-course-kb`, S3_VECTORS storage; data source
  `${ProjectPrefix}-kb-datasource` with FIXED_SIZE chunking (512 tokens, 20%
  overlap).
- SSM discovery params `${ProjectPrefix}-kb-id`,
  `${ProjectPrefix}-kb-datasource-id`, `${ProjectPrefix}-kb-datasource-bucket`.
- Outputs: `KnowledgeBaseId`, `KnowledgeBaseArn`
  (`arn:aws:bedrock:${Region}:${Account}:knowledge-base/${KnowledgeBase}`),
  `DataSourceId`, `DataSourceBucketName`.

`EmbeddingModelId` and the index `Dimension` are coupled and both default to the
cohere 1024-dim pairing — keep the coupling comment.

### 3.5 `deploy/kb/build_corpus.sh` (CREATE)

Port of the reference, **re-derived for this repo's real formats** (this is the
most-changed file). It stages, does not upload. Pin `REPO_ROOT` from
`${BASH_SOURCE[0]}/../..` so a wrong cwd cannot silently stage zero files.

Staging (per §2):

- **Modules:** iterate `"$REPO_ROOT"/md/MLAGAC-*-EN-M0*-*_InstructorDeck.md`.
  - Hard-exclude any `*_KnowledgeCheck.md` (note: single word — this is the
    exclusion that differs from the reference's `*_Knowledge_Check.md`).
  - Positive provenance allow-list at copy time: basename must match
    `MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md` and must NOT be `*_KnowledgeCheck.md`.
  - Copy through a **re-derived noise filter**. This repo's noise lines are NOT
    the reference's `![Slide ` / `🔊 Audio narration:`. From the real decks,
    drop:
    - slide-image lines matching `^!\[` (e.g. `![M01 slide 1](images/M01/slide-01.png)`),
    - lines that are exactly the slide separator noise is kept (`---` is
      meaningful structure — keep it),
    - audio: these decks render narration inline as blockquotes under a
      `**Narration:**` header; there is NO standalone audio-link line to strip,
      so the audio filter from the reference is **dropped** (nothing matches it).
    Implement the filter in `python3` with explicit `startswith`/regex (NOT an
    emoji `grep -E`, which can hang): drop a line iff
    `line.lstrip().startswith("![")`. Preserve every other line verbatim.
- **Docs:** copy `"$REPO_ROOT"/slides/docs/lab.md` → `$STAGING_DIR/docs/lab.md`
  (error out if missing).

Post-stage gates (before the caller syncs):

1. Every `modules/*.md` basename matches
   `MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md`.
2. Every `docs/*` basename is exactly `lab.md`.
3. Hard gate: zero `*_KnowledgeCheck.md` and zero `*.md.js` anywhere under
   staging (`find ... \( -name '*_KnowledgeCheck.md' -o -name '*.md.js' \)` must
   be empty). This blocks the `slides/docs/lab.md.js` viewer wrapper and any
   knowledge-check.
4. Count floor: `>= 7` `.md` files (6 module decks + 1 lab doc), using `-lt 7`
   so a future M07 deck grows the corpus and still passes. (Reference used 11;
   this repo's floor is 7.)

Report the staged tree to the deploy log.

### 3.6 `deploy/agc-slides-cloudfront.yaml` (EDIT)

Add the assistant alongside the existing judge (keep everything judge intact):

- New parameter `AssistantFunctionUrlDomain` (String).
- Reuse the existing single `LambdaOriginAccessControl` (type `lambda`) for the
  assistant origin — no second lambda OAC needed.
- New origin `${ProjectPrefix}-assistant` (DomainName
  `!Ref AssistantFunctionUrlDomain`, same `LambdaOriginAccessControl`,
  `https-only`, TLSv1.2, 443, `OriginCustomHeaders` x-origin-secret =
  `!Ref OriginSecret`) — exact parallel to the `${ProjectPrefix}-judge` origin.
- New cache behavior `/assistant*` → `${ProjectPrefix}-assistant`, caching
  disabled (`4135ea2d-...`), `OriginRequestPolicyId` AllViewerExceptHostHeader
  (`b689b0a8-...`), methods `[GET,HEAD,OPTIONS,PUT,POST,PATCH,DELETE]`, NO
  viewer-request function association — exact parallel to `/judge*`.

The `OriginSecret` parameter already exists in this template; it is reused for
the assistant origin header (single shared secret for both backends).

### 3.7 `deploy/agc-slides-root.yaml` (EDIT)

Thread the assistant + KB params through (see §4 for the full wiring):

- Add parameters: `AssistantModelId`
  (`global.anthropic.claude-haiku-4-5-20251001-v1:0`), `ReservedConcurrency`
  (default 3), `KnowledgeBaseId` (""), `KnowledgeBaseArn` (""),
  `EmbeddingModelId` (`cohere.embed-english-v3`).
- Add nested `AssistantStack` (TemplateURL `.../${Prefix}/assistant.yaml`)
  parallel to `JudgeStack`, passing `ProjectPrefix`, `AssistantModelId`,
  `OriginSecret`, `ReservedConcurrency`,
  `CloudFrontDistributionArn: !Ref JudgeDistributionArn` (reuse the same
  self-ref ARN), `KnowledgeBaseId`, `KnowledgeBaseArn`, `EmbeddingModelId`.
- Pass `JudgeStack` the new KB params too **only if** judge KB-grounding is
  adopted (see §6 decision — it is **skipped**, so JudgeStack params are left
  unchanged).
- Add `AssistantFunctionUrlDomain:
  !GetAtt AssistantStack.Outputs.AssistantFunctionUrlDomain` to the
  `CloudFrontDistributionStack` params.
- Add outputs `AssistantFunctionName`
  (`!GetAtt AssistantStack.Outputs.AssistantFunctionName`) and
  `AssistantFunctionUrl`.

The KB stack is deployed **as a sibling** by the deploy script and is NOT nested
in the root; the root only receives the resolved KB id/arn as parameters.

### 3.8 `deploy/agc-slides-deploy.sh` (EDIT) — see §5.

### 3.9 `slides/index.html` (EDIT)

Append the course-assistant chat widget, ported from the reference index.html:

- Add the `.ca-*` CSS block to the existing `<style>` (before `</style>`). It
  uses existing CSS vars (`--navy`, `--blue`, `--orange`, `--card`, `--line`,
  `--ink`, `--muted`, `--bg`, `--radius`, `--shadow`, `--shadow-hover`), all of
  which already exist in this repo's `:root`, so it renders in the AgentCore
  palette with no CSS additions. (Note the palette: `--orange` is #1DB893
  teal-green here — the widget simply inherits it.)
- Add the launcher button + panel markup before `</body>`, with the title
  `Course Assistant` / subtitle `Amazon Bedrock AgentCore`.
- Add the IIFE: POSTs `{message, history}` to `/assistant` (overridable with
  `?assistant=<url>`, disabled with `?assistant=off`), computes the
  `x-amz-content-sha256` body hash via `crypto.subtle` (same `sha256Hex` the
  repo's `quiz.html` already uses), rolling 6-turn history in `sessionStorage`
  under key `agc-assistant-history` (repo-scoped, parallels quiz.html's keys),
  XSS-safe markdown renderer (escape-first), graceful non-200/timeout fallback,
  and a Sources line from `data.sources[].label`.

Font Awesome is already loaded in this repo's `<head>`, so the widget icons
(`fa-comments`, `fa-robot`, `fa-trash-can`, `fa-xmark`, `fa-paper-plane`) work
without new assets.

### 3.10 `slides/serve_with_judge.py` (EDIT)

Extend the local dev proxy to also proxy `/assistant` (today it proxies only
`/judge`). Changes:

- Add `ASSISTANT_UPSTREAM` env (default
  `https://agc.aws.yikyakyuk.com/assistant`, mirroring the existing
  `JUDGE_UPSTREAM` default host for this repo).
- In `do_POST`, route on `self.path.rstrip("/")`: `/judge` → `JUDGE_UPSTREAM`,
  `/assistant` → `ASSISTANT_UPSTREAM`, else 404. Both add the
  `x-amz-content-sha256` body hash exactly as the judge path does today.
- Update the banner prints to mention the `/assistant` proxy.

No other local-dev file changes; `quiz.html`, `quiz/`, `deck.html`, `doc.html`
are untouched.

---

## 4. Wiring `AssistantStack` into the root (parallel to `JudgeStack`)

In `agc-slides-root.yaml`, `AssistantStack` is a nested `AWS::CloudFormation::Stack`
sitting beside `JudgeStack`, using the identical S3-URL nesting idiom
(`TemplateURL: !Sub ['https://${Bucket}.s3.${BucketRegion}.amazonaws.com/${Prefix}/assistant.yaml', Bucket: !GetAtt BucketNameParam.Value]`).

Parameter threading:

| AssistantStack param | Root source | Notes |
|---|---|---|
| `ProjectPrefix` | `!Ref ProjectPrefix` | `agc` |
| `AssistantModelId` | `!Ref AssistantModelId` | Haiku 4.5 default |
| `OriginSecret` | `!Ref OriginSecret` | **same** shared secret as JudgeStack |
| `ReservedConcurrency` | `!Ref ReservedConcurrency` | default 3 |
| `CloudFrontDistributionArn` | `!Ref JudgeDistributionArn` | **reuse** the self-referential dist ARN; one distribution fronts both Function URLs, so one ARN scopes both Lambda policies |
| `KnowledgeBaseId` | `!Ref KnowledgeBaseId` | empty ⇒ 503 until gated-in |
| `KnowledgeBaseArn` | `!Ref KnowledgeBaseArn` | empty ⇒ no retrieve grant |
| `EmbeddingModelId` | `!Ref EmbeddingModelId` | cohere 1024-dim |

`CloudFrontDistributionStack` gains one new param,
`AssistantFunctionUrlDomain: !GetAtt AssistantStack.Outputs.AssistantFunctionUrlDomain`.
Because the CloudFront stack now `!GetAtt`s outputs from BOTH `JudgeStack` and
`AssistantStack`, CloudFormation implicitly orders both before the CloudFront
stack — no explicit `DependsOn` needed.

Self-referential distribution ARN flow (unchanged idiom):
1. First create: `JudgeDistributionArn=""`. Both judge and assistant Lambda
   permissions fall back to `SourceAccount`. CloudFront is created.
2. Deploy script reads the stack's `CloudFrontDistributionId` output, builds
   `arn:aws:cloudfront::<acct>:distribution/<id>`, and re-passes it as
   `JudgeDistributionArn` on the next deploy. Both Lambda policies tighten to
   `aws:SourceArn` scoped to that exact distribution.

The single `OriginSecret` (SSM SecureString `${PARAMETER_PREFIX}/agc/JudgeOriginSecret`,
already used by the judge) is reused verbatim for the assistant origin header
and the assistant Lambda's `ORIGIN_SECRET` env — both backends verify the same
value. No new SSM secret is introduced.

---

## 5. `agc-slides-deploy.sh` changes

Keep the existing judge + content flow fully intact. Add a KB sibling-stack
path and an assistant publish parallel to the judge. The target deploy script is
currently a single linear flow (not sub-command dispatched like the reference).
**Chosen approach:** add an optional first-arg sub-command for the KB
(`./agc-slides-deploy.sh kb`) while keeping the default (no-arg) flow deploying
the root + publishing content, and have the default flow **re-derive** the KB
wiring from the KB stack + sentinel on every run. This matches the reference's
"always re-resolve KB params" behavior while preserving the target's existing
single-command ergonomics. Rationale: CloudFormation resets any
NoEcho/defaulted param not passed back to its default, so the default deploy
MUST re-derive and re-pass the KB params or a routine deploy would silently
un-wire a live KB.

New config block (near the existing `ORIGIN_SECRET_SSM`):

```bash
ASSISTANT_SRC_DIR="$SCRIPT_DIR/assistant"
ASSISTANT_MODEL_ID="${ASSISTANT_MODEL_ID:-global.anthropic.claude-haiku-4-5-20251001-v1:0}"
KB_STACK_NAME="${KB_STACK_NAME:-agc-slides-kb}"
KB_TEMPLATE="$SCRIPT_DIR/kb/kb.yaml"
KB_CORPUS_BUILDER="$SCRIPT_DIR/kb/build_corpus.sh"
KB_STAGING_DIR="$SCRIPT_DIR/kb/.staging"
KB_INGEST_SSM="${KB_INGEST_SSM:-/agc/kb-ingestion-status}"
EMBEDDING_MODEL_ID="${EMBEDDING_MODEL_ID:-cohere.embed-english-v3}"
ASSISTANT_TEMPLATE="$SCRIPT_DIR/agc-slides-assistant.yaml"
```

### 5.1 `deploy_kb` path (sibling stack `agc-slides-kb`)

Triggered by `./agc-slides-deploy.sh kb`. Ported from the reference
`deploy_kb_stack`, adapted to the target's `set -euo pipefail` style (the target
script has no `trap cleanup_on_error ERR`, so use `|| rc=$?` captures where the
reference relied on the trap):

1. `aws cloudformation deploy` the KB stack with `--no-fail-on-empty-changeset`,
   `ProjectPrefix=agc`, `EmbeddingModelId=$EMBEDDING_MODEL_ID`,
   `--capabilities CAPABILITY_NAMED_IAM`. Capture rc via `|| rc=$?` so an empty
   changeset is not fatal.
2. Read outputs `DataSourceBucketName`, `KnowledgeBaseId`, `DataSourceId`
   (fail if any empty).
3. `bash "$KB_CORPUS_BUILDER" "$KB_STAGING_DIR"` then
   `aws s3 sync "$KB_STAGING_DIR" "s3://$DS_BUCKET/" --delete`.
4. `aws bedrock-agent start-ingestion-job` with up to 5 retries, 15s apart (the
   KB can be briefly not-queryable right after CREATE_COMPLETE).
5. Poll `get-ingestion-job` to `COMPLETE` (set-e-safe loop; terminal
   `FAILED`/`STOPPED`, 5 consecutive unreadable polls, or ~1200s timeout are
   fatal; a lone transient CLI non-zero is absorbed). On `COMPLETE`, write the
   sentinel `aws ssm put-parameter --name "$KB_INGEST_SSM" --type String
   --overwrite --value "COMPLETE:${KB_ID}"`. On `FAILED`/`STOPPED`, write
   `"${status}:${KB_ID}"` and surface `failureReasons[]`.

### 5.2 KB id/arn re-derivation with sentinel gating (default flow)

In the default (root-deploy) flow, before building `PARAM_OVERRIDES`:

```bash
kb_outputs=$(aws cloudformation describe-stacks --stack-name "$KB_STACK_NAME" \
  --region "$REGION" --query 'Stacks[0].Outputs' --output json 2>/dev/null || echo "[]")
KB_ID_MAIN=$(echo "$kb_outputs"  | jq -r '[.[]?|select(.OutputKey=="KnowledgeBaseId").OutputValue][0] // ""')
KB_ARN_MAIN=$(echo "$kb_outputs" | jq -r '[.[]?|select(.OutputKey=="KnowledgeBaseArn").OutputValue][0] // ""')
KB_INGEST=$(aws ssm get-parameter --name "$KB_INGEST_SSM" --region "$REGION" \
  --query 'Parameter.Value' --output text 2>/dev/null || echo "")

KB_ID_PARAM=""; KB_ARN_PARAM=""
if [[ -n "$KB_ID_MAIN" && -n "$KB_ARN_MAIN" ]]; then
  if [[ "$KB_INGEST" == "COMPLETE:${KB_ID_MAIN}" ]]; then
    KB_ID_PARAM="$KB_ID_MAIN"; KB_ARN_PARAM="$KB_ARN_MAIN"
  else
    log "KB present but ingestion not COMPLETE (status='$KB_INGEST'); assistant will render 503 until ingestion completes."
  fi
elif [[ ( -n "$KB_ID_MAIN" && -z "$KB_ARN_MAIN" ) || ( -z "$KB_ID_MAIN" && -n "$KB_ARN_MAIN" ) ]]; then
  err "KB stack is partial (id='$KB_ID_MAIN' arn='$KB_ARN_MAIN'); refusing to half-wire."; exit 1
fi
```

These are **always** resolved (even when the KB stack is absent — then both stay
empty, and the assistant renders 503, which is the correct "not configured"
state). The empty-when-not-COMPLETE gating is what prevents wiring a KB whose
ingestion failed or is mid-flight.

### 5.3 New `PARAM_OVERRIDES` entries

Append to the existing array (judge entries unchanged):

```bash
PARAM_OVERRIDES+=(
  "AssistantModelId=${ASSISTANT_MODEL_ID}"
  "ReservedConcurrency=3"
  "KnowledgeBaseId=${KB_ID_PARAM}"
  "KnowledgeBaseArn=${KB_ARN_PARAM}"
  "EmbeddingModelId=${EMBEDDING_MODEL_ID}"
)
```

### 5.4 Upload the assistant template + `publish_assistant_code`

- In the template-upload block, add
  `aws s3 cp "$ASSISTANT_TEMPLATE" "s3://${BUCKET_NAME}/${PREFIX}/assistant.yaml"`
  (parallel to the judge/cloudfront/s3 copies).
- Add the assistant template to the preflight existence loop.
- After the content publish, add `publish_assistant_code` — a function parallel
  to the existing judge publish: read `AssistantFunctionName` output; if
  resolvable, zip `deploy/assistant/handler.py` at archive root,
  `update-function-code --publish`, `wait function-updated`. Guard on a
  resolvable name so a not-yet-created output skips non-fatally. Skipped in
  `--content-only` mode (same as the judge publish).

The judge publish, content sync, invalidation, dry-run, and `--content-only`
paths are unchanged.

Deploy order for a full first-time bring-up:
`./agc-slides-deploy.sh kb` (creates KB, ingests, sets sentinel) → then
`./agc-slides-deploy.sh` (deploys root with KB wired, publishes both Lambdas +
content). A second `./agc-slides-deploy.sh` run tightens the distribution ARN on
both Lambda policies.

---

## 6. DECISION — KB-grounding the judge too: **SKIP**

**Decision: do NOT upgrade the target judge in this port.** Leave
`deploy/judge/handler.py`, `deploy/agc-slides-judge.yaml`, and the root's
`JudgeStack` wiring exactly as they are (older, non-KB judge).

**Reasoning (risk vs scope):**

- The required deliverable is the **assistant + KB**. Judge KB-grounding is an
  explicit nice-to-have.
- The target judge is a **different, older** handler than the reference's newer
  KB-grounded judge. The reference judge also carries a substantial new
  no-leak guard subsystem (`_leak_guard`, n-gram/overlap thresholds,
  `eval_judge.py` as the shared oracle). Porting KB-grounding faithfully would
  mean either (a) importing that whole guard apparatus, expanding scope far
  beyond this task, or (b) grafting only the fail-open retrieval onto the older
  judge, producing a hybrid that matches neither repo and is hard to reason
  about. Both options add risk to a currently-working grader.
- The judge is on the **critical path** of the knowledge-check UX. The assistant
  is additive and fails soft (non-200 ⇒ friendly fallback), so shipping it
  carries low blast radius. Changing the judge risks regressing live grading for
  a benefit (source citations on explanations) that is not required.
- The KB stack, params, and gating this design builds are **judge-agnostic**.
  If judge KB-grounding is wanted later, it is a clean follow-up: thread the
  same `KnowledgeBaseId/Arn/EmbeddingModelId` into `JudgeStack` (the root already
  resolves them) and port the newer judge handler + its guard tests as a
  dedicated task. Nothing in this design blocks that.

Net: scope stays on the required assistant + KB; the working judge is left
untouched; the follow-up path is preserved.

---

## Error handling (concrete, per operation)

- **Bad JSON body** (`json.loads` raises): 400 `{"error":"invalid JSON body"}`.
  Not logged (expected client error). Recoverable (client fixes payload).
- **Missing/empty `message`** (after trim): 400 `{"error":"missing message"}`.
  Checked before KB config and retrieval, so order is deterministic. Not logged.
- **Wrong/absent `x-origin-secret`** when `ORIGIN_SECRET` set: 403
  `{"error":"forbidden"}`. Fatal for that request; not logged with the value.
  This is defense-in-depth behind CloudFront.
- **`KNOWLEDGE_BASE_ID` empty**: 503 `{"error":"assistant not configured"}`.
  Expected pre-KB / mid-ingestion state. Front-end shows the soft-failure
  message. Recoverable once the deploy script wires the KB.
- **Quiz paste detected**: 200 refusal, `sources: []`, `converse` NOT called.
  This is a success path (deliberate refusal), not an error.
- **KB `retrieve` raises** (throttle, perms, transient): **502**
  `{"error":"assistant unavailable","detail":...}` (fail-closed, unlike the
  judge). `detail` is truncated to 200 chars. Front-end soft-fails. Recoverable.
- **`converse` raises / returns empty**: 502 `{"error":"assistant unavailable"}`
  / `{"error":"assistant returned empty answer"}`. Recoverable; front-end soft-fails.
- **CFN KB stack partial** (id xor arn): deploy script **exits 1** (fatal,
  refuses to half-wire). Logged.
- **Ingestion `FAILED`/`STOPPED`**: deploy script exits 1, writes a non-COMPLETE
  sentinel, prints `failureReasons[]`. The most likely cause (embedding
  dimension mismatch) is surfaced there. Fatal for the KB deploy; the root
  deploy then renders the assistant as 503 (not wired) rather than broken.
- **`publish_assistant_code` with unresolved function name**: skip non-fatally
  (return 0) so `set -e` does not abort. A resolvable-name-but-failed
  `update-function-code` is the only fatal publish path.

## Input validation (per external input)

- `message`: required, string, capped at `MAX_INPUT=4000` chars then trimmed;
  empty ⇒ 400.
- `history`: optional; must be a list, else ignored (`[]`). Each entry must be a
  `{role, content}` dict with non-empty string `content`; malformed entries
  dropped; kept to the last 6; each content truncated to 1000 chars; role
  coerced to `assistant`|`user`.
- `x-origin-secret` header: required only when `ORIGIN_SECRET` env is set;
  case-insensitive header-name match; must equal the configured value.
- KB result URIs (`location.s3Location.uri`): untrusted; `_source_label` is
  defensive (non-string/empty/unparseable ⇒ `None` ⇒ dropped). Labels derive
  from the **key only**, never chunk content, so a source line cannot leak
  retrieved text.
- `build_corpus.sh` inputs (filesystem): positive allow-list at copy time +
  post-stage gates; any file failing the allow-list or any
  `*_KnowledgeCheck.md`/`*.md.js` under staging ⇒ exit 1 before sync.

## Invariant ownership

- **"No knowledge-check content in the KB"** — owned by `build_corpus.sh` (copy
  allow-list + hard find gate). The handler is a second line of defense:
  `_source_label` would surface a KnowledgeCheck basename only if one were
  wrongly staged, but it never is. Enforced at build time because that is the
  only layer that sees the full corpus.
- **"Assistant never answers quiz questions"** — owned by the handler
  (`_is_quiz_attempt` guard, runs before retrieval/converse). Pure function;
  conservative (over-refuses rather than leaks).
- **"Assistant answers only from KB context"** — owned jointly by the handler
  (injects only retrieved context into `system`, 503 when no KB) and the system
  prompt (instructs the model to answer only from context). The handler owns the
  hard guarantee (no KB ⇒ no answer); the prompt owns answer quality.
- **"KB wired only when ingestion COMPLETE"** — owned by the deploy script
  (sentinel gating). CloudFormation cannot express "ingestion done", so the
  bash layer owns it.
- **S3-URI ↔ label contract** — owned jointly by `build_corpus.sh` (writes the
  keys) and `handler._source_label` (parses them); the §3.2 unit test is the
  executable enforcement that the two agree.

## Testability

- **Unit (no AWS):** `deploy/assistant/test_handler.py` — all status codes,
  quiz-refusal-no-converse, source mapping for THIS repo's keys, history
  parsing. Bedrock + KB mocked. This also unit-tests the §2 contract.
- **Unit (no AWS):** `build_corpus.sh` can be run standalone against the real
  `md/` + `slides/docs/lab.md` tree; assert it stages exactly 6 modules + 1 doc,
  stages zero KnowledgeCheck/`.md.js`, and that each staged module basename
  matches `_MODULE_KEY_RE` (a tiny python one-liner can cross-check the regex
  against the staged names — recommended smoke check in CI).
- **Integration (AWS):** KB stack create + ingestion to COMPLETE (dimension
  coupling verified here); CloudFront `/assistant*` → Function URL via OAC with
  the x-origin-secret header; end-to-end a grounded question returns an answer +
  sources. These require a deployed stack and cannot be unit-tested.
- **Local manual:** `serve_with_judge.py` proxying `/assistant` against a
  deployed distribution exercises the full front-end widget without AWS creds.

The design is testable: the two risk-concentrating couplings (URI↔label, corpus
provenance) both have no-AWS executable checks, and the AWS-only paths are
isolated to the KB/CFN/OAC layers that inherently need integration testing.
