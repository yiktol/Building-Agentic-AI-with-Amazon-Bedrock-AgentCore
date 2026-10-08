# Design Review — Port the KB-grounded Course Assistant into `agc-slides`

Reviewed document: `.agents/tasks/port-course-assistant-kb/design.md`
Review performed fresh against the actual source in both the target repo
(`Building-Agentic-AI-with-Amazon-Bedrock-AgentCore`) and the reference repo
(`temp/agentic-ai-foundations`).

## Verdict summary

The design is strong, concrete, and overwhelmingly backed by the real source.
All five requested focus areas (a–e) hold up under verification. The findings
below are minor: two NITs on internal wording/consistency and a couple of
NITs on small template-text staleness. **No HIGH or MEDIUM findings.** Verdict:
**APPROVED**.

---

## Findings

1. **NIT — Fallback-regex wording differs from the "copied verbatim" claim (§1.4).**
   §1.4 specifies the module-name fallback substitution as
   `re.sub(r"[_-]+", " ", group2)`, but the reference handler
   (`temp/.../deploy/assistant/handler.py`) uses `re.sub(r"_+", " ", m.group(2))`.
   The design elsewhere says the citation helpers are "copied verbatim," so the
   changed character class is an intentional-but-undeclared deviation. It is
   harmless (the fallback only fires when a module number is absent from
   `MODULE_TITLES`, which never happens for modules 1–6, so the map always
   wins), but the "verbatim" framing is slightly inaccurate.
   CONCRETE FIX: state explicitly that `_source_label`'s fallback `re.sub` is
   changed from `_+` to `[-_]+` to soften the camelCase/hyphen target stems, and
   that this path is dead for the 1–6 corpus — i.e. list it as a deliberate edit
   rather than under "copied verbatim."

2. **NIT — build_corpus allow-list `M0[1-9]` is narrower than the glob/regex (§3.5).**
   §1.4's `_MODULE_KEY_RE` uses `M0?(\d+)` and §3.5's copy glob is
   `md/MLAGAC-*-EN-M0*-*_InstructorDeck.md` (both accept two-digit module
   numbers), but the copy-time and post-stage allow-list patterns are
   `MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md`, which only matches single-digit
   `M01`–`M09`. §3.5 gate 4 explicitly motivates the floor with "a future M07
   deck," so M07–M09 are covered, but a future `M10+` deck would pass the glob
   and regex yet be rejected by the allow-list. This is an internal
   inconsistency about how far "future growth" extends.
   CONCRETE FIX: either (a) accept the single-digit ceiling and state it
   ("corpus supports M01–M09; a 10th module needs an allow-list bump"), or
   (b) widen the allow-list to `M0?[0-9]+` / `M[0-9][0-9]?` to match the glob and
   regex. Pick one and make the three patterns agree.

3. **NIT — "byte-identical BedrockInvoke policy" is not literally byte-identical (§3.3).**
   §3.3 says the assistant's base `BedrockInvoke` policy "is byte-identical to
   the judge's and the reference assistant's." Verified against
   `deploy/agc-slides-judge.yaml` and the reference `deploy/assistant.yaml`: the
   policy bodies match in structure and ARNs, but the inference-profile ARN line
   interpolates a different parameter name — the judge uses `${JudgeModelId}`
   and the assistant uses `${AssistantModelId}`. So the rendered policy is
   equivalent, but the template text is not byte-identical.
   CONCRETE FIX: reword to "structurally identical to the judge's, with
   `${JudgeModelId}` replaced by `${AssistantModelId}`" to avoid a reviewer/coder
   expecting a literal copy-paste.

4. **NIT — Reused `OriginSecret` parameter description will be stale (§3.6, §4).**
   The design reuses the single existing `OriginSecret` for the assistant origin
   header and the assistant Lambda env. In the target root/judge/cloudfront
   templates the `OriginSecret` parameter `Description` says it is sent "toward
   the judge Lambda." After the port, that secret also fronts the assistant, so
   the description becomes misleading. This is purely cosmetic (no behavioral
   impact) and the design does not call it out.
   CONCRETE FIX: note in §3.6/§4 that the `OriginSecret` parameter descriptions
   in the root and cloudfront templates should be updated to mention both the
   judge and assistant origins, so the templates stay self-documenting.

---

## Verified Assumptions

Each item below was checked against the actual files, not taken on the design's
word.

- **(a) MODULE_TITLES / _DOC_LABELS derived from the TARGET repo (6-module course).**
  VERIFIED. `md/` contains exactly the 13 files listed in §1.1 (6
  `..._InstructorDeck.md`, 6 `..._KnowledgeCheck.md`, 1
  `...-Lab-EnhanceAndScaleAgents.md`). The §1.2 `MODULE_TITLES` map (1–6) matches
  `slides/index.html`'s `modules[]` titles verbatim ("Foundations of Agentic AI
  Patterns", "AgentCore Runtime and Framework Integration", "Security and
  Identity Management", "Tool Integration and AgentCore Gateway", "Agentic Memory
  Implementation", "Production Monitoring and Observability"). The reference's
  8-module map (0–7, "From LLMs to Agents", etc.) and reference `_DOC_LABELS`
  (`lab1.md`/`lab2.md`/`qs-student-guide.md`) are correctly NOT carried over;
  §1.3 reduces `_DOC_LABELS` to the single `lab.md` entry.

- **(b) Corpus staging layout AGREES with the handler's S3-URI parser.**
  VERIFIED. The §1.4 regex `^MLAGAC-\d+-EN-M0?(\d+)-(.+?)_InstructorDeck\.md$`
  was executed against the real module basenames: `M01`→(1,'Foundations'),
  `M03`→(3,'SecurityAndIdentity'), `M06`→(6,'DeploymentObservablity'); the Lab
  basename does NOT match (falls through to `_DOC_LABELS["lab.md"]`), and a
  `_KnowledgeCheck.md` basename does NOT match. The §2 staging layout
  (`modules/<original-basename>`, `docs/lab.md`) feeds `_source_label`'s
  basename-only parse (`key.rsplit("/", 1)[-1]`, reference confirmed), so the
  §2 "Agreement check" examples resolve exactly as written. The two sides are
  explicitly stated to agree and do.

- **(c) AssistantStack wiring parallel to JudgeStack.**
  VERIFIED against `deploy/agc-slides-root.yaml`. `JudgeStack` nests
  `judge.yaml` by S3 URL with `BucketNameParam` and passes `OriginSecret` +
  `CloudFrontDistributionArn: !Ref JudgeDistributionArn`. §4's table reuses the
  same `OriginSecret` and the same `JudgeDistributionArn` self-ref for the
  assistant, threads `KnowledgeBaseId/Arn/EmbeddingModelId`, adds
  `AssistantFunctionUrlDomain` to the CloudFront stack params, and relies on the
  implicit `!GetAtt` ordering (consistent with how `JudgeFunctionUrlDomain` is
  already wired). The reference `deploy/assistant.yaml` confirms the ported
  template's params, `HasDistributionArn`/`HasKnowledgeBase` conditions,
  conditional `AssistantKbPolicy`, two `AWS::Lambda::Permission` resources, the
  BUFFERED IAM Function URL, and the `AssistantFunctionUrlDomain` output
  (`!Select [2, !Split ["/", ...]]`).

- **(d) deploy.sh KB sibling-stack + ingestion sentinel + id/arn re-derivation gating.**
  VERIFIED against the reference `temp/.../deploy/deploy.sh` (which DOES contain
  `deploy_kb_stack`, `KB_INGEST_SSM`, `bedrock-agent start-ingestion-job`/
  `get-ingestion-job`, the 5×15s start retry, the 1200s poll, the
  `COMPLETE:${KB_ID}` sentinel write, the `${status}:${KB_ID}` failure sentinel,
  and `failureReasons[]` surfacing). §5.1 and the §5.2 re-derivation snippet
  mirror the reference's logic closely, correctly adapted to the target's
  `set -euo pipefail` (no ERR trap) with `|| rc=$?` captures. The target's
  existing single-command `agc-slides-deploy.sh` was read; §5's plan to add a
  `kb` sub-command while keeping the default no-arg flow is consistent with the
  existing structure (same `ORIGIN_SECRET_SSM`, same self-ref `JUDGE_DIST_ARN`
  derivation, same `--content-only`/`--dry-run` paths, same `get_output`
  publish pattern). The partial-KB (id XOR arn) fatal exit and the
  not-COMPLETE-⇒-empty gating match the reference.

- **(e) Judge KB-grounding decision explicitly made with reasoning.**
  VERIFIED. §6 explicitly decides **SKIP**, with four concrete reasons (required
  deliverable is assistant+KB; target judge is an older, different handler and
  the reference's KB judge drags in a `_leak_guard`/`eval_judge.py` subsystem;
  judge is on the critical grading path with higher blast radius; KB stack/params
  are judge-agnostic so it is a clean follow-up). This is internally consistent
  with §3.7 (JudgeStack params left unchanged) and §5.3 (KB params flow only to
  the assistant). The target `deploy/judge/handler.py` + `agc-slides-judge.yaml`
  are indeed the older non-KB judge, so the decision is grounded in the real
  code.

- **Front-end dependencies (§3.9/§3.10).** VERIFIED. `slides/quiz.html` contains
  a `sha256Hex` helper; all 11 CSS vars the widget uses
  (`--navy --blue --orange --card --line --ink --muted --bg --radius --shadow
  --shadow-hover`) exist in `index.html`'s `:root`; `--orange` is literally
  `#1DB893` (the design's teal-green note is exact); Font Awesome is loaded in
  `<head>`; `serve_with_judge.py` exists, proxies `/judge`, adds
  `x-amz-content-sha256`, and defaults `JUDGE_UPSTREAM` to the
  `agc.aws.yikyakyuk.com` host the design cites for `ASSISTANT_UPSTREAM`.

- **Corpus noise filter re-derivation (§3.5).** VERIFIED. Real decks contain
  image lines of the form `![M01 slide 1](images/M01/slide-01.png)` (start with
  `![`, NOT the reference's `![Slide `), confirming the reference filter would
  miss them and the design's `line.lstrip().startswith("![")` is the correct
  re-derivation. Narration renders as a `**Narration:**` header + blockquote
  with no standalone audio-link line, confirming the design's decision to drop
  the reference's audio filter. The module glob `md/MLAGAC-*-EN-M0*-*_InstructorDeck.md`
  matches exactly the 6 decks and excludes the `_KnowledgeCheck.md` files.

- **KB template details (§3.4).** VERIFIED against reference `deploy/kb/kb.yaml`:
  the four `NonFilterableMetadataKeys` (`AMAZON_BEDROCK_TEXT`,
  `AMAZON_BEDROCK_METADATA`, `x-amz-bedrock-kb-source-file-modality`,
  `x-amz-bedrock-kb-data-source-id`), `Dimension: 1024` + `cohere.embed-english-v3`
  coupling, FIXED_SIZE 512 tokens / 20% overlap, three scoped KB-role policies,
  the three SSM discovery params, and the `knowledge-base/${KnowledgeBase}` ARN
  output shape all match.

## Unverified / Wrong Assumptions

- **No wrong assumptions found.** Every substantive claim in the design that was
  checkable against source checked out. One initial grep for the reference's KB
  logic returned no matches due to a path-glob quirk in the search tool; a
  direct read of `temp/.../deploy/deploy.sh` confirmed `deploy_kb_stack`, the
  sentinel, and the re-derivation gating all exist exactly as the design
  describes — so the design's §5 "ported from the reference" basis is sound, not
  invented.

- **Not verifiable without AWS (acknowledged by the design, not a gap):** actual
  Bedrock KB create + ingestion to `COMPLETE`, the embedding-dimension coupling
  at ingestion time, CloudFront `/assistant*` → Function URL via OAC with the
  `x-origin-secret` header, and end-to-end grounded Q&A. §Testability correctly
  isolates these to integration testing and does not assert them as unit-checked.
