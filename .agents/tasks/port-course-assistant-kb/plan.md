# Implementation Plan — Port the KB-grounded Course Assistant + Bedrock KB into `agc-slides`

Source of truth: `.agents/tasks/port-course-assistant-kb/design.md` (APPROVED,
review verdict in `design-review.json`). This plan sequences that design; it does
not re-decide architecture. Where the design review raised NITs, they are folded
into the relevant items (fallback regex `[_-]+`, M01–M09 allow-list ceiling,
"structurally identical" policy wording, OriginSecret description refresh).

Reference repo (copy-from): `temp/agentic-ai-foundations/`.
Target repo (edit): repository root `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/`.

## Grounded facts established during exploration (do not re-derive)

- Target `md/` holds exactly 6 `MLAGAC-10-EN-M0N-<Name>_InstructorDeck.md` decks
  (M01 Foundations, M02 Runtime, M03 SecurityAndIdentity, M04 ToolsAndGateway,
  M05 Memory, M06 DeploymentObservablity), 6 `..._KnowledgeCheck.md` files (one
  word, no underscore), and one `MLAGAC-10-EN-Lab-EnhanceAndScaleAgents.md`. The
  Lab basename does NOT match the `M0N` module glob, so the module loop never
  picks it up.
- Module deck noise lines are image embeds like `![M01 slide 1](images/M01/slide-01.png)`.
  Narration renders as a `**Narration:**` header followed by blockquotes — there
  is NO standalone audio-link line, so the reference's audio filter is dropped.
  The only filter: drop a line iff `line.lstrip().startswith("![")`.
- `slides/docs/lab.md` exists (plus a `lab.md.js` viewer wrapper that must NEVER
  be staged). `lab.md` is the staging source for `docs/lab.md`.
- Target `slides/index.html` already defines every CSS var the widget needs
  (`--navy #232F3E`, `--blue #007FAA`, `--orange #1DB893`, `--teal #005276`,
  `--ink`, `--muted`, `--line`, `--bg`, `--card`, `--radius`, `--shadow`,
  `--shadow-hover`), loads Font Awesome 6.4.0 in `<head>`, has `</style>` at the
  end of its style block and a single `</body>` near EOF. Module titles in
  `index.html` match the design's `MODULE_TITLES` 1:1.
- `slides/quiz.html` already defines `sha256Hex` + the `x-amz-content-sha256`
  POST pattern; the widget's `sha256Hex` is identical and self-contained.
- Target `deploy/` has NO `assistant/` or `kb/` dir yet; `judge/handler.py`
  exists. `agc-slides-judge.yaml` is the structural template for the assistant
  stack. `agc-slides-root.yaml` nests `ContentBucketStack`, `JudgeStack`,
  `CloudFrontDistributionStack` by S3 URL under short names (`s3.yaml`,
  `judge.yaml`, `cloudfront.yaml`). `agc-slides-deploy.sh` is a single linear
  flow (no sub-command dispatch) using `set -euo pipefail`, reusing an SSM
  SecureString `${PARAMETER_PREFIX}/agc/JudgeOriginSecret`.
- Tooling available for offline verification: `python3` (3.13), `cfn-lint`
  (1.56.0), `jq`, `zip`, `bash`. `yamllint` is NOT installed — use cfn-lint plus
  a `python3` PyYAML/ast well-formedness check instead.
- DESIGN DECISION §6: the judge is left UNTOUCHED (no KB-grounding). Plan item 9
  is therefore a no-op/verification-only item, not a code change.

## Offline verification toolkit (referenced by items below)

Because AWS deploys cannot run here, every item is verified offline:

- Unit tests: `cd deploy/assistant && ORIGIN_SECRET=testsecret python3 test_handler.py` → must print `ALL PASS`.
- Python syntax: `python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" <file.py>` for every edited/created `.py`.
- Shell syntax: `bash -n <script.sh>` for `build_corpus.sh` and `agc-slides-deploy.sh`.
- YAML/CFN: `cfn-lint <template.yaml>` (treat exit 4 = warnings-only as non-fatal; exit 0 ideal) AND `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <template.yaml>` for well-formedness. If PyYAML is unavailable, fall back to `python3 -c "import json; ..."` is not valid for YAML — instead rely on cfn-lint's parse plus `aws cloudformation validate-template --template-body` only if creds exist; otherwise cfn-lint parse is the gate.
- Corpus staging: run `build_corpus.sh` against a temp dir, assert the expected keys/counts, then remove the temp dir.

---

- [ ] 1. Create the assistant Lambda handler, ported from the reference with this repo's maps.
      Copy `temp/agentic-ai-foundations/deploy/assistant/handler.py` to the new file VERBATIM except:
      (a) replace `MODULE_TITLES` with `{1:"Foundations of Agentic AI Patterns", 2:"AgentCore Runtime and Framework Integration", 3:"Security and Identity Management", 4:"Tool Integration and AgentCore Gateway", 5:"Agentic Memory Implementation", 6:"Production Monitoring and Observability"}`;
      (b) replace `_DOC_LABELS` with `{"lab.md": "Hands-on Lab — Enhance and Scale Agents"}`;
      (c) replace `_MODULE_KEY_RE` with `re.compile(r"^MLAGAC-\d+-EN-M0?(\d+)-(.+?)_InstructorDeck\.md$", re.I)`;
      (d) in the `_source_label` fallback, change the title substitution to `re.sub(r"[-_]+", " ", m.group(2))` (deliberate deviation from the reference's `_+`; a dead path for modules 1–6 since the map always wins — this folds in design-review NIT §1.4);
      (e) in `ASSISTANT_SYSTEM`, change the course name to `"Building Agentic AI with Amazon Bedrock AgentCore"`.
      Keep `BEDROCK_REGION` default `ap-southeast-1`, the quiz-refusal guard (`_is_quiz_attempt`, `_QUIZ_REFUSAL`, `_QUIZ_*` regexes), all citation helpers (`_source_label`, `_map_sources`, `_SOURCES_CAP=3`), the lazy KB client, fail-closed retrieval (502), and the 503-when-no-KB behavior VERBATIM.
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/assistant/handler.py`
      Verify: `python3 -c "import ast; ast.parse(open('deploy/assistant/handler.py').read())"` succeeds (full behavioral verification is item 2's test run).

- [ ] 2. Create the assistant unit tests, adapted to this repo's S3-URI↔label contract.
      Copy `temp/agentic-ai-foundations/deploy/assistant/test_handler.py` and change ONLY the fixtures/expected labels to this repo's contract:
      in `test_grounded_answer`, use `s3://my-bucket/modules/MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md` and `s3://my-bucket/docs/lab.md`, expecting `sources == [{"label": "Module 3 — Security and Identity Management", "module": 3}, {"label": "Hands-on Lab — Enhance and Scale Agents", "module": None}]`;
      replace every other `s3://b/docs/lab1.md` (and any `lab2.md`/`qs-student-guide.md`) fixture with `s3://b/docs/lab.md`.
      Keep ALL status-code cases (200 grounded, 200 quiz-refusal-no-converse, 200 empty-retrieval redirect, 400 missing message, 400 bad JSON, 403 wrong secret, 502 converse raises, 502 retrieval raises, 503 not configured, history-included) unchanged in intent. This is the executable guard that item 1's maps and item 5's staging agree.
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/assistant/test_handler.py`
      Verify: `cd deploy/assistant && ORIGIN_SECRET=testsecret python3 test_handler.py` prints `ALL PASS`; also `python3 -c "import ast; ast.parse(open('deploy/assistant/test_handler.py').read())"` succeeds.

- [ ] 3. Create the assistant Lambda CloudFormation stack (`assistant.yaml`), agc-prefixed.
      Port `temp/agentic-ai-foundations/deploy/assistant.yaml`, aligning naming with `deploy/agc-slides-judge.yaml`:
      `ProjectPrefix` default `agc`; `AssistantFunction` FunctionName `!Sub "${ProjectPrefix}-course-assistant"`, role `!Sub "${ProjectPrefix}-course-assistant-role"`.
      Parameters: `AssistantModelId` (default `global.anthropic.claude-haiku-4-5-20251001-v1:0`), `OriginSecret` (NoEcho), `ReservedConcurrency` (default 3), `CloudFrontDistributionArn` (default ""), `KnowledgeBaseId` (default ""), `KnowledgeBaseArn` (default ""), `EmbeddingModelId` (default `cohere.embed-english-v3`).
      Conditions `HasDistributionArn`, `HasKnowledgeBase`.
      Base `BedrockInvoke` policy is structurally identical to the judge's with `${JudgeModelId}` replaced by `${AssistantModelId}` (design-review NIT §3.3).
      Separate `AssistantKbPolicy` (`Condition: HasKnowledgeBase`) granting `bedrock:Retrieve` on `!Ref KnowledgeBaseArn` + `bedrock:InvokeModel` on the embedding-model ARN, so the base role is identical when the KB is empty.
      Function URL `AuthType: AWS_IAM`, `InvokeMode: BUFFERED`, CORS `AllowMethods: ["POST"]`, `AllowHeaders: ["content-type","x-origin-secret"]`.
      Two `AWS::Lambda::Permission` resources (`lambda:InvokeFunctionUrl` + `lambda:InvokeFunction`) scoped by `aws:SourceArn` when the dist ARN is set else `SourceAccount`.
      Inline 503 `ZipFile` stub ("assistant code not yet published").
      Outputs: `AssistantFunctionName` (+Export `${AWS::StackName}-AssistantFunctionName`), `AssistantFunctionUrl`, `AssistantFunctionUrlDomain` = `!Select [2, !Split ["/", !GetAtt AssistantFunctionUrl.FunctionUrl]]` (+Export).
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/agc-slides-assistant.yaml`
      Verify: `cfn-lint deploy/agc-slides-assistant.yaml` (exit 0, or 4 warnings-only) and `python3 -c "import yaml; yaml.safe_load(open('deploy/agc-slides-assistant.yaml'))"` succeeds.

- [ ] 4. Create the Knowledge Base sibling stack (`kb/kb.yaml`), agc-prefixed.
      Port `temp/agentic-ai-foundations/deploy/kb/kb.yaml` with `ProjectPrefix` default `agc`:
      `DataSourceBucket` `!Sub "${ProjectPrefix}-kb-datasource-${AWS::AccountId}"`; S3 Vectors bucket `${ProjectPrefix}-kb-vectors-${AWS::AccountId}`, index `${ProjectPrefix}-kb-index`, `DataType: float32`, `Dimension: 1024`, `DistanceMetric: cosine`, `MetadataConfiguration.NonFilterableMetadataKeys` = the four Bedrock-managed keys VERBATIM (keep the coupling + 2048-byte comment).
      `KnowledgeBaseRole` `${ProjectPrefix}-kb-role` with the three scoped inline policies (foundation-model InvokeModel on `EmbeddingModelId`, S3 data-source Get/List, S3 Vectors Put/Get/Delete/Query/GetIndex).
      `KnowledgeBase` `${ProjectPrefix}-course-kb` (S3_VECTORS storage); `KnowledgeBaseDataSource` `${ProjectPrefix}-kb-datasource` with FIXED_SIZE chunking (MaxTokens 512, OverlapPercentage 20). Update the KB `Description` to name THIS course.
      SSM params `${ProjectPrefix}-kb-id`, `${ProjectPrefix}-kb-datasource-id`, `${ProjectPrefix}-kb-datasource-bucket`.
      Outputs: `KnowledgeBaseId`, `KnowledgeBaseArn` (`arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:knowledge-base/${KnowledgeBase}`), `DataSourceId`, `DataSourceBucketName`.
      Keep `EmbeddingModelId`↔`Dimension` coupling (both the cohere 1024-dim pairing).
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/kb/kb.yaml`
      Verify: `cfn-lint deploy/kb/kb.yaml` (exit 0 or 4) and `python3 -c "import yaml; yaml.safe_load(open('deploy/kb/kb.yaml'))"` succeeds.

- [ ] 5. Create `build_corpus.sh`, re-derived for THIS repo's filenames and noise.
      Port the reference `temp/agentic-ai-foundations/deploy/kb/build_corpus.sh` structure (shebang, `set -euo pipefail`, `REPO_ROOT` pinned from `${BASH_SOURCE[0]}/../..`, fresh `modules/` + `docs/` staging), but re-derive the corpus logic:
      Default staging dir `${1:-$REPO_ROOT/deploy/kb/.staging}`.
      MODULES: iterate `"$REPO_ROOT"/md/MLAGAC-*-EN-M0*-*_InstructorDeck.md`; `continue` on `*_KnowledgeCheck.md` (single word); positive allow-list `MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md` (document the M01–M09 ceiling explicitly per design-review NIT §3.5) rejecting anything else; copy each deck's basename into `modules/` through a `python3` filter that drops a line iff `line.lstrip().startswith("![")` and preserves every other line verbatim (NO emoji grep, NO audio filter — none matches these decks).
      DOCS: copy `"$REPO_ROOT"/slides/docs/lab.md` → `$STAGING_DIR/docs/lab.md` (error out if missing). Never glob `*.md.js`.
      POST-STAGE GATES (before returning): every `modules/*.md` basename matches `MLAGAC-*-EN-M0[1-9]-*_InstructorDeck.md`; every `docs/*` basename is exactly `lab.md`; hard gate `find "$STAGING_DIR" \( -name '*_KnowledgeCheck.md' -o -name '*.md.js' \)` is empty; count floor `[ "$total" -lt 7 ]` is fatal (6 decks + 1 doc). Report the staged tree.
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/kb/build_corpus.sh`
      Verify: `bash -n deploy/kb/build_corpus.sh`; then run it against a temp dir and assert the contract, then clean up:
      `TMP="$(mktemp -d)"; bash deploy/kb/build_corpus.sh "$TMP"; test "$(find "$TMP/modules" -name '*_InstructorDeck.md' | wc -l | tr -d ' ')" = "6"; test -f "$TMP/docs/lab.md"; test -z "$(find "$TMP" \( -name '*_KnowledgeCheck.md' -o -name '*.md.js' \))"; test "$(find "$TMP" -name '*.md' | wc -l | tr -d ' ')" -ge 7; python3 -c "import re,os,sys; rx=re.compile(r'^MLAGAC-\d+-EN-M0?(\d+)-(.+?)_InstructorDeck\.md$',re.I); [sys.exit('bad: '+b) for b in os.listdir(sys.argv[1]+'/modules') if not rx.match(b)]" "$TMP"; rm -rf "$TMP"` — all assertions pass (6 module decks staged, lab.md present, zero forbidden files, regex matches every staged module name).

- [ ] 6. Edit the CloudFront template to add the `/assistant*` behavior + assistant origin.
      In `deploy/agc-slides-cloudfront.yaml`, keep everything judge-related intact and ADD, parallel to the judge:
      a new parameter `AssistantFunctionUrlDomain` (String);
      a new origin `!Sub "${ProjectPrefix}-assistant"` with `DomainName: !Ref AssistantFunctionUrlDomain`, reusing the EXISTING `LambdaOriginAccessControl` (no second lambda OAC), `CustomOriginConfig` https-only / TLSv1.2 / 443, and `OriginCustomHeaders` `x-origin-secret: !Ref OriginSecret` — exact parallel to the `${ProjectPrefix}-judge` origin;
      a new cache behavior `PathPattern: /assistant*` → `TargetOriginId: !Sub "${ProjectPrefix}-assistant"`, `CachePolicyId: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad` (CachingDisabled), `OriginRequestPolicyId: b689b0a8-53d0-40ab-baf2-68738e2966ac` (AllViewerExceptHostHeader), `AllowedMethods: [GET,HEAD,OPTIONS,PUT,POST,PATCH,DELETE]`, `CachedMethods: [GET,HEAD]`, NO viewer-request FunctionAssociations — exact parallel to `/judge*`.
      Refresh the `OriginSecret` parameter `Description` to mention BOTH the judge and assistant origins (design-review NIT §3.6).
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/agc-slides-cloudfront.yaml`
      Verify: `cfn-lint deploy/agc-slides-cloudfront.yaml` (exit 0 or 4) and `python3 -c "import yaml; yaml.safe_load(open('deploy/agc-slides-cloudfront.yaml'))"` succeeds.

- [ ] 7. Edit the root template to nest `AssistantStack` and thread KB params through.
      In `deploy/agc-slides-root.yaml`:
      add parameters `AssistantModelId` (default `global.anthropic.claude-haiku-4-5-20251001-v1:0`), `ReservedConcurrency` (Number, default 3), `KnowledgeBaseId` (default ""), `KnowledgeBaseArn` (default ""), `EmbeddingModelId` (default `cohere.embed-english-v3`);
      refresh the `OriginSecret` parameter `Description` to mention both judge and assistant (design-review NIT §3.6);
      add a nested `AssistantStack` (`AWS::CloudFormation::Stack`) using the identical S3-URL nesting idiom with remote name `assistant.yaml`, parallel to `JudgeStack`, passing `ProjectPrefix: !Ref ProjectPrefix`, `AssistantModelId: !Ref AssistantModelId`, `OriginSecret: !Ref OriginSecret`, `ReservedConcurrency: !Ref ReservedConcurrency`, `CloudFrontDistributionArn: !Ref JudgeDistributionArn` (reuse the same self-ref ARN), `KnowledgeBaseId: !Ref KnowledgeBaseId`, `KnowledgeBaseArn: !Ref KnowledgeBaseArn`, `EmbeddingModelId: !Ref EmbeddingModelId`;
      add `AssistantFunctionUrlDomain: !GetAtt AssistantStack.Outputs.AssistantFunctionUrlDomain` to the `CloudFrontDistributionStack` Parameters;
      add outputs `AssistantFunctionName: !GetAtt AssistantStack.Outputs.AssistantFunctionName` and `AssistantFunctionUrl: !GetAtt AssistantStack.Outputs.AssistantFunctionUrl`.
      Leave `JudgeStack` Parameters UNCHANGED (design §6: judge KB-grounding is SKIPPED). The KB stack is a sibling deployed by the script; the root only receives resolved KB id/arn as params.
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/agc-slides-root.yaml`
      Verify: `cfn-lint deploy/agc-slides-root.yaml` (exit 0 or 4) and `python3 -c "import yaml; yaml.safe_load(open('deploy/agc-slides-root.yaml'))"` succeeds. (Note: cfn-lint may warn about the S3-URL nested TemplateURL as it does today for Judge/CloudFront stacks — treat the same way the existing stacks are treated.)

- [ ] 8. Edit the deploy script to add KB sibling-stack handling + assistant publish + KB wiring.
      In `deploy/agc-slides-deploy.sh`, keep the existing judge + content flow fully intact and ADD:
      (a) a config block near `ORIGIN_SECRET_SSM` defining `ASSISTANT_SRC_DIR="$SCRIPT_DIR/assistant"`, `ASSISTANT_MODEL_ID="${ASSISTANT_MODEL_ID:-global.anthropic.claude-haiku-4-5-20251001-v1:0}"`, `ASSISTANT_TEMPLATE="$SCRIPT_DIR/agc-slides-assistant.yaml"`, `KB_STACK_NAME="${KB_STACK_NAME:-agc-slides-kb}"`, `KB_TEMPLATE="$SCRIPT_DIR/kb/kb.yaml"`, `KB_CORPUS_BUILDER="$SCRIPT_DIR/kb/build_corpus.sh"`, `KB_STAGING_DIR="$SCRIPT_DIR/kb/.staging"`, `KB_INGEST_SSM="${KB_INGEST_SSM:-/agc/kb-ingestion-status}"`, `EMBEDDING_MODEL_ID="${EMBEDDING_MODEL_ID:-cohere.embed-english-v3}"`;
      (b) extend the arg parse so `kb` is accepted as an optional first sub-command (default no-arg flow unchanged; `--dry-run` / `--content-only` preserved);
      (c) a `deploy_kb()` function (ported from the reference `deploy_kb_stack`, adapted to `set -euo pipefail` with `|| rc=$?` captures since there is no ERR trap): `aws cloudformation deploy` the KB stack with `ProjectPrefix=agc EmbeddingModelId=$EMBEDDING_MODEL_ID --capabilities CAPABILITY_NAMED_IAM --no-fail-on-empty-changeset`; read `DataSourceBucketName`/`KnowledgeBaseId`/`DataSourceId` (fail if any empty); `bash "$KB_CORPUS_BUILDER" "$KB_STAGING_DIR"` then `aws s3 sync "$KB_STAGING_DIR" "s3://$DS_BUCKET/" --delete`; start-ingestion-job with up to 5 retries 15s apart; poll get-ingestion-job to COMPLETE (set-e-safe loop; terminal FAILED/STOPPED, 5 consecutive unreadable polls, or ~1200s timeout fatal); on COMPLETE write SSM sentinel `COMPLETE:${KB_ID}`, on FAILED/STOPPED write `${status}:${KB_ID}` and print `failureReasons[]`. When invoked as `./agc-slides-deploy.sh kb`, run `deploy_kb` and exit;
      (d) in the default flow, BEFORE building `PARAM_OVERRIDES`, re-derive KB wiring verbatim per design §5.2: read KB stack outputs `KnowledgeBaseId`/`KnowledgeBaseArn` (default "" when absent) and the SSM sentinel; set `KB_ID_PARAM`/`KB_ARN_PARAM` only when BOTH outputs present AND sentinel `== "COMPLETE:${KB_ID_MAIN}"`; `err`+`exit 1` on the partial (id-xor-arn) case; otherwise leave both empty (assistant renders 503);
      (e) append to `PARAM_OVERRIDES`: `"AssistantModelId=${ASSISTANT_MODEL_ID}"`, `"ReservedConcurrency=3"`, `"KnowledgeBaseId=${KB_ID_PARAM}"`, `"KnowledgeBaseArn=${KB_ARN_PARAM}"`, `"EmbeddingModelId=${EMBEDDING_MODEL_ID}"` (judge entries unchanged);
      (f) in the preflight existence loop and the template-upload block, add `ASSISTANT_TEMPLATE` and `aws s3 cp "$ASSISTANT_TEMPLATE" "s3://${BUCKET_NAME}/${PREFIX}/assistant.yaml"`;
      (g) add `publish_assistant_code` parallel to the existing judge publish (read `AssistantFunctionName` output; guard on a resolvable name → skip non-fatally; zip `deploy/assistant/handler.py` at archive root; `update-function-code --publish`; `wait function-updated`), and call it right after the judge publish in the default (non-`--content-only`) flow.
      Preserve the judge publish, content sync, invalidation, dry-run, and `--content-only` paths unchanged.
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/deploy/agc-slides-deploy.sh`
      Verify: `bash -n deploy/agc-slides-deploy.sh` succeeds (no syntax errors). (Full deploy requires AWS and is out of scope for offline verification.)

- [ ] 9. Confirm the judge is left untouched (design §6 DECISION = SKIP).
      Make NO changes to `deploy/judge/handler.py`, `deploy/agc-slides-judge.yaml`, or the root's `JudgeStack` wiring. This item is a guard, not an edit: KB-grounding the judge is explicitly out of scope for this port.
      Files: (none changed)
      Verify: `git status --porcelain deploy/judge/handler.py deploy/agc-slides-judge.yaml` shows no modification to these two files, and the `JudgeStack` block in `deploy/agc-slides-root.yaml` still passes only `ProjectPrefix`, `JudgeModelId`, `OriginSecret`, `CloudFrontDistributionArn`.

- [ ] 10. Add the course-assistant chat widget to the slides landing page.
      In `slides/index.html`, preserve ALL existing content and append the widget ported from `temp/agentic-ai-foundations/slides/index.html`:
      (a) insert the `.ca-*` CSS block (launcher, panel, head, msgs, bubble user/bot/err, srcs, typing, `@keyframes ca-blink`, input, mobile media query) immediately before the closing `</style>`. It uses only CSS vars already defined in this repo's `:root` (including `--teal` used by `.ca-srcs b`), so no new vars are needed;
      (b) insert the launcher button + `ca-panel` dialog markup immediately before `</body>`, with title text `Course Assistant` and subtitle `Amazon Bedrock AgentCore` (adapt the reference's `Agentic AI Foundations` subtitle); icons `fa-comments`, `fa-robot`, `fa-trash-can`, `fa-xmark`, `fa-paper-plane` (Font Awesome already loaded in `<head>`);
      (c) insert the IIFE `<script>` (also before `</body>`, after the markup): POST `{message, history}` to `/assistant` (overridable `?assistant=<url>`, disabled `?assistant=off|none`), `sha256Hex` body hash in the `x-amz-content-sha256` header, rolling 6-turn history in `sessionStorage` under key `agc-assistant-history` (repo-scoped — change the reference's `agentic-ai-assistant-history` to `agc-assistant-history`), escape-first XSS-safe `renderMarkdown`, 25s AbortController timeout, graceful non-200/timeout fallback bubble, and a `Sources:` line from `data.sources[].label`. Adapt the greeting/subtitle course-name strings to this course; keep everything else verbatim.
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/slides/index.html`
      Verify: `python3 -c "import html.parser,sys
class P(html.parser.HTMLParser):
    pass
P().feed(open('slides/index.html').read())"` parses without exception; grep confirms exactly one `</body>` and that `caLauncher`, `caPanel`, `agc-assistant-history`, and `/assistant` all appear. (Full UI behavior is validated manually via item 11's proxy against a deployed stack.)

- [ ] 11. Extend the local dev proxy to also proxy POST `/assistant`.
      In `slides/serve_with_judge.py`, parallel to the existing `/judge` handling:
      add `ASSISTANT_UPSTREAM = os.environ.get("ASSISTANT_UPSTREAM", "https://agc.aws.yikyakyuk.com/assistant")` next to the existing `UPSTREAM`/`JUDGE_UPSTREAM`;
      in `do_POST`, route on `self.path.rstrip("/")`: `/judge` → the judge upstream, `/assistant` → `ASSISTANT_UPSTREAM`, else `send_error(404)`; both paths read the body, compute `hashlib.sha256(body).hexdigest()`, and forward with headers `content-type: application/json` + `x-amz-content-sha256: <hash>` exactly as the judge path does today;
      update the startup banner prints to mention the `/assistant` proxy too.
      Leave `quiz.html`, `quiz/`, `deck.html`, `doc.html` untouched.
      Files: `/Users/erictole/demo/Building-Agentic-AI-with-Amazon-Bedrock-AgentCore/slides/serve_with_judge.py`
      Verify: `python3 -c "import ast; ast.parse(open('slides/serve_with_judge.py').read())"` succeeds; grep confirms `ASSISTANT_UPSTREAM` and an `/assistant` route branch are present.

---

## Final offline verification gate (run after all items)

Run the full offline suite and confirm each result:

1. `cd deploy/assistant && ORIGIN_SECRET=testsecret python3 test_handler.py` → `ALL PASS`.
2. `python3 -c "import ast; ast.parse(...)"` on `deploy/assistant/handler.py`, `deploy/assistant/test_handler.py`, `slides/serve_with_judge.py` → all succeed.
3. `bash -n deploy/kb/build_corpus.sh` and `bash -n deploy/agc-slides-deploy.sh` → no errors.
4. `cfn-lint` + `python3 ... yaml.safe_load` on `deploy/agc-slides-assistant.yaml`, `deploy/kb/kb.yaml`, `deploy/agc-slides-cloudfront.yaml`, `deploy/agc-slides-root.yaml` → parse clean (cfn-lint exit 0 or 4-warnings-only).
5. `build_corpus.sh` against a fresh temp dir → 6 module decks + `docs/lab.md`, zero `*_KnowledgeCheck.md`/`*.md.js`, `>= 7` `.md` files, every staged module basename matches `_MODULE_KEY_RE`; then remove the temp dir.
6. `slides/index.html` parses and contains exactly one `</body>`, the `.ca-*` widget, `agc-assistant-history`, and `/assistant`.

AWS-dependent integration (KB create + ingestion to COMPLETE, CloudFront
`/assistant*` → Function URL via OAC, end-to-end grounded answer) cannot be
verified offline and is validated only on a real deploy; note this in the final
report rather than attempting it here.

## Notes / assumptions

- `.staging` dirs produced by `build_corpus.sh` under `deploy/kb/.staging` are
  deploy-time artifacts; do not commit them. If a `.gitignore` exists, consider
  adding `deploy/kb/.staging/`; otherwise just ensure temp dirs are cleaned up
  after verification.
- The deploy script's full first-time bring-up order is `./agc-slides-deploy.sh kb`
  (creates KB, ingests, sets sentinel) → `./agc-slides-deploy.sh` (deploys root
  with KB wired, publishes both Lambdas + content); a second default run tightens
  the distribution ARN on both Lambda policies. This is documented for the
  operator; it is not part of offline verification.
