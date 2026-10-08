# Quiz Expansion Verification Note

Scope: Expanded every module quiz (`slides/quiz/m1`..`m6`, both `.json` and `.js`)
from 2 to 5 questions by adding `mNq3`, `mNq4`, `mNq5`. Existing `mNq1`/`mNq2`
and the `module`/`title`/`subtitle`/`intro` fields were kept verbatim. New
questions are grounded in the module instructor decks per
`.agents/tasks/quiz-plan.md`.

Generation method: a throwaway Python generator read each existing `mN.json`,
appended the three new question objects, re-wrote the JSON 2-space
pretty-printed (trailing newline), and regenerated `mN.js` as
`window.QUIZ_DATA = window.QUIZ_DATA || {};` + `window.QUIZ_DATA["N"] = <compact>;`
using `json.dumps(obj)` with default separators (byte-matching the existing
files' serialization). The generator was deleted after verification.

## Checks run (all PASS)

1. JSON validity — for each module:
   `python3 -c "import json,sys; json.load(open(sys.argv[1]))" slides/quiz/mN.json`
   -> all 6 valid.

2. Schema / per-question invariants (all 6 modules x 5 questions):
   - questions length == 5; ids == `mNq1..mNq5`.
   - exactly 4 options; new q3-q5 options each end with a period.
     (Pre-existing q1/q2 period quirks in m2-m6 are out of scope per the plan,
     so the period assertion was applied to the new questions only.)
   - `0 <= answerIndex <= 3`; `answer == options[answerIndex]`;
     `answerLetter == "ABCD"[answerIndex]`; exact 7-key key set.
   - new-question correct positions vary per module and match the plan:
     m1=C,A,D  m2=D,B,A  m3=C,B,A  m4=C,D,B  m5=C,A,D  m6=C,A,B.

3. `.js` == `.json` parity — regex-extracted the object from each `mN.js`,
   `json.loads` it, deep-compared to `json.load(mN.json)` -> all 6 equal.

4. First-two-questions + header unchanged vs `git HEAD`:
   compared `git show HEAD:slides/quiz/mN.json` -> `module/title/subtitle/intro`
   and `questions[:2]` identical for all 6. Also confirmed each regenerated
   `mN.js` shares a byte-identical prefix with HEAD up to `HEAD_len - 4`
   (the old `]};\n` array close), i.e. q1/q2 serialization is unchanged.

5. `node --check slides/quiz/mN.js` -> OK for all 6 (node available).

Grounding: every new question/answer/explanation traces to the cited slides in
the module instructor decks (`md/MLAGAC-10-EN-M0N-*_InstructorDeck.md`); no
AgentCore features, API names, or limits were invented. Distractors are drawn
from real deck concepts used in a wrong role.
