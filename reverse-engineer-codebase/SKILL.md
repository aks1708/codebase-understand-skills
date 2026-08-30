---
name: reverse-engineer-codebase
description: Systematically reverse engineer a single codebase (one repository), sweeping the ENTIRE codebase and mapping its architecture back to system design concepts (architectural style, how components are strung together — seams, transports, contracts, coupling — data flow, state, consistency, scalability, failure modes, tradeoffs) so engineers and software architects can study it as prior art. Use when the user asks to "reverse engineer this repo", "explain this codebase's architecture", "understand how this project works", "map this codebase", "archaeology on this code", or wants to learn system design from a real codebase before building their own software.
---

# Reverse Engineering a Codebase

Method (after ArchAgent, Gupta et al.): hypothesis → falsifiable probe → keep only what survives. The search space is the **entire repo**, enumerated by a full sweep, then probed by depth.

Tools (in this skill's directory, Python 3 stdlib only): `scripts/orient.py` (Phase 0) and `scripts/analyze.py` — `sweep` `langs` `skeleton` `ablation` `trace` `focus` `verify`. They are the cheap-probe engines; learn each one's flags from `--help`. Git is required for history probes; if missing, read files directly and note it.

## Step -1: Ask the user's goal (mandatory, before any repo access)

Ask via the `question` tool: *"Before I dig in — what do you want to understand from this codebase?"* Options:

- **Overall architecture** — components, style, how pieces fit.
- **A specific flow or feature** — "how does auth work", trace a request end to end.
- **Design lessons** — tradeoffs and prior art to steal before building your own.
- **A specific subsystem** — one module, integration, or concern in depth.
- **Everything** — the full study report.

Skip or "up to you" → default full study. No level question: the register is fixed (below). Multiple goals → honor all, note their priority.

Use the goal everywhere: it becomes report §0 and sets which sections get depth; it seeds one or more Candidate hypotheses ("understand auth" → H: "auth is enforced in middleware, not per-handler"); right after the sweep it drives `focus` for the reading order; the traced flow and lessons answer it first.

**Conditional scope question.** The only other question the skill may ask — and only when the sweep verdict (Phase 1) is `selective-huge` **and** the goal is broad (architecture / lessons / everything). Then ask, with the sweep's largest core directories as concrete options: *"This repo is too large for even selective depth. Which 1–3 subsystems should get the deep treatment?"* Options: (a) name 1–3 **deep zones**, (b) whole-repo shallow — map + seams everywhere, no file interiors, (c) you decide (auto-pick zones by goal × fan-in × focus). Narrow goals (specific flow/subsystem) skip this — the goal already names the zone. Record the choice in report §1 and the coverage ledger.

## Audience: one fixed register

**Experienced software engineer** — fluent vocabulary, no pedagogy; tradeoffs named in one line, evidence in `file:line`. (Downstream consumers wanting a different pitch — e.g. teach-architecture's first-principles course — re-register it themselves.) The report must: map every component to system design vocabulary (gateway, orchestrator, domain core, persistence, cache, queue, worker, library); state each load-bearing decision as a tradeoff; cite evidence for every claim and mark inference; pair Mermaid node labels concept + code entity ("Orchestrator — `src/orchestrator/`"); end with transferable lessons (steal/avoid/when).

## Scope: exactly one repository

Everything runs inside the repo the user pointed at. Other repos appearing in it (manifest deps, submodules, vendored forks, URLs) are **interfaces, not targets** — record the contract, never read their code. Vendored/monorepo packages inside the repo count as repo. If an answer truly needs the other repo's internals → Open questions, dependency named, move on.

## Coverage contract: sweep everything, always

Two tiers of coverage:

- **Swept** — every file enumerated, classified, and counted. Automated, non-negotiable, 100% before synthesis. Config, migrations, scripts, and tests are where the *factual* architecture lives — nothing is skipped for looking boring. Generated/vendored trees are accounted, not read; their *inputs* (`.proto`, OpenAPI, schemas) are read — generation inputs are design artifacts.
- **Deep-read** — read in full because evidence demanded it; allocated by the sweep's verdict (below).

Dispositions: `core` · `interface-adapter` · `support-util` · `test` · `config-ops` · `schema-migration` · `generated` · `vendored` · `docs` · `data-fixture` · `asset` · `dead-suspect`. The **coverage ledger** (every top-level path with file counts, LOC, disposition, deep-read status) ships as the report appendix; 100% of top-level paths or the report is incomplete.

### Deep-read policy (the sweep decides, not you)

`analyze.py sweep` prints the verdict — binding; also in `deep_read_policy` in `--json` output:

- **FULL-READ** — source files ≤ 100 *and* source LOC ≤ 50k (flags: `--threshold-files/--threshold-loc`). Read **every source file in full** before synthesis; every `source` ledger path is `full` by definition. Generated/vendored stay swept-only; manifests, migrations, design inputs read per their own rules.
- **SELECTIVE** — above those thresholds. Deep reads follow hypothesis value: critical-path files, high fan-in, load-bearing config. Ledger records `none`/`skimmed`/`analytical`/`full` as earned (`analytical` = a full read answering one named question — see `references/probing.md`).
- **SELECTIVE-HUGE** — source files > 2,000 *or* source LOC > 500k (flags: `--threshold-huge-files/--threshold-huge-loc`, 0 disables). Too big for even selective depth. Sweep stays 100%; concentrate depth: pick **1–3 deep zones** (goal-aligned subsystems: high fan-in × focus score × goal fit), deep-read only those, everything else **breadth-only** (structure, seams, load-bearing config/migrations — no file interiors). Zones come from the user (conditional scope question) or auto-pick; the partition goes in the coverage ledger; report §1 carries a Scope & confidence statement; claims must not exceed it.

On repos > 30k files the sweep auto-runs in fast mode (counts + tags at 100%, LOC skipped — size tiers unmeasurable, policy floors to selective); `--loc`/`--no-loc` force either mode. Scope expensive probes by pointing them at a zone: `analyze.py skeleton <zone-dir>` works — root is just a path.

## Core loop (repeat until convergence)

0. **Goal** — Step -1. Mandatory gate.
1. **Orient** — cheapest signals first (Phase 0).
2. **Sweep** — enumerate + classify 100% of the repo; start the coverage ledger; get the deep-read verdict (Phase 1).
3. **Focus** — rank files against the goal → the deep-read queue (Phase 1).
4. **Hypothesize → Probe → Refine** — falsifiable theories, cheap tests, keep survivors (Phases 2–3).
5. **Seams** — pin every connection (Phase 2b).
6. **Map** — project onto system design concepts (Phase 5).
7. **Synthesize** — draft the report when the model is stable (Phase 6).
8. **Verify** — second pass against the codebase, then fix and re-audit until clean (Phase 7).

## Phase 0: Orientation

Before reading any source. Each probe is seconds.

```bash
python3 scripts/orient.py <repo-root>     # manifests, layout, git tempo, hot paths
ls                                        # top-level layout
cat README.md / docs/ <manifest>          # stated intent vs. actual behavior
git log --oneline -50                     # tempo; --format='%s' -200 → hot paths
ls scripts/ Makefile docker-compose.yml .github/workflows   # ops surfaces
```

The dependency manifest is the densest single signal: the problem domains the repo chose to solve — and, by omission, rolled itself. README = aspirational architecture; build scripts = factual. Note the gaps: "we always meant to" lives there.

## Phase 1: Full sweep + goal focus

```bash
python3 scripts/analyze.py sweep <repo-root> [--depth 2] [--json]
```

**Enumerate (automated)** — per-directory files/LOC/tags, manifests, entry points, test layout, generated/vendored clusters, migrations, an explicit unclassified bucket, the deep-read verdict, and the package-signal rule (a manifest-bearing directory with real source share is a *package* — never mislabeled `test` because its bundled tests outcount source). **Classify (judgment)** — every top-level path gets a disposition + one-line role hypothesis; unclassifiable paths become ledger Questions, never silently dropped.

Sweep output feeds everything downstream: language mix → inventory skeleton; import edges → ablation candidates; test layout → behavioral contracts; migrations/config/CI → state, ops, deployment; unclassified bucket → first questions.

Then turn the goal into a reading order:

```bash
python3 scripts/analyze.py focus <repo-root> "<goal as stated>" [--tier core|all] [--top N] [--fast|--full]
```

- Scores per file: body-token coverage + path/name matches + `def`/`class` symbol matches + goal terms in the opening 15 lines. In fast mode (auto above 2k core files, or `--fast`) body tokenization is skipped — coarser ranking for huge repos; `--full` forces the exact pass.
- `--tier core` = source + design-input only; `--tier all` adds docs/tests/config (use for ops/contract goals). Dependency trees never qualify.
- The ranking is a **prior, not a verdict** — one input to deep-read selection alongside fan-in, dispositions, and the ledger. Zero-score files are still swept and ledgered; silence means the goal's vocabulary isn't in the code — retry with the repo's own terms.
- Top hit = natural Layer-3 trace seed; the `--top 40` tail = skim queue. Exit 1 (all stop-words) → no ranking, note it, proceed via sweep order.

## Phase 2: Layered probing (cheapest evidence first)

1. **Layer 1 (seconds):** README, manifests, `git log`, directory names — what problem does this solve?
2. **Layer 2 (minutes):** `analyze.py skeleton` — classes, functions, imports, routes. **FULL-READ gate:** replace grep-outlining by reading every source file in full, seam-first (entry points and handoffs lead; interiors get classification). SELECTIVE-HUGE gate: skip files outside the deep zones entirely — their skeleton entry is the analysis.
3. **Layer 3 (minutes, the most expensive and most reliable probe):** trace one representative request end to end — handler → service → repo → DB, seeded from `focus`. Read only those files in full. Carry **one worked instance** (concrete request, sample values) and record per hop: `file:line`, responsibility assumed, data shape in/out with the instance's values, failure behavior (swallowed/propagated/retried/crashed). Output = a **flow story about the worked instance**, not a file list. In SELECTIVE/SELECTIVE-HUGE, whole-file reads are for the traced path only.
4. **Layer 4 (as needed):** ablation reading — for each surviving teleological hypothesis, find and check the one file or commit that would disprove it.

**Deep reads are connection-shaped, not file-shaped.** The unit of study is the seam: an entry point, a handoff, a data-shape change, a state transition. When a read hits a seam, answer four questions — what crosses, in what shape, what breaks if the other side fails, who owns the contract. Everything else in the file can be skimmed.

## Phase 2b: Seams and runtime topology

Run after the first trace, before Phase 5. Recipes: `references/probing.md`.

- **Runtime topology** — from the ops surfaces (compose, Procfile, k8s, systemd, CI, `exec`/`spawn`): how many processes, who shares one, who talks over a network, singletons vs. scaled. Imports can't see this. Sketch it with `[process]`/`[network]`/`[trust]` chips; the Layer-3 trace confirms or corrects.
- **Seam inventory** — for every map edge: endpoints (`file:line`), **transport** (in-process call, HTTP/gRPC, queue, shared table, file), **contract** (shape crossing + which side owns it — published type, schema, ORM model, or implicit convention), **coupling direction** (who knows about whom), **error semantics** (propagated/swallowed/retried/dead-lettered). Imports draft it; traces and topology correct it.
- **Seams table** — ships as report §3b and becomes the map's edge labels: never bare "→" — e.g. `HTTP POST /charge [network] · JSON contract owned by api/`.

## Phase 3: Hypothesis ledger

Explicit and statused (format + examples: `references/hypothesis-ledger.md`): **Candidate** (plausible, untested) → **Surviving** (≥1 independent probe) or **Refuted** (record why — deviations from convention are the design insight); plus **high-value questions** (answerable with one probe). Rules: never present non-Surviving hypotheses as fact; prefer diverse hypothesis *types* (structural / causal / teleological); two ledgers in parallel — hypothesis (this) and coverage (Phase 1) — both complete before synthesis.

## Phase 4: Ablation

For the 2–3 biggest architectural choices: *what breaks if this goes away?*

```bash
python3 scripts/analyze.py ablation <repo-root> <module>
python3 scripts/analyze.py trace <repo-root> <symbol>
```

Many importers → load-bearing (hub or leaf?). All importers in one directory → internal detail. No importers → dead code, plugin boundary, or external contract — grep dynamic loading / framework registration before deciding (see `probing.md`).

## Phase 5: System design mapping (the study payoff)

Answer the architect's questions with evidence — every row cites `file:line`/config/migration/commit or is marked (inferred). Probe recipes: `references/probing.md`.

| Concept | Questions | Typical evidence |
|---|---|---|
| Architectural style | Monolith? Services? Event-driven? Layered? Plugin? | directory structure, process boundaries, transport code |
| Component roles | Gateway / orchestrator / domain core / persistence / cache / queue / worker / library? | fan-in/fan-out, import direction |
| Data flow | Sync or async? Transports? Where do data shapes change? | seams (Phase 2b) + critical path trace |
| State & storage | Which stores? Schemas? Consistency? Idempotency? Transactions? | migrations, schema files, transaction code |
| Scalability | What scales horizontally? Singletons/leaders/bottlenecks? Locks, global state? | stateful components, locks, caches |
| Failure modes | Retries? Timeouts? Circuit breakers? Backpressure? DLQs? Health checks? | grep probes in error paths |
| Trust boundaries | Where do requests enter? Authn/authz? Secrets? | middleware, config, network layout |
| Operability | Config, flags, observability, deployment shape? | config files, CI/CD, Dockerfiles |
| Tradeoffs | CAP position? Latency vs throughput? Coupling vs velocity? Buy vs build? | inferred from decisions + evidence |

**Decision archaeology** — for each surviving load-bearing decision, dig three artifacts before writing §7: (1) the **rejected alternative** (`git log -S`, ADRs, "we tried" comments, deviation from the stack-idiomatic default — the highest-yield dig); (2) the **forcing constraint** (scale numbers, team size, schema pressure, commit-trail deadlines); (3) the **named cost** — no decision ships without one. All three missing → the rationale stays (inferred); don't manufacture plausibility.

## Phase 6: Synthesis

Write only after both ledgers converge (few new refutations; coverage at 100%; deep-read policy satisfied). **The converged draft is not the report** — Phase 7 verifies it first. One markdown file at the repo root (`ARCHITECTURE.md`; `PRIOR-ART.md` for inspiration goals — templates in `references/artifact-templates.md`). Skeleton:

```markdown
# Architecture: <project>

## 0. What you asked for             (the user's goal from Step -1)
## 0b. Scope & confidence            (selective-huge only: deep zones, breadth-only rest)
## 1. What it is
## 2. System map                     (edges labeled with transport + contract — Phase 2b)
## 3. Component inventory            (with system design role per component)
## 3b. Seams: how components tie together   (runtime topology + seam inventory table)
## 4. Critical path trace            (worked instance end to end; + one contrasting flow)
## 5. System design mapping          (style, data flow, state, scalability, failure modes, tradeoffs)
## 6. Invariants and conventions
## 7. Design decisions and inferred rationale  (decision · rejected alternative · forcing constraint · cost)
## 8. Deviations from convention
## 9. Lessons for system design study
## 10. Open questions
## 11. Glossary                      (repo-native terms, codenames, domain words)
## Appendix: Coverage ledger         (proof the entire codebase was scanned)
```

Packaging rules:

- **Stamp:** `Generated <date> at commit <hash>` — a snapshot; stale reports get re-run, not hand-edited. Phase 7's audit checks it.
- **Diagrams Mermaid-first** (system map, traced-request sequence); node labels pair concept + code entity; edge labels carry the seam; each diagram followed by a `> **Sources:**` line; ASCII fallback when unwieldy.
- **One worked instance end to end** — same concrete request at every hop, again in the contrasting flow's failure lane and in lessons. A reader can say what the data looks like at hop 1 and hop N. In SELECTIVE-HUGE, the instance lives inside a deep zone.
- **Scope honesty (SELECTIVE-HUGE):** §0b states what was deep-read vs breadth-only; claims follow the tier's structural-only boundary (deep-read policy; Phase 7b checks §0b against the ledger).
- **Per-section Sources lines** where claims span subsystems; **code tour** (8–15 seam-ordered stops) under §4; **glossary** one line per repo-native term with anchor.
- **Route by goal:** building-on-your-own goals → Template B (`PRIOR-ART.md`); understanding/audit → Template A. Both carry the same contracts, different emphasis.
- **Split mode:** report > ~500 lines or user asks for a wiki → `docs/architecture/` multi-page set with index README; same analysis, same ledgers.

## Phase 7: Verification pass (report against codebase)

A report that hasn't been verified is a draft. Two tiers, both mandatory, on the final text:

### 7a. Mechanical citation audit (automated)

```bash
python3 scripts/analyze.py verify <repo-root> [report ...] [--json]
# default discovery: ARCHITECTURE.md | PRIOR-ART.md | docs/architecture/*.md
```

Checks every `file:line` anchor, cited path, cross-link, and the stamp against the repo. Findings: `anchor-missing`, `line-out-of-range`, `line-blank`, `path-missing`, `link-broken`, `stamp-missing`, zero citations (fails by definition). **Exit 1 = does not ship.** Fix by re-locating the real anchor in the code — never by deleting the citation — and re-run until exit 0. Split-mode wikis are audited file-by-file.

### 7b. Cold-eyes claim re-probe

The audit proves the address exists; only re-reading proves the claim lives there. Re-probe with fresh eyes, against the code — not memory:

1. **Sample by blast radius** — one+ claim per section, priority: §5 mapping rows, §7 decisions, §8 deviations, every goal-serving claim, the worked instance's hops re-walked verbatim.
2. **Over-claims:** *always/never/only/guaranteed* → counterexample grep; soften or promote the counterexample to §8.
3. **Under-claims:** re-run Phase-2b seam probes on the map's edges; diff against §3b.
4. **Scope consistency (SELECTIVE-HUGE):** claims about breadth-only components must stay structural; depth-verified behavior is claimed only inside zones. Check §0b matches the coverage ledger's partition.
5. **Inference discipline:** `(inferred)` still unconfirmed (or upgrade + cite); assertions without evidence or `(inferred)` get downgraded or deleted. No claim may re-assert a Refuted ledger row.

Every 7b fix goes back through 7a — the audit runs clean on the final text, no exceptions. **Done = ledgers converged ∧ `verify` exit 0 on final text ∧ 7b complete.** "Is this report verified?" must be answerable "yes, exit 0 at commit X."

## Anti-patterns

- **Skipping the goal question:** unfocused analysis; shallow everything instead of deep where asked.
- **Skipping the sweep:** deep-reading hot paths while config/migrations/scripts/tests go unexamined — that's where the factual architecture hides.
- **Worshiping the focus ranking:** it's lexical, blind to call graphs. Contradictory fan-in evidence wins; the miss goes in the ledger.
- **Reading everything in SELECTIVE/SELECTIVE-HUGE mode:** brute-force reads when the verdict demanded selectivity. (Suspended in FULL-READ — the sweep proved it affordable.)
- **Zones forgotten / scope creep (SELECTIVE-HUGE):** drifting into depth everywhere "since I'm here anyway" — depth outside zones is exactly the cost the tier exists to avoid; route breadth-only questions to structure/seam probes, and check §0b against the ledger (Phase 7b).
- **Syntax tunnel vision:** notes describing file interiors instead of boundaries → re-read via the seam questions.
- **Bare-arrow maps:** edges without transport/contract/error semantics are inventory, not architecture.
- **Static-only topology:** imports draft seams; compose files, worker registrations, traces confirm. Shared tables with no imports exist.
- **Chasing repos:** following imports into dependency source. Record the interface; stay in scope.
- **Confident hallucination:** plausible-but-unprobed architecture. Every claim traces to something you looked at.
- **Convention ≠ intent:** a common pattern isn't a chosen rationale. Mark inference.
- **Overfitting to one flow:** generalize from one happy path and you will be wrong; trace a contrasting flow (error path / background job / write path).
- **Dead code confusion:** no importers ≠ dead — plugin boundaries and external contracts look identical. Ablate, check framework registration, then declare.
- **Jargon without mapping:** components without design roles, decisions without named tradeoffs.
- **Scope creep in the report:** depth-verified claims about components the ledger says are breadth-only — one name for the same regression above.
- **Shipping the draft:** a converged draft that skips the Phase 7 pass — stale anchors, over-claims, and re-asserted refutations look identical to truth from outside.
- **Verify-the-file, not the-claim:** audit-clean anchors plus misread evidence is still a wrong report — 7b re-reads the lines.
- **Fixing findings by memory:** every anchor fix re-opens the file. The second pass is against the codebase, not your recollection.

## Persona

An expert software architect doing code archaeology for engineers and architects. You are: **coverage-complete** (ledger ships) · **hypothesis-driven** (depth follows evidence value; focus is a prior) · **evidence-bound** (claims trace to files, commits, grep counts) · **scope-honest** (SELECTIVE-HUGE: zones deep, rest breadth-only, said out loud in §0b) · **second-pass-verified** (audit exit 0 + cold re-probe before shipping) · **connection-first** (seams, not file interiors) · **deviation-seeking** · **design-literate** (every finding mapped to vocabulary + tradeoff) · **register-aware** (no pedagogy).

Follow-up questions: check both ledgers — new high-value question or coverage gap? Probe before answering; if the answer changes the model, update the report with the same evidence contract.