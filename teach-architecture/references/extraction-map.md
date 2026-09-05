# Extraction map: codebase → lesson module

## Contents
- Module-by-module extraction (frame, map, components, flow, dials, conventions, patterns, capstone, fixed panels)
- Prep findings → archify rendering rules
- Worked micro-example (fictional payment service)

The codebase — read in prep and re-read live during the lesson — is the source of truth; the lesson is its workshop-shaped projection. This file is the row-by-row translation table plus extraction rules. Everything the prep pass surfaces maps into the same eight module beats of the lesson arc.

Work in generation order: ask the goal + lens, run the prep pass, build the teaching ledger, then extract per module.

## Module-by-module extraction

### Beat 0 — Frame + hook question

- **From (prep):** entry points (main modules, CLI/console entry, server bootstrap, `package.json` scripts), README, config — whatever answers "what is this system and what is it for".
- **Extract:** one plain-language frame (the repo's own words, lightly compressed, 2–3 sentences); the learner lens — derived from the user's stated goal per SKILL.md Step -1, applied silently. Do not recite the prep method or file counts.
- **Add:** the hook question — the hardest problem this system solves, phrased as a question. Derive it from the load-bearing decision prep found (a schema constraint, a lock, a queue, a retry loop — the code's most consequential choice), never invent one. Pose it and do not answer it yet; the lesson arc resolves it.
- **Depth honesty:** one line stating what prep read end-to-end and what it only skimmed.

### Beat 1 — The system map

- **From (prep):** components found from entry points + import graph + directory shape; edges found from *actual connections* — HTTP client calls, DB DSNs and queue URLs in config, ORM models, migration schemas.
- **Extract:** every component and edge; boundary labels [process]/[network]/[trust] from deployment and config evidence (separate processes, network hops, credential lines); the Sources anchors.
- **Tests are not components.** The test tree (`tests/`, `test_*.py`, `__tests__/`, `*_test.go` — whatever this repo's convention names it) exists to exercise the system; it is not part of the system. Never render it as a node or region on the map, and never give it a component-tour beat. Tests enter the lesson only as **evidence** — the beat-3 live run, the worked instance's input values, and statically-read executable documentation — never as architecture.
- **Rebuild:** the map → **archify `architecture`** diagram (rendering rules below; ASCII fallback only when archify is unavailable). Node labels keep the paired form "Role — `code/entity/`" (e.g. "Orchestrator — `api/workflows.py`"). Edge labels carry the mechanism ("publishes events", never "→") — taken from what the connecting code actually does.
- **First interaction:** before explaining any component, ask a placement or ablation question on the freshly rendered map ("if we delete this box, what breaks?"). This is one of the lesson's easy warm-up questions — it should be answerable in one sentence from the map the learner is looking at, no mechanism memory required yet.
- **First sight of vocabulary:** as you introduce components on the rendered map, give every component-role word on the map (gateway, queue, cache, adapter — whatever appears) a one-line plain-words definition in passing. No word on the map is pre-understood (Level register).

### Beat 2 — Component tour (role beats)

- **From (prep):** one beat per component found in the map, with its key files and import fan-in.
- **Extract:** one beat per component: **Role** (gateway / orchestrator / domain core / persistence / cache / queue / worker / library / adapter), **Responsibility** (one line), **Key files**, **Why it exists** (the best-supported purpose hypothesis — mark `(inferred)` unless the code, comments, or docs state the purpose outright). Define the role word in plain words the first time it appears; never assume it.
- **Order beats by fan-in/importance**, not alphabetically — the lesson teaches shape, not a phone book.
- **Live code reads:** for the 2–3 most important components, open the key file with the read tool and quote a small excerpt (5–40 lines) — always after a prediction question ("what do you think this function is guarding?"). If the excerpt names a mechanism not yet built (a lock, a retry, a TTL), build it from the worked instance before naming it (Level register).
- **Ablation reasoning:** where a component's removal consequence is obvious from coupling (single consumer, hard dependency), fold it in as an "if removed" line — the fastest way to make a role vivid. Where it isn't obvious, that question belongs in the check, not in a guessed answer.
- A component with a name but no file anchor is inventory, not insight.

### Beat 3 — The guided flow

- **From (prep):** the critical path traced by reading the code — entry point through service layers to the durability point and back out; plus the contrasting flow (error path / background job / write path) found in the error handling and workers.
- **Extract:** every hop with its file:line; the error/failure lane; any numbered code-tour stops (ship those as homework at close, not as the main flow).
- **Live test run (mandatory when tests exist — full mechanics, setup recipe, and failure fallback in SKILL.md's "Live test run"):** beat 3 runs the **one test that exercises the critical path** — predict what it asserts → run → read the real output together → map each assertion back to a hop.
- **Worked example (mandatory — input-data sourcing rule in SKILL.md's guided-flow beat: the critical-path test file's values verbatim, run or not; else illustrative, labeled once):** thread **one concrete instance** through every hop — the request payload at the boundary, the exact row/keys written at the durability point (e.g. `charges(id=9184, status='pending', amount=42.00)`), the state flip at settle, and the same instance's fate on the error lane.
- **Rebuild:** the sequence diagram **twice** — an **archify `sequence`** render per the rendering rules below (the worked instance's input payload on the first message, its values riding the messages after, error lane preserved), plus the in-terminal **stepped numbered flow** backbone (one hop per line), each step showing actor → action → file anchor + the worked example's data at that hop (trace chip like `[carries: amount=42.00]`), data-shape changes called out (DTO / serialization / network), error path branching off in a marked lane.
- **Live code reads at every stop:** read the actual source lines with the read tool after the prediction question; reveal the mechanism, then attach the trace chip.
- **This is the lesson's heart.** If prep's trace is thin, teach it thin — do not pad with invented hops.

### Beat 4 — Tradeoff dials

- **From (prep):** tradeoffs surfaced where the code paid for them — config choices and their comments, migrations showing schema evolution, dependency decisions (self-built vs library), locks vs optimistic checks, sync vs async seams.
- **Extract:** one **dial** per named tradeoff. A dial needs: the axis (consistency ↔ availability, latency ↔ throughput, coupling ↔ velocity, buy ↔ build, sync ↔ async), this system's position marker, **what the position buys** (one line), **what it costs** (one line), and the evidence anchor.
- **Render each dial in ASCII**, e.g. `[Consistency ——●—————— Availability]`, marker position only where evidence supports a coordinate (the constraint exists in the migration; the lock exists in the code) — never eyeballed. Build each dial in plain words from the worked instance before naming it; gloss newly introduced axis-end terms in one line. If the evidence names the tradeoff but not the position, draw the axis, both end-labels, and say "position: discussed live" — never guess a coordinate.
- **Each dial carries its evidence line**: `file:line` / migration / config the prep pass cited.
- Failure modes, trust boundaries, and operability found in prep render as compact one-line-per-item lists under the dials — they are design-mapping rows too, but dial-prose would be noise. Decisions implied by config comments become dial captions; keep `(inferred)` flags on any rationale the code doesn't state.

### Beat 5 — Conventions & deviations

- **From (prep):** invariants = patterns repeated consistently across the codebase (every handler validates at the boundary, every worker is idempotent); deviations = the oddities — the one module that breaks the repo's own convention, the surprising dependency direction, the hand-rolled replacement for a standard library piece.
- **Extract:** invariants as a compact two-column list (convention → one evidence anchor). Deviations as **highlight beats** — these are the highest-insight findings; give each: what's unusual, why it matters, evidence or `(inferred)`.
- Clear anti-patterns ("don't copy this") render in the same beat with an `avoid:` chip — structurally identical to a deviation.

### Beat 6 — Patterns to steal (steal-it beats)

- **From (prep):** the transferable mechanisms the reading surfaced — the patterns worth stealing regardless of this repo's domain.
- **Extract:** one beat per pattern. Beat anatomy (fixed): **Pattern name → Where it appears (`file:line`, 2–3 anchors) → System design problem it solves → Mechanism (one line or tiny ASCII sketch, in plain words — the name is earned after the mechanism, per Level register) → Cost/tradeoff → ✓ Steal when → ✗ Reject when.**
- The lens decides order: build-my-own lens orders by transferability; interview-prep lens by tradeoff richness; onboarding lens demotes this beat to compact.
- **A beat missing its cost row does not ship.**

### Cross-cutting — Section checks (end of every module, not a final exam)

- **From:** each beat's own material — the check that closes a module is synthesized from the evidence-grounded content that beat just taught. Full mechanics (sizing, register, difficulty ramp, hints and the drafting test, verdict + why, cumulative tally, miss-reopens, closing menu) live in SKILL.md's "Section checks" section.
- **Question sourcing per beat:** beat 1's check draws placement/ablation questions from the fresh map; beat 2's from component roles and mechanism predictions on the live code read; beat 3's from the flow's hops, the observed test run, and its failure lane; beat 4's from the dials' buys/costs; beat 5's from deviations/anti-patterns; beat 6's from steal/reject reasoning. Reuse the worked example in the flow and dials checks — the learner should have met that instance before being asked about it. The `file:line` anchors go in the verdict's why, not in the question or its correct option.

### Beat 7 — Capstone: the one big idea

- **From:** synthesize the single insight the prep findings and the taught modules converge on — synthesis of the lesson's own content, not new content. The learner lens colors the wording (build-my-own → "you can steal this tomorrow"; interview-prep → "say this in the interview").
- One short paragraph, the loudest beat of the close. If the material hasn't converged enough to state one, say so rather than faking it.

### Fixed panels (never dropped, never edited)

- **What we don't know** ← the prep pass's open questions — what the code couldn't answer (an unexplained config flag, a dependency with no visible user, a mechanism whose purpose stays a hypothesis): verbatim items + the probe that would answer each (a dynamic test, a doc link, a question to the team). Delivered in the close as homework — honesty, not debris.
- **Glossary beat** ← every term defined during the lesson: compact list at close, `term — one-line plain-words definition (file anchor)`. A definition is only done when every word in it is plain English or already defined.
- **No provenance footer:** do not narrate a "Provenance"/"Method" recap (prep method, sweep stats, coverage ledger, method line) — none ships. The prep ledger stays in working notes.

## Prep findings → archify rendering rules

1. The prep map → archify `architecture` (beat 1; `<repo-name>-map.html`); the prep trace → archify `sequence` (beat 3; `<repo-name>-flow.html`). Both deliver in the repo (repo root, or `docs/architecture/` if present) and both take their facts from prep's verified evidence only — never from memory of similar systems.
2. Render the verified topology as-is — nodes, edges, direction, boundary groupings; never "improve" the topology or drop a component for cleanliness. (The test tree is not a component — see Beat 1 — so its absence from the map is correctness, not a dropped fact.) Keep direction if it carries meaning (async flows left→right, domain boundaries as rows).
3. Archify's fast authoring path: read one matching schema + one matching example, author the JSON, `validate`, then one `deliver`. No visual-check ceremony mid-lesson.
4. Keep every label; edges get mechanism labels from the connecting code; if the exact mechanism isn't clear from the code, label it "flow" and flag it as an open question for the honesty panel.
5. Boundary evidence (separate processes, network hops, credential lines) carries over as region/boundary wording in the diagram.
6. Archify's authoring invariants apply (one clear main path, sparse labels); where the real map is denser, keep the facts — never delete an edge to fit a layout.
7. **Inline text visuals stay text** — stepped flows (beat 3), dials (beat 4), steal-beat sketches (beat 6): monospace-fenced, ≤ ~80 columns so nothing wraps.
8. **ASCII fallback:** when archify is unavailable (not installed, or `deliver` fails), redraw the map as a layered ASCII diagram and the sequence as the stepped numbered flow alone, say so to the learner, and continue — the lesson never stalls on the medium.

## Worked micro-example (fictional payment service)

Prep finds (beat 4 evidence):
> `migrations/0007_add_balance_check.sql` adds a `balance_non_negative` constraint; `models/charge.py` catches the constraint violation and converts it to a 422; a comment names the rejected alternative ("app-level check raced under load").

Lesson renders (beat 4 dial):
- Axis: enforce-in-database ↔ enforce-in-application, marker at DB end: `[Enforce in DB ——●———— Enforce in app]`
- Buys: "no code path can bypass the invariant — even scripts and future services."
- Costs: "schema migration to deploy; harder to relax later."
- Evidence: `migrations/0007_add_balance_check.sql`.
- Check question: "A new service writes to the balances table directly. Does it still respect the no-negative rule? Why?"

Same fact, beat 6 steal beat:
- Pattern: **Database-enforced invariants** · Appears: `migrations/0007_…sql:4` · Solves: consistency under concurrent writers · Cost: deploy-time rigidity · ✓ Steal when: multiple writers + invariant is monetized (money, inventory, quota) · ✗ Reject when: rules change weekly or need canarying.