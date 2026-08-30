# Ledgers: hypothesis ledger + coverage ledger

## Contents
- The hypothesis ledger (purpose, schema, worked example, diversity rule)
- The coverage ledger (purpose, schema, rules, worked example)
- Convergence signal

Two ledgers run in parallel through the whole analysis. Both must be complete before synthesis.

1. The **hypothesis ledger** — the evolutionary database of the run: what we believe about the design and what evidence moved each belief.
2. The **coverage ledger** — proof the entire codebase was scanned: every directory accounted for with a disposition.

## The hypothesis ledger

### Purpose

The ledger forces hypotheses to be:

1. **Explicit** — written down, not held loosely in your head.
2. **Falsifiable** — each has a named probe that could kill it.
3. **Statused** — Candidate / Surviving / Refuted / Question, updated as evidence lands.

### Schema

| Field | Meaning |
|---|---|
| ID | Short stable identifier (H1, H2, ...) for cross-referencing |
| Hypothesis | One falsifiable sentence about structure, behavior, or intent |
| Type | structural / causal / teleological (why-did-they-build-it-this-way) |
| Probe | The cheapest concrete command or file read that could change its status |
| Status | Candidate → Surviving or Refuted (Question = probe not yet run) |
| Evidence | file:line, commit hash, or grep count that produced the current status |

Keep the hypothesis ledger in your working notes. When a hypothesis is promoted to Surviving, its evidence should appear in the report. Refuted hypotheses generate the "Deviations from convention" section.

### Worked example

Scenario: reverse engineering a fictional payment-processing service.

| ID | Hypothesis | Type | Probe | Status | Evidence |
|----|-----------|------|-------|--------|----------|
| H1 | `payments/` is the domain core; `api/` is a thin adapter | causal | trace one POST /charge end-to-end | Surviving | api/charges.py:20 → payments/service.py:88 |
| H2 | Background jobs are driven by Celery, not cron | structural | `rg "celery\|@task\|crontab"` | Refuted | no celery imports; `crontab` in deploy/ — jobs are cron-driven |
| H3 | Double-entry ledger is enforced in the DB, not app code | teleological | inspect migrations for constraints/triggers | Surviving | migrations/0007_add_balance_check.sql: constraint `balance_non_negative` |
| H4 | `legacy_v1/` is dead code | structural | ablation probe (imports) | Refuted | zero imports, but referenced in docker-compose as separate service — it's an external contract, not dead |
| Q1 | Why is there no retry logic around the PSP call? | — | `git log -S "retry" -- payments/` | Question | — |

Notes from the example:

- H2's refutation *changed the report*: "jobs are cron-driven" went into System Map; the initial Celery guess went nowhere.
- H4 shows the ablation trap: "no importers" ≠ dead. Probe before declaring.
- Q1 becomes a Design Decision entry with inference marked: "No retry around PSP call — *likely* deliberate (idempotency concerns), unconfirmed."

### Diversity rule

Aim for a mix of hypothesis **types** at all times:

- **Structural** — what exists, what depends on what.
- **Causal** — what actually happens at runtime for a given input.
- **Teleological** — why a team would choose this (cost, team size, history, risk).

Teleological hypotheses are the hardest to confirm and the most valuable when they survive — they are the "design rationale" the whole exercise is after. Dig for them with **decision archaeology** (Phase 5): the rejected alternative (`git log -S`, ADRs, comments, deviation from stack-idiomatic default), the forcing constraint (scale numbers, team size in `git shortlog`, schema pressure), and the named cost. Constraint evidence upgrades a teleological hypothesis from (inferred) to evidence-backed.

## The coverage ledger

### Purpose

The coverage ledger enforces the coverage contract: **100% of the repo enumerated and classified before synthesis.** It is the difference between "I studied the parts I liked" and "I studied the repo." It ships as the report appendix, so the reader can verify nothing was skipped.

### Schema

| Field | Meaning |
|---|---|
| Path | Directory or file cluster (top-level, plus nested clusters that matter) |
| Files / LOC | Counted by `analyze.py sweep` — never guessed |
| Disposition | One of the canonical tags (below), or `unclassified` (a debt to clear) |
| Deep-read | `none` / `skimmed` / `analytical` / `full` — or **`breadth-only`** in SELECTIVE-HUGE mode: structure, seams, and load-bearing config examined; file interiors unread. `analytical` = a full read answering one named question (the probing.md read-tier ladder). In FULL-READ mode every `source` row is `full` by definition; in SELECTIVE it's earned per path |
| Note | One-line role hypothesis or question; in SELECTIVE-HUGE, zone rows say `zone (deep)` and why they were picked |

Canonical dispositions: `core` · `interface-adapter` · `support-util` · `test` · `config-ops` · `schema-migration` · `generated` · `vendored` · `docs` · `data-fixture` · `asset` · `dead-suspect` · `unclassified`.

(The sweep script emits file-level tags; promote them to these study dispositions with judgment: a file tagged `source` in a load-bearing directory becomes `core`; a leaf utility directory becomes `support-util`; zero-fan-in candidates become `dead-suspect` pending an ablation probe. The sweep's *primary* disposition already applies the package-signal rule — a manifest-bearing directory with a real source share stays `source` even when its bundled `tests/` outcount source files — so a `test` verdict on a package tree means it genuinely has no source, e.g. a pure fixtures dir.)

### Rules

- **No path is skipped.** Config, migrations, scripts, tests, CI, and build files get dispositions first — that's where factual architecture lives.
- **`unclassified` is a debt, not a category.** Every unclassified bucket must be resolved (classified or explicitly justified) before synthesis.
- **Generated/vendored are accounted, not ignored.** Record what is generated and analyze the *inputs* (`.proto`, OpenAPI, schema files) — generation inputs are design artifacts.
- **Sweep is never budgeted; deep reads follow the sweep's policy.** `analyze.py sweep` prints the verdict and it is binding. The three tiers (FULL-READ / SELECTIVE / SELECTIVE-HUGE), their thresholds, and their deep-read obligations are defined once in SKILL.md's deep-read policy; the ledger's `Deep-read` column simply records what each path earned under that policy — `full` for every `source` row in FULL-READ mode, earned tiers in SELECTIVE, zone rows + `breadth-only` in SELECTIVE-HUGE.
- **The ledger ships.** If a top-level path is missing from the appendix, the report is incomplete by definition.

### Worked example

| Path | Files | LOC | Disposition | Deep-read | Note |
|---|---|---|---|---|---|
| `src/payments/` | 42 | 5.1k | core | full | domain core — all flows terminate here |
| `src/api/` | 18 | 2.2k | interface-adapter | full | thin HTTP adapters over the domain |
| `src/utils/` | 11 | 0.6k | support-util | skimmed | leaf helpers, zero fan-in questions |
| `migrations/` | 23 | 1.8k | schema-migration | full | constraints live here, not in app code (H3) |
| `deploy/` | 9 | 0.4k | config-ops | full | docker-compose: legacy_v1 runs as a service (H4) |
| `tests/` | 60 | 8.9k | test | skimmed | mirror of src/; e2e tests confirm coupling |
| `web/dist/` | 341 | — | generated | none | build output; inputs in `web/src/` |
| `docs/` | 7 | 2.1k | docs | skimmed | includes real ADRs — rationale goldmine |
| `fixtures/` | 12 | 0.3k | data-fixture | none | sample payloads for e2e |
| `legacy_v1/` | 30 | 4.0k | dead-suspect → external contract | skimmed | zero imports but deployed as a service (H4) |

Note how `legacy_v1/` carries both ledgers: the coverage ledger surfaced it, the hypothesis ledger resolved what it is.

## Convergence signal

Stop probing and synthesize when:

- The last 3 probes produced no hypothesis status changes (model is stable), **and**
- Every architectural claim you intend to make is Surviving or explicitly marked as inference, **and**
- The coverage ledger accounts for 100% of top-level paths with no unexplained `unclassified` bucket, **and**
- The sweep's deep-read policy is satisfied per its tier rules (SKILL.md deep-read policy).

Convergence gates *synthesis*, not *shipping*: the run is done only after the Phase 7 verification pass — `analyze.py verify` exits 0 on the final text and the cold-eyes re-probe has checked the load-bearing claims against the code. A converged, unverified report is still a draft. (In SELECTIVE-HUGE mode the verification pass also checks §0b's Scope & confidence statement against this ledger's `breadth-only` partition.)

If new probes keep flipping statuses, the model isn't converged — keep probing, prioritizing Question rows with cheap probes. If coverage has holes, close them before synthesizing: unexamined directories are where confident hallucinations come from.