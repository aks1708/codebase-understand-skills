# Extraction map: report section → lesson module

## Contents
- Module-by-module extraction (frame, map, components, flow, dials, conventions, patterns, capstone, fixed panels)
- Mermaid → ASCII translation rules
- Worked micro-example (fictional payment service)

The report is the source of truth; the lesson is its workshop-shaped projection. This file is the row-by-row translation table plus extraction rules. Both report templates (A: architecture study, B: prior-art/inspiration) map into the same eight module beats of the lesson arc.

Work top-to-bottom in generation order: read the report once fully, build the teaching ledger, then extract per module.

## Module-by-module extraction

### Beat 0 — Frame + hook question

- **From:** A §1 "What it is" / B "The problem it really solves"; report title.
- **Extract:** one plain-language frame (report's own words, lightly compressed, 2–3 sentences); the learner lens — derived from the report per SKILL.md Step -1, applied silently. Do not recite the report's stamp (date @ commit).
- **Add:** the hook question — the hardest problem this system solves, phrased as a question. Derive it from the report's load-bearing decision (its §7 or tradeoffs row), never invent one. Pose it and do not answer it yet; the lesson arc resolves it.

### Beat 1 — The system map

- **From:** A §2 System map (+ §2b critical-path diagrams) / B "Architecture in one diagram".
- **Extract:** every component and edge; boundary labels [process]/[network]/[trust]; the Sources anchors.
- **Rebuild:** Mermaid `graph`/`flowchart` → ASCII layered diagram. Node labels keep the paired form "Role — `code/entity/`" (e.g. "Orchestrator — `api/workflows.py`"). Arrow labels carry the mechanism ("publishes events", never "→").
- **First interaction:** before explaining any component, ask a placement or ablation question on the freshly drawn map ("if we delete this box, what breaks?"). This is one of the lesson's easy warm-up questions — it should be answerable in one sentence from the map the learner is looking at, no mechanism memory required yet.
- **First sight of vocabulary:** as you draw, give every component-role word on the map (gateway, queue, cache, adapter — whatever appears) a one-line plain-words definition in passing. No word on the map is pre-understood (Level register).
- **If the report has an ASCII fallback instead of Mermaid:** rebuild from the ASCII — it encodes the same topology.

### Beat 2 — Component tour (role beats)

- **From:** A §3 Component inventory / B implied by its diagram's components.
- **Extract:** one beat per component: **Role** (gateway / orchestrator / domain core / persistence / cache / queue / worker / library / adapter), **Responsibility** (one line), **Key files**, **Why it exists** (the report's surviving teleological hypothesis — mark `(inferred)` if the report marked it so). Define the role word in plain words the first time it appears; never assume it.
- **Order beats by fan-in/importance**, not alphabetically — the lesson teaches shape, not a phone book.
- **Live code reads:** for the 2–3 most important components, open the key file with the read tool and quote a small excerpt (5–40 lines) — always after a prediction question ("what do you think this function is guarding?"). If the excerpt names a mechanism not yet built (a lock, a retry, a TTL), build it from the worked instance before naming it (Level register).
- **Ablation findings** (if the report ran them): fold in as an "if removed" line — the fastest way to make a role vivid.
- A component with a name but no file anchor is inventory, not insight.

### Beat 3 — The guided flow

- **From:** A §4 Critical path trace + §4b code tour (+ §2b sequence diagram) / B's mechanism notes.
- **Extract:** every hop with its file:line; the contrasting flow (error path / background job / write path); the code tour's numbered stops (ship those as homework at close, not as the main flow).
- **Worked example (mandatory):** before drawing the flow, pick **one concrete instance** and thread it through every hop — the request payload at the boundary, the exact row/keys written at the durability point (e.g. `charges(id=9184, status='pending', amount=42.00)`), the state flip at settle, and the same instance's fate on the error lane. Field names, state names, and route names come from the report's evidence anchors; the concrete values are illustrative — state this once ("sample values"). If the report's critical-path trace already carries example data, use its values verbatim; do not invent a second shape.
- **Rebuild:** the sequence diagram as a **stepped numbered flow** (one hop per line), each step showing actor → action → file anchor + the worked example's data at that hop (trace chip like `[carries: amount=42.00]`), data-shape changes called out (DTO / serialization / network), error path branching off in a marked lane.
- **Live code reads at every stop:** read the actual source lines with the read tool after the prediction question; reveal the mechanism, then attach the trace chip.
- **This is the lesson's heart.** If the report's trace is thin, teach it thin — do not pad with invented hops.

### Beat 4 — Tradeoff dials

- **From:** A §5 System design mapping + §7 Design decisions table / B's "Cost/tradeoff" fields.
- **Extract:** one **dial** per named tradeoff. A dial needs: the axis (consistency ↔ availability, latency ↔ throughput, coupling ↔ velocity, buy ↔ build, sync ↔ async), this system's position marker, **what the position buys** (one line), **what it costs** (one line), and the evidence anchor.
- **Render each dial in ASCII**, e.g. `[Consistency ——●—————— Availability]`, marker position from the report — never eyeballed. Build each dial in plain words from the worked instance before naming it; gloss newly introduced axis-end terms in one line. If the report names the tradeoff but not the position, draw the axis, both end-labels, and say "position: see report discussion" — never guess a coordinate.
- **Each dial carries its evidence line**: `file:line` / migration / config the report cited.
- Failure modes, trust boundaries, operability render as compact one-line-per-item lists under the dials — they are design-mapping rows too, but dial-prose would be noise.
- §7's decisions table (Decision / Alternative / Tradeoff / Rationale / Evidence) becomes dial captions; keep `(inferred)` flags.

### Beat 5 — Conventions & deviations

- **From:** A §6 Invariants + §8 Deviations from convention / B "Anti-patterns to avoid".
- **Extract:** invariants as a compact two-column list (convention → one evidence anchor). Deviations as **highlight beats** — the report calls these the highest-insight findings; give each: what's unusual, why it matters, evidence or `(inferred)`.
- B's anti-patterns ("don't copy this") render in the same beat with an `avoid:` chip — structurally identical to a deviation.

### Beat 6 — Patterns to steal (steal-it beats)

- **From:** A §9 Lessons for system design study / B "Patterns worth stealing" + "The one big idea".
- **Extract:** one beat per pattern/lesson. Beat anatomy (fixed): **Pattern name → Where it appears (`file:line`, 2–3 anchors) → System design problem it solves → Mechanism (one line or tiny ASCII sketch, in plain words — the name is earned after the mechanism, per Level register) → Cost/tradeoff → ✓ Steal when → ✗ Reject when.**
- The lens decides order: build-my-own lens orders by transferability; interview-prep lens by tradeoff richness; onboarding lens demotes this beat to compact.
- **A beat missing its cost row does not ship.**

### Beat 7 — The check (final exam)

- **From:** every module taught — the exam is synthesized from report-grounded material, not fetched. Full mechanics (8 questions, answer isolation, scoring, retake, closing menu) live in SKILL.md's "The check" section.
- **Question sourcing per beat:** mechanism questions from beat 3's flow, tradeoff questions from beat 4's dials, prediction/ablation questions from beats 1–2 and 3's failure lane, deviation/anti-pattern questions from beat 5. Reuse the worked example in at least one question — the learner should have met that instance before.
- **Question register and difficulty ramp:** fixed by SKILL.md's "The check" (concepts-not-coordinates, easy→hard ordering). The `file:line` anchors go in the verdict's why, not in the question or its correct option.
- **Hints (one per question, max):** per SKILL.md's "The check" — points at what the learner has already seen, never at the options. Drafting test: would the hint still make sense if the correct option were removed from the question? If not, it's the answer, not a hint.

### Beat 8 — Capstone: the one big idea

- **From:** B "The one big idea" directly; from A, synthesize the single insight that its §9 lessons converge on — synthesis of report content, not new content. The learner lens colors the wording (build-my-own → "you can steal this tomorrow"; interview-prep → "say this in the interview").
- One short paragraph, the loudest beat of the close. If the report hasn't converged enough to state one, say so rather than faking it.

### Fixed panels (never dropped, never edited)

- **What we don't know** ← A §10 / B "Open questions": verbatim items + the probe that would answer each. Delivered in the close as homework — honesty, not debris.
- **Glossary beat** ← A §11 terms + every term defined during the lesson: compact list at close, `term — one-line plain-words definition (file anchor)`. Re-translate any report glossary entry that itself leans on jargon; a definition is only done when every word in it is plain English or already defined.
- **No provenance footer:** do not narrate a "Provenance"/"Method" recap (report stamp, sweep stats, coverage ledger, method line) — none ships. The appendices ledger and stamp stay in working notes.

## Mermaid → ASCII translation rules

1. `graph TD/LR`, `flowchart` → layered ASCII diagram (roles as rows/columns); keep direction if it carries meaning (async flows left→right, domain boundaries as rows).
2. `sequenceDiagram` → stepped numbered flow (beat 3); participants become the actor column, error paths branch into a marked failure lane.
3. Keep every label; arrows get mechanism labels from the report; if the report's arrow is bare "→", infer the mechanism from that section's prose **only if stated there** — otherwise label it "flow" and flag the section in the teaching ledger.
4. Subgraphs become boundary containers with their trust/process/network label as a chip like `[network]`.
5. Any diagram over ~30 elements: split by subsystem, keep one full map plus per-beat excerpts.
6. Keep every diagram ≤ ~80 columns so it never wraps.

## Worked micro-example (fictional payment service)

Report says (A §7):
> Decision: balance constraint in DB (`balance_non_negative`) vs app-level check | Tradeoff: correctness under concurrent writers vs migration cost | Evidence: migrations/0007_add_balance_check.sql

Lesson renders (beat 4 dial):
- Axis: enforce-in-database ↔ enforce-in-application, marker at DB end: `[Enforce in DB ——●———— Enforce in app]`
- Buys: "no code path can bypass the invariant — even scripts and future services."
- Costs: "schema migration to deploy; harder to relax later."
- Evidence: `migrations/0007_add_balance_check.sql`.
- Check question: "A new service writes to the balances table directly. Does it still respect the no-negative rule? Why?"

Same fact, beat 6 steal beat:
- Pattern: **Database-enforced invariants** · Appears: `migrations/0007_…sql:4` · Solves: consistency under concurrent writers · Cost: deploy-time rigidity · ✓ Steal when: multiple writers + invariant is monetized (money, inventory, quota) · ✗ Reject when: rules change weekly or need canarying.