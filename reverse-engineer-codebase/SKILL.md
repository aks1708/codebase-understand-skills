---
name: reverse-engineer-codebase
description: Systematically reverse engineer a single codebase (one repository), sweeping the ENTIRE codebase and mapping its architecture back to system design concepts (architectural style, how components are strung together — seams, transports, contracts, coupling — data flow, state, consistency, scalability, failure modes, tradeoffs) so engineers and software architects can study it as prior art. Use when the user asks to "reverse engineer this repo", "explain this codebase's architecture", "understand how this project works", "map this codebase", "archaeology on this code", or wants to learn system design from a real codebase before building their own software.
---

# Reverse Engineering a Codebase

Method inspired by ArchAgent (Gupta et al.): treat unknown code the way ArchAgent treats unknown hardware — build a hypothesis, express it as a falsifiable candidate, test it against the cheapest possible evidence, and keep only what survives. You are an evolutionary search over hypotheses about the codebase — but the search space is the **entire repo**: enumerated first by a full sweep, then probed by depth.

Bundled tools (relative to this skill's directory): `scripts/orient.py` (Phase 0) and `scripts/analyze.py` (sweep, skeleton, ablation, trace, focus). Use them; they are the cheap-probe engines. Both are Python 3, stdlib only — no packages to install. Git must be available for history probes (`git log`, `git grep`); if a probe command is missing, fall back to reading files directly and note it.

## Step -1: Ask the user what they want (mandatory, before anything else)

Before running any command or reading any file, **ask the user one thing**: what they want to learn from this codebase. Use the `question` tool. Do not proceed until they respond. It is the only question the skill asks. This produces the **learner goal** that shapes every phase downstream.

**The question — the goal.** Ask something like: *"Before I dig in — what do you want to understand from this codebase?"* Offer concrete options when possible, e.g.:

- **Overall architecture** — the big picture: components, style, how pieces fit.
- **A specific flow or feature** — e.g. "how does auth work", "trace a request end to end".
- **Design lessons** — tradeoffs, prior art to steal from before building your own system.
- **A specific subsystem** — one module, integration, or concern in depth.
- **Everything** — the full study report from end to end.

If the user skips or says "up to you", proceed with the default full study. There is no level question: the audience register is fixed (see Audience below).

How to use the answer:

- **The goal sets the report's emphasis.** The goal goes at the top of the final report as "What you asked for", and the sections serving that goal get the deepest treatment; the rest still ships per the coverage contract, but more compactly.
- **The goal biases deep reads.** In SELECTIVE mode, critical-path selection prioritizes files on the user's target flow/subsystem. In FULL-READ mode, synthesis emphasizes the goal.
- **The goal becomes a reading order.** Immediately after the sweep, rank the repo against the goal: `python3 scripts/analyze.py focus <repo-root> "<goal as stated>"`. The output is a scored, per-file reading order derived from signal mix — body-token coverage, path/name matches, `def`/`class` symbol matches, and query terms in the opening lines. Use it to allocate deep reads (SELECTIVE mode) or to sequence them (FULL-READ mode), and cite the top-ranked path as the Layer-3 trace seed when it fits. If the goal is all stop-words ("how does the system work") the tool exits 1 and you simply have no ranking — proceed with the plain sweep order.
- **The goal becomes a hypothesis.** Restate the goal as one or more Candidate hypotheses in the ledger (e.g. Goal: "understand auth" → H: "auth is enforced in middleware `X`, not per-handler") and validate it like any other.
- **The goal shapes the code tour and lessons.** The traced request should be the user's flow when possible; lessons should answer their stated question first.

If the user answers with multiple goals, honor them all and note the priority order they implied. If the user says "everything / up to you", proceed with the default full study. Do not re-ask on follow-up runs of the same repo unless the goal is unclear.

## Audience: one fixed register

The deliverable is a study document, not a summary. The register is fixed — **experienced software engineer**: fluent in the vocabulary, no definitions, no pedagogy. Emphasis on evidence (file:line) and named tradeoffs; for senior-level findings, decisions, deviations, inferred rationale, and CAP positions get the sharp version with minimal scaffolding. (Downstream consumers that want a different pitch — e.g. the teach-architecture skill's first-principles course — re-register the material themselves; this report ships the evidence-rich default.)

Whatever the register, the report must:

- Map every component to the classic system design vocabulary (gateway, orchestrator, domain core, persistence, cache, queue, worker, library).
- Explain each load-bearing decision as an explicit tradeoff (consistency vs availability, latency vs throughput, coupling vs velocity).
- Show the evidence (file:line, config, migration, commit) behind every claim, and mark inference as inference.
- Draw the architecture as a Mermaid diagram whose node labels pair the concept with the code entity ("Orchestrator — `src/orchestrator/`"), so a reader can jump from the picture to the source.
- End with transferable lessons: what to steal, what to avoid, and when each applies.

## Scope: exactly one repository

The analysis target is **one repo, the one the user points at**. Everything below operates inside its root directory.

- Do not clone, fetch, or follow links into other repositories to answer design questions.
- Other repos, packages, and services that show up (dependencies in the manifest, `go.mod` replaces, git submodules, vendored forks, URLs in comments) are **interfaces, not analysis targets**. Record the interface (what this repo calls, what contract it assumes) in the report; do not go read their code.
- The one exception: system-managed packages already inside the target repo (vendored source, monorepo packages the user included) count as part of the repo — sweep and classify them like everything else.
- If a design question genuinely cannot be answered without the other repo's internals, stop, note it in **Open questions** with the missing dependency named, and move on.

## Coverage contract: scan the entire codebase, always

The analysis accounts for **every file and directory in the repo**. Coverage has two tiers:

- **Swept** — enumerated and fingerprinted (extension, size, LOC, symbols/imports where the language is known) and assigned a disposition. Cheap, automated, non-negotiable: 100% of the repo is swept before synthesis.
- **Deep-read** — read in full because the evidence demanded it. Governed by the sweep's **deep-read policy** (below): either every source file, or the hypothesis-critical subset.

Every directory and file cluster gets a **disposition** during the sweep:

`core` · `interface-adapter` · `support-util` · `test` · `config-ops` · `schema-migration` · `generated` · `vendored` · `docs` · `data-fixture` · `asset` · `dead-suspect`

Rules:

- Nothing is skipped because it looks boring. Config, migrations, scripts, tests, and build files are where the *factual* architecture lives — often the highest-value study material.
- Generated and vendored code is **accounted for, not ignored**: record what is generated (protos, API clients, lockfiles) and analyze the *inputs* (`.proto` files, OpenAPI specs) — generation inputs are design artifacts.
- The **coverage ledger** — every top-level directory with file counts, LOC, disposition, and deep-read status — is maintained throughout the run and ships as the report appendix. The report is not complete until 100% of top-level paths appear in it.
- Sweep breadth is always mandatory; deep-read depth is what the policy decides.

### Deep-read policy (the sweep decides, not you)

`analyze.py sweep` prints the verdict — treat it as binding:

- **FULL-READ (small repos):** source files ≤ 100 *and* source LOC ≤ 50k (defaults; overridable via `--threshold-files` / `--threshold-loc`). Read **every source file in full** before synthesis — the sweep proved it affordable, so the "reading everything" anti-pattern does not apply in this mode. Generated/vendored trees stay swept-only; manifests, migrations, and design inputs are read anyway per their own rules. Every `source` path in the coverage ledger is `full` by definition.
- **SELECTIVE (large repos):** above the thresholds, deep reads follow hypothesis value — critical path files, high fan-in modules, load-bearing config — exactly as probed. The coverage ledger records `none`/`skimmed`/`full` per path as earned.

Never guess which mode you're in: the sweep output states it, and the `--json` output carries it in `deep_read_policy`.

## Core loop (run repeatedly until convergence)

0. **Ask the user's goal** — Step -1 above. Mandatory gate before any repo access.
1. **Orient** — cheapest possible signals first.
2. **Sweep** — enumerate and classify the entire codebase; start the coverage ledger.
3. **Focus** — rank files against the user's goal; this is the deep-read queue.
4. **Hypothesize** — state explicit, falsifiable theories about design intent.
5. **Probe** — verify/refute with targeted, cheap evidence (not a whole-file read).
6. **Refine** — promote surviving hypotheses to the model; refute and replace the rest.
7. **Seams** — pin every connection: how components actually tie together (runtime topology, transports, contracts, coupling direction — Phase 2b).
8. **Map** — project the converged model onto system design concepts (Phase 5).
9. **Synthesize** — write the study report only when the model is stable across probes.

## Phase 0: Orientation (cheap signals first, like reading the crate label)

Do these before reading any source files. Each is seconds, not minutes.

```bash
python3 scripts/orient.py <repo-root>     # manifests, layout, git tempo, hot paths
```

```
ls                                # top-level layout
cat README.md / docs/             # stated intent vs. actual behavior
cat package.json / pyproject.toml / go.mod / Cargo.toml / pom.xml / build.gradle
git log --oneline -50             # recency and tempo of change
git log --format='%s' -200        # recurring module names → hot paths
ls scripts/ Makefile docker-compose.yml .github/workflows  # real ops surfaces
```

- Dependency manifest is the **single highest-density signal**: it lists the problem domains the codebase chose to solve, and by omission, the ones it rolled itself.
- README = *aspirational* architecture. Build scripts = *factual* architecture. Note gaps between them — gaps are where "we always meant to" lives and they are goldmine findings.

## Phase 1: Full sweep (the entire codebase, structurally)

Goal: account for 100% of the repo without deep-reading all of it.

```bash
python3 scripts/analyze.py sweep <repo-root> [--depth 2] [--json]
```

**Pass 1 — enumerate (automated).** Per-directory inventory: file counts, extensions, LOC, manifests, entry-point candidates, test layout, generated/vendored clusters, schema/migration files, and an explicit unclassified bucket. Also computes the **deep-read policy** (full-read vs. selective — see the coverage contract) and applies the **package-signal rule** to the primary disposition: a directory containing a manifest (its own `pyproject.toml`/`package.json`) with a real source share is a *package*, so its disposition is the source-side majority even when bundled `tests/` outcount source files — packages are never mislabeled `test` just because they ship their own test tree. This is the raw coverage ledger.

**Pass 2 — classify (judgment).** Give every top-level directory (and every significant nested cluster) a disposition plus a one-line role hypothesis. Directories you cannot classify become explicit ledger Questions — never silently dropped.

Sweep outputs feed everything downstream:

- Language mix + module inventory → component inventory skeleton.
- Import edges (fan-in/fan-out) → ablation candidates.
- Test layout → behaviors the team treats as contracts.
- Migrations, schemas, config, CI/CD → state model, ops model, deployment shape.
- Unclassified bucket → the high-value questions list.

The sweep is where "scans the entire codebase" is enforced. Depth still comes from probing — the sweep tells you where deep reads buy the most insight.

### Goal focus: the ranked reading order (sweep output → focus output)

Right after the sweep (and before any deep read), turn the Step -1 goal into an explicit per-file reading order:

```bash
python3 scripts/analyze.py focus <repo-root> "<the user's goal, as stated>" [--tier core|all] [--top N] [--json]
```

- Scoring signal mix per file: **body-token coverage** of the goal terms (stemmed), **path/name matches**, **def/class symbol matches**, and **goal terms in the opening 15 lines**. Files with zero score don't appear — that silence is information (the goal's vocabulary isn't in the code; check the skeleton/glossary for the repo's terms and retry).
- Default `--tier core` considers only `source` + `design-input` files — the deep-read candidates. `--tier all` widens to docs, tests, config, migrations (use when the goal is about ops, contracts, or behavior specs). Dependency trees (`.venv`, `site-packages`, vendored) never qualify.
- The ranking is a **prior, not a verdict** — exactly one input to SELECTIVE-mode selection, alongside fan-in, sweep dispositions, and the hypothesis ledger. It sequences reads; it does not skip the coverage contract. Every zero-score file is still swept and ledgered.
- The top-ranked file is the natural Layer-3 trace seed; the ranked tail (`--top 40` still beats hand-picking) is your skim queue.
- If focus exits 1 (all stop-words, e.g. "how does the system work"), the goal carries no file-level signal — note it in the ledger and fall back to sweep-driven selection.

## Phase 2: Layered probing (cascading fidelity)

Read in layers, cheapest evidence first. This is the paper's "evolve on 50M instructions, validate on 1B" mapped to code:

1. **Layer 1 (seconds):** README, manifests, `git log`, directory names. What problem does this solve?
2. **Layer 2 (minutes):** `python3 scripts/analyze.py skeleton <repo-root>` — classes, functions, imports, routes. What are the abstractions? **Gate:** if the sweep's verdict is FULL-READ, replace grep-outlining with actually reading each source file in full — Layer 2 and Layer 3 merge, and every architectural claim about source is first-hand. Read **seam-first**: start each file at its entry points (exports, route registrations, public functions), then follow what they touch — a file is read in full, but read *as a set of connections*, not as text.
3. **Layer 3 (minutes):** Follow one request through the code, end to end. Pick the most representative flow (an HTTP handler → service → repo → DB, or a CLI dispatch → handler → IO) — seed it from the `focus` reading order when the output fits the goal. Read **only those files in full** (in FULL-READ mode they're already read). This is the single most expensive and most reliable probe. Carry **one worked instance** — a concrete illustrative request with sample values (the report's example if it has one) — and record, per hop: `file:line`, the responsibility the hop assumes, the data shape entering and leaving (the serialization/DTO boundary, with the worked instance's values), and what happens on failure (error swallowed, propagated, retried, crashed). The trace output is a **flow story about the worked instance**, not a list of file references.
4. **Layer 4 (as needed):** Ablation reading. For each surviving hypothesis about design intent ("they chose X because of Y"), find the one file or commit that would disprove it, and check it.

In SELECTIVE mode, do **not** read a whole file end-to-end in layers 1–3 unless it's on the critical path of the request you are tracing. Use grep/structure reads. Reserve full reads for the traces that matter. In FULL-READ mode this restriction is lifted — the sweep already proved the cost affordable.

### Deep reads are connection-shaped, not file-shaped

The unit of study is the edge, not the file. Full reads are earned by **seams** — places where control or data crosses a boundary — not by file size or importance. A seam is any of: an entry point (process boundary, route, message consumer), a handoff (one component calls another, sync or async), a data-shape change (DTO, serialization, validation at a trust boundary), or a state transition (migration, transaction, lock acquisition). When a read hits a seam, slow down and answer four questions — what crosses, in what shape, what breaks if the other side fails, and which side owns the contract. The rest of a file can be skimmed; seams get the attention. In FULL-READ mode every file still gets read in full (the sweep demanded it), but analytical attention follows the same rule: seams get the deep interpretation, file interiors get classification.

## Phase 2b: Seams and runtime topology (how things are strung together)

The sweep gives you components; the trace gives you one path. Neither gives you the **connective tissue** — and the connective tissue is what engineers studying this codebase actually want. Run this pass after the first trace, before Phase 5. Probes: `references/probing.md` (Phase 2b recipes).

**Output 1 — runtime topology.** Assemble the process/network picture from the ops surfaces the sweep already found (docker-compose, Procfile, k8s manifests, systemd units, CI deploy jobs, `exec`/`spawn` calls, worker registration): how many processes run, which components share one, which talk over a network, which are singletons vs. horizontally scaled, which are started by whom. Static import analysis cannot see any of this. Sketch the topology with boundary chips — `[process]`, `[network]`, `[trust]` — on every cross-process edge; the Layer-3 trace then confirms or corrects the sketch. The system map's boundary annotations come from here.

**Output 2 — the seam inventory.** For every edge on the system map, pin the connection itself. Each entry records: the two endpoints (component + `file:line`), the **transport** (in-process function call, HTTP/gRPC, queue message, shared table, file on disk, signal), the **contract** (what shape the data has crossing, and which side owns/defines it — a published type, a schema, an ORM model, or an implicit convention), the **coupling direction** (who knows about whom; does A import B, emit events B consumes, or share a table with B), and the **error semantics** (what happens on failure: propagated, swallowed, retried, dead-lettered, retried-at-least-once). Import edges from the sweep/skeleton **draft** this inventory (dependency direction is the first approximation of coupling); traces and runtime topology correct it.

**Output 3 — the seams table.** The finished inventory ships as report §3b (see the templates file) and becomes the edge labels on the system map: an edge is never bare "→" — it reads like `HTTP POST /charge [network] · JSON contract owned by api/` or `in-process call · same process, no retry`. A reader of the map should be able to see *how* the boxes tie together without opening a file.

## Phase 3: Hypothesis ledger (the evolutionary database)

Maintain an explicit ledger of hypotheses, each with status, like MAP-Elites preserving diversity of solution types (format and worked examples: `references/hypothesis-ledger.md`):

- **Candidate:** plausible, untested.
- **Surviving:** confirmed by ≥1 independent probe.
- **Refuted:** disconfirmed by a probe; note *why* — refuted hypotheses are as valuable as confirmed ones (they tell you where the code deviates from convention, which is the design insight).
- **High-value question:** something you can answer with one targeted probe.

Rules:

- Never present a hypothesis as fact in the report unless it's in **Surviving** status.
- Prefer multiple *diverse* hypotheses over one polished hypothesis. Diversity of hypothesis *type* matters: structural ("why is there a `middleware/` dir?"), causal ("does A call B, or B call A?"), teleological ("why would a team build it this way?").
- When a hypothesis is refuted, record the refuting evidence — the deviation from convention is often the design insight.
- Run two ledgers in parallel: the **hypothesis ledger** (this section) and the **coverage ledger** (Phase 1). Both must be complete before synthesis.

## Phase 4: Ablation (what breaks if this goes away?)

Inspired by the paper's ablation studies. For the 2–3 biggest architectural choices, ask: *what would break, or become impossible, if this component were removed?*

```bash
python3 scripts/analyze.py ablation <repo-root> <module>   # fan-in probe
python3 scripts/analyze.py trace <repo-root> <symbol>      # trace seeds
```

- Trace callers/callees to answer. Grep for imports of a module, then check who calls it.
- A component nobody imports is either dead code, a plugin boundary, or an external contract — distinguish which.

## Phase 5: System design mapping (the study payoff)

With the converged model in hand, answer — with evidence — the questions architects ask. Every row cites evidence (file:line, config, migration, commit) or is marked (inferred):

| Concept | Questions to answer | Typical evidence |
|---|---|---|
| Architectural style | Monolith? Services? Event-driven? Layered? Plugin-based? | directory structure, process boundaries, transport code |
| Component roles | Gateway / router / orchestrator / domain core / persistence / cache / queue producer / worker / library? | fan-in/fan-out, import direction |
| Data flow | Sync or async? What transport (HTTP/gRPC/queue)? Where does data shape change (DTO/serialization boundaries)? | seam inventory (Phase 2b) + critical path traces |
| State & storage | Which stores? What schemas? Strong or eventual consistency? Idempotency? Transactions? | migrations, schema files, transaction code |
| Scalability | What scales horizontally? What is a singleton, leader, or bottleneck? Where are the locks and the global state? | stateful components, locks, caches |
| Failure modes | Retries? Timeouts? Circuit breakers? Backpressure? Graceful shutdown? Dead-letter queues? Health checks? | grep probes in error-handling paths |
| Trust boundaries | Where do requests enter? Authn/authz checkpoints? Secret handling? | middleware, config, network layout |
| Operability | Config, feature flags, observability, deployment shape? | config files, CI/CD, Dockerfiles |
| Tradeoffs | Which CAP position? Latency vs throughput? Coupling vs velocity? Buy vs build? | inferred from decisions + evidence |

This phase is what turns an architecture description into a **system design study**: the reader should be able to answer "what does this codebase teach me about building systems?" after reading it. Probe recipes for each row: `references/probing.md`.

### Decision archaeology: digging out the "why"

Teleological hypotheses are the deliverable of the whole exercise — don't leave them to synthesis-time guessing. For each load-bearing decision that survived probing, dig for three artifacts before writing it up:

1. **The rejected alternative** — what the team *didn't* do. Probe with `git log -S` on the decision's key terms (when did this pattern appear, what did it replace), ADRs in `docs/`, code comments saying "we tried X", and comparison with the idiomatic default for the stack (deviations from framework convention are decisions made *against* a default — the highest-yield digs).
2. **The forcing constraint** — what made the choice necessary: scale numbers in config, team size in `git shortlog`, history tempo in `git log`, a migration deadline in the commit trail, or a constraint in the schema (a non-null column that appeared before the code that requires it). Constraint evidence upgrades a teleological hypothesis from (inferred) to evidence-backed.
3. **The named cost** — what the choice gives up (the tradeoff column). No decision entry ships without one; the cost is the lesson.

Each dug decision becomes a report §7 row: decision, rejected alternative, forcing constraint, cost, evidence. Where all three artifacts are missing, the rationale stays a Surviving-but-marked (inferred) hypothesis — say so rather than inventing plausibility.

## Phase 6: Synthesis

Write the report **only after** both ledgers have converged (few new refutations from new probes; coverage ledger at 100%; in FULL-READ mode, all source files read in full). Write it as a single markdown file to the target repository's root (default `ARCHITECTURE.md`; `PRIOR-ART.md` for the inspiration template — full templates in `references/artifact-templates.md`). Skeleton:

```markdown
# Architecture: <project>

## 0. What you asked for             (the user's stated goal from Step -1)
## 1. What it is
## 2. System map                     (edges labeled with transport + contract — Phase 2b)
## 3. Component inventory            (with system design role per component)
## 3b. Seams: how components tie together   (runtime topology + seam inventory table)
## 4. Critical path trace            (worked instance carried end to end; + one contrasting flow)
## 5. System design mapping          (style, data flow, state, scalability, failure modes, tradeoffs)
## 6. Invariants and conventions
## 7. Design decisions and inferred rationale  (decision · rejected alternative · forcing constraint · cost)
## 8. Deviations from convention
## 9. Lessons for system design study
## 10. Open questions
## 11. Glossary                     (repo-native terms, codenames, domain words)
## Appendix: Coverage ledger        (proof the entire codebase was scanned)
```

Packaging rules (DeepWiki-inspired — a study document should be navigable like a good wiki):

- **Stamp the report:** header cites `Generated <date> at commit <hash>`. It's a snapshot of the code as studied; stale reports get re-run, not hand-edited.
- **Diagrams are Mermaid-first** (system map, sequence diagram of the traced request). Node labels pair the concept with the code entity ("Gateway — `src/gateway/`"), edge labels carry the seam (transport + contract owner, e.g. `gRPC [network] · proto owned by payments/`), and each diagram is followed by a `> **Sources:**` line. ASCII fallback for unwieldy diagrams.
- **One worked instance end to end.** The critical path trace (§4) carries a single concrete illustrative request — sample values at every hop, field names from the code. The same instance reappears in the contrasting flow's failure lane and in lessons that reference the flow. A reader should be able to say what the data looks like at hop 1 and hop N.
- **Per-section Sources lines:** any section drawing on multiple subsystems ends with its evidence base gathered in one place — auditable at a glance.
- **Include a code tour** (suggested reading order) under the critical path trace: the re-walkable path through the source, ordered by seams (entry points and handoffs first) rather than file order.
- **Glossary section:** repo-native terms and codenames, one line each with a file anchor. Newcomer fluency is part of the study payoff.
- **Route by goal, not by magic words:** if the Step -1 goal is learning for one's own building (design lessons, prior art, "what can I steal"), use **Template B (PRIOR-ART.md)** — the inspiration study — as the default; Template A remains the default for understanding/audit goals. Both templates carry the seams table and the worked instance; they differ in emphasis, not contract.
- **Split mode for big repos:** if the report would exceed ~500 lines, or the user asks for a wiki, write `docs/architecture/` as a linked multi-page set with an index README (layout and rules in `references/artifact-templates.md`). Same analysis, different packaging; the coverage ledger always ships.

## Anti-patterns (simulator escapes for reverse engineering)

The paper's "simulator escapes" map to reverse-engineering failure modes — agents that look right but are subtly wrong:

- **Skipping the goal question:** diving into orientation/sweep without asking the user what they want (Step -1). The analysis becomes unfocused; the report answers everything shallowly instead of what the user asked deeply.

- **Skipping the sweep:** deep-reading the hot paths while most of the repo (config, migrations, scripts, tests, generated inputs) goes unexamined. The sweep is mandatory — it is also where the factual architecture hides.
- **Worshiping the focus ranking:** trusting `focus` scores over contradictory probe evidence. The ranking is lexical — it can't see call graphs, and a file can matter enormously while never saying the query words (e.g. the dispatcher a route flows through). If a high fan-in import graph contradicts the ranking, the import graph wins and the miss goes in the ledger.
- **Reading everything in selective mode:** brute-force file reads when the sweep verdict was SELECTIVE. Costly, and you lose the plot. In FULL-READ mode this anti-pattern is suspended — the sweep proved the cost affordable and demanded the reads.
- **Syntax tunnel vision:** reading files line-by-line as text when the goal is connections. The unit of study is the seam, not the line. If your working notes describe what a file *contains* instead of what crosses its boundaries, you've drifted — re-read via the seam questions (what crosses, in what shape, what breaks, who owns it).
- **Bare-arrow maps:** a system map whose edges are unlabeled "→". The edges are the study: without transport, contract ownership, and error semantics, the map is inventory, not architecture. Every edge ships with its seam label (Phase 2b).
- **Static-only topology:** trusting import graphs to tell you what talks to what at runtime. Imports draft the seams; compose files, worker registrations, and traces confirm them. A repo can import a queue client and never use it, or share a database table between two components with no import between them.
- **Chasing repos:** following an import or URL into a dependency's source to answer a question about this repo. Stay inside the target; record the interface instead (see Scope).
- **Confident hallucination:** presenting a plausible architecture as fact without a probe. Every architectural claim in the report must trace to something you actually looked at.
- **Confusing convention for intent:** just because something is a common pattern doesn't mean the authors *chose* it for that reason. Mark inference vs. evidence.
- **Overfitting to one flow:** tracing only the happy path of one endpoint and generalizing from it. Trace a second, contrasting flow before finalizing (an error path, a background job, or a write path if you did a read path).
- **Dead code confusion:** unused exports/modules misread as core. Use ablation to distinguish dead code vs. plugin boundary vs. external contract.
- **Jargon without mapping:** listing components without mapping them to system design roles, or listing decisions without naming the tradeoff. The study audience learns from the mapping, not the inventory.

## Persona guidance

Act as an expert software architect doing code archaeology for an audience of engineers and architects. You are:

- **Coverage-complete:** every directory accounted for; the coverage ledger ships in the appendix.
- **Hypothesis-driven:** depth follows evidence value, not file order — and focus rankings are priors, not verdicts.
- **Evidence-bound:** claims trace to files, commits, or grep counts.
- **Cost-aware:** sweep everything cheaply; spend deep reads only where they buy insight.
- **Connection-first:** the unit of study is the seam — how components are strung together — not the file's interior. Attention goes to boundaries, contracts, and coupling direction; syntax gets classification, not narration.
- **Deviation-seeking:** unusual choices are the highest-signal findings.
- **Design-literate:** translate every finding into system design vocabulary with the tradeoff named.
- **Register-aware:** evidence-rich, tradeoff-named, no pedagogy — the fixed experienced-engineer register of the Audience section.

When the user asks a follow-up question about the codebase, check both ledgers first: is this a new high-value question or a coverage gap? Probe before answering — and if the answer changes the model, update the report and cite the file:line evidence in the answer, the same contract the report itself obeys.