# Artifact templates

## Contents
- Template A: Architecture + system design study
- Template B: Inspiration / prior-art study
- Notes on writing quality
- DeepWiki-style multi-file wiki (split mode)

The final deliverable is a single markdown report written to the analyzed repository's root (unless the user picks a different path). Pick one template for the whole file — do not mix them.

Two output templates. Route by the user's Step -1 goal, not by magic words: if the goal is learning for one's own building (design lessons, prior art, "what can I steal"), **Template B is the default**; for understanding/audit goals ("what is this", "how does it work", onboarding), Template A is the default. The user can always override. Pick one template for the whole file — do not mix them.

Both templates carry the same contracts regardless of emphasis: the coverage ledger appendix, the seams table (how components tie together — transports, contracts, coupling direction, error semantics), and one worked instance carried through the critical path. They differ in what they foreground, not in rigor.

The reader is an **engineer or software architect studying prior art**. Both templates must read as study documents: claims cite evidence, findings map to system design vocabulary, tradeoffs are named, and the coverage ledger proves the whole repo was scanned.

---

## Template A: Architecture + system design study

```markdown
# Architecture: <project name>

> Generated <date> at commit <short-hash on <branch>>. Method: full sweep + hypothesis-driven layered probing (see SKILL.md). A study doc, not live tooling — re-run to refresh.
> Audience: engineers and architects studying prior art.
> Claims marked (inferred) are unconfirmed reasoning; all other claims trace to evidence.

## 1. What it is
<One paragraph, plain language. Written from surviving hypotheses only.>

## 2. System map
<Mermaid diagram (falls back to ASCII when it would exceed ~30 lines): major
components, arrows = data/control flow. Node labels pair the concept with the
code entity ("Orchestrator — `api/workflows.py`"). Edge labels carry the seam:
transport + contract owner + boundary chip, e.g. "gRPC [network] · proto owned
by payments/", never a bare "→". Mark the boundaries (process, network, trust)
you observed. End the section with a Sources line.>
> **Sources:** `file:line` citations backing the diagram.

## 2b. Critical-path diagrams
<Mermaid sequenceDiagram for the Layer-3 trace; a flowchart for the one
contrasting flow (error path / background job / write path). Every section
that makes architectural claims carries its own Sources line.>

## 3. Component inventory
| Component | System design role | Responsibility | Key files | Why it exists |
|---|---|---|---|---|
<System design role: gateway / orchestrator / domain core / persistence /
cache / queue producer / worker / library / adapter. Why it exists = the
surviving teleological hypothesis, in one phrase.>

## 3b. Seams: how components tie together
<The connective tissue — the section a system designer reads first.>
**Runtime topology:** <one paragraph or small diagram: how many processes,
which components share one, which talk over a network, singletons vs.
horizontally scaled, started by whom. Boundary chips [process]/[network]/
[trust] on every cross-process edge. Evidence: compose files, Procfile,
k8s, worker registrations, deploy jobs.>

| Edge | Transport | Contract (shape · owner) | Coupling direction | Error semantics |
|---|---|---|---|---|
<One row per edge on the system map. Transport: in-process call / HTTP /
gRPC / queue message / shared table / file. Contract: the data shape that
crosses and which side owns/defines it (published type, schema, ORM model,
or implicit convention — say which). Coupling direction: who knows about
whom. Error semantics: propagated / swallowed / retried / dead-lettered /
crash. Every row cites file:line for both endpoints.>

## 4. Critical path trace
<Walkthrough of the representative request/flow as a FLOW STORY about one
worked instance — a concrete illustrative request (e.g. "POST /charge for
$42.00, user 123") carried end to end, file:line at each hop, plus per hop:
responsibility assumed, data shape entering/leaving (the worked instance's
values), failure behavior. The reader should know what the data looks like
at hop 1 and hop N. Include one contrasting flow (error path, background
job, or write path) and trace the same instance's fate on it.>

### 4b. Suggested reading order (code tour)
<Numbered list — the order a reader should open files to retrace the analysis
with least effort. 8-15 stops, one line each on what to notice. Ordered by
seams: entry points and handoffs first, not file order. This is the
guided-tour idea: the study doc should be re-walkable.>

## 5. System design mapping
<The study payoff — the questions architects ask, answered with evidence.>
- **Architectural style:** <monolith / services / event-driven / layered /
  plugin-based> — evidence: <dir structure, process boundaries, transports>
- **Data flow:** <sync/async, transports, DTO/serialization boundaries>
- **State & storage:** <stores, schemas, consistency model, idempotency,
  transactions> — evidence: <migrations, schema files, transaction code>
- **Scalability:** <what scales horizontally, singletons/leaders/bottlenecks,
  locks and global state>
- **Failure modes:** <retries, timeouts, circuit breakers, backpressure,
  graceful shutdown, DLQs, health checks>
- **Trust boundaries:** <entry points, authn/authz checkpoints, secrets>
- **Operability:** <config, feature flags, observability, deployment shape>
- **Tradeoffs:** <CAP position, latency vs throughput, coupling vs velocity,
  buy vs build — each named explicitly>

## 6. Invariants and conventions
<Patterns held everywhere: error handling style, config access, naming, logging,
testing layout. Each with a representative file:line citation.>

## 7. Design decisions and inferred rationale
| Decision | Rejected alternative | Forcing constraint | Tradeoff named | Rationale | Evidence |
|---|---|---|---|---|---|
<One row per load-bearing decision, dug via decision archaeology:
rejected alternative = what the team didn't do (git log -S, ADRs, deviation
from stack-idiomatic default); forcing constraint = what made the choice
necessary (scale, team size, schema, history); tradeoff named = what this
choice costs (e.g. "AP: accepts stale reads"). Rationale marked (inferred)
where no commit/comment evidence exists — dig for the alternative and the
constraint before settling for (inferred).>

## 8. Deviations from convention
<Where the codebase is unusual. For each: what's unusual, why it matters,
evidence or (inferred) reasoning. These are the highest-insight findings.>

## 9. Lessons for system design study
<For architects: what this codebase teaches. Each lesson: the system design
problem it addresses, when to apply it, when NOT to, and the evidence.>

## 10. Open questions
<Unconfirmed items, each with the probe that would answer it.>

## 11. Glossary
<Terms the repo itself uses — domain words, codenames, idiosyncratic component
names — with one-line definitions and a file:line anchor each. A reader who
joins this team tomorrow should be fluent after this section.>

## Appendix: Coverage ledger
<Proof the entire codebase was scanned. Table: path, file count, LOC,
disposition (core / interface-adapter / support-util / test / config-ops /
schema-migration / generated / vendored / docs / data-fixture / asset /
dead-suspect), deep-read status, note. Every top-level path appears; the
unclassified bucket is empty or justified. Source: `analyze.py sweep`.
State the sweep's deep-read policy verdict: in FULL-READ mode (small repos)
every source path shows `full`; in SELECTIVE mode the column records what
each path earned.>
```

---

## Template B: Inspiration / prior-art study

For when the goal is "what can I steal from this?" rather than "what is this?"

```markdown
# Prior-art study: <project name>

## The problem it really solves
<Strip away the marketing. From the dependency manifest + code, what domains
does this actually address, and which did it deliberately not?>

## Architecture in one diagram
<Mermaid diagram (ASCII fallback) with the 3-5 load-bearing components, labeled
with system design roles (gateway / orchestrator / domain core / persistence /
queue / worker). Node labels pair role with code entity; edge labels carry the
seam (transport + contract owner), never a bare "→". Add a Sources line.>

## How it ties together
<Compact seams treatment for the inspiration reader: runtime topology in one
paragraph (processes, network edges, singletons), then the seams table in the
§3b format (see Template A) — one row per edge on the diagram: transport,
contract owner, coupling direction, error semantics. Patterns worth stealing
live at these edges; a steal card that references a seam cites it.>

## Patterns worth stealing
### <Pattern name>
- **Where it appears:** file:line (2-3 examples)
- **System design problem it solves:** <one sentence, in architect vocabulary>
- **Mechanism:** <how it works, briefly, with a minimal code sketch — anchored
  to the worked instance's values where the pattern sits on the traced flow>
- **Cost / tradeoff:** <what it makes harder — nothing is free>
- **Steal when:** <conditions in your own project that make it a fit>
- **Reject when:** <conditions that make it a liability>

(repeat 3-7 times, ordered by transferability. If the analysis includes a
worked-instance trace, reuse its values verbatim in mechanism sketches — the
reader who followed "$42.00" through the flow should meet it again here.)

## Anti-patterns to avoid
<Things this codebase does that you should NOT copy — even if they look
attractive. Accidental complexity, premature abstraction, dead abstractions.>

## The one big idea
<If you could take exactly one insight from this codebase, what is it?
One paragraph. This is the payoff of the whole exercise.>

## Open questions
<What you couldn't determine, and the probe that would resolve it.>

## Appendix: Coverage ledger
<Same contract as Template A: full-sweep table, 100% of paths accounted for,
with the deep-read policy verdict stated (FULL-READ: all source paths `full`;
SELECTIVE: earned per path).>
```

---

## Notes on writing quality

- **Every architecture claim cites evidence** (file:line, commit, grep count) unless explicitly marked (inferred). This is the report's anti-hallucination contract.
- **The critical path trace is the heart of Template A.** A reader who follows it should be able to retrace the flow themselves without re-doing the analysis. It is a flow story about one worked instance with values at every hop — not a list of file references.
- **The seams table is what makes it a wiring study, not a parts catalog.** Component inventory says what the boxes are; the seams table says how they are strung together — transport, contract owner, coupling direction, error semantics per edge. A system designer reads §3b first.
- **The system design mapping is what makes it a study document.** Component names without roles and decisions without tradeoffs are inventory, not insight.
- **"Deviations from convention" is the highest-insight section.** Convention = what any competent team would do; deviation = what *this* team knew that others don't (or a mistake — the distinction goes in the evidence column).
- **"The one big idea" is the payoff of Template B.** If you can't write it, the analysis hasn't converged yet — go back to probing.
- **The coverage ledger is the trust anchor.** If a top-level path is missing from the appendix, the report is incomplete by definition.
- Don't pad. A converged 6-page artifact with full coverage beats a 20-page summary of file listings.
- Diagrams: prefer Mermaid (graph, sequenceDiagram) rendered from the design mapping; fall back to ASCII when the diagram would be unwieldy. Keep them under ~30 lines. Arrows labeled with the seam ("fetches via gRPC [network] · proto owned by payments/"), never bare "→". Every nontrivial diagram is followed by a Sources line.
- **Per-section Sources lines** (DeepWiki's citation habit): any section whose claims span multiple subsystems ends with a `> **Sources:** ...` line gathering its file:line citations. Inline citations stay inline; the Sources line inoculates against confident hallucination by making a section's evidence base auditable at a glance.
- A report older than the current HEAD is a snapshot — that's fine, but the header says so; users re-run the skill rather than hand-editing a stale artifact.

---

# DeepWiki-style multi-file wiki (split mode)

Use when the codebase is large enough that a single ARCHITECTURE.md (or PRIOR-ART.md) would exceed ~500 lines, or when the user asks for a "wiki". Same run, same ledgers — only packaging differs; the default running order below maps Template A's sections and adapts for Template B.

```
docs/architecture/      (or wiki/, user's choice)
├── README.md           ← report index: table of contents with one-line
│                         summaries, links to each page, generated <date>@<commit>
├── 1-what-it-is.md     ← §1 + system map + diagrams
├── 2-components.md     ← component inventory + seams table (§3b) + ablation findings
├── 3-critical-path.md  ← worked-instance trace + contrasting flow + code tour
├── 4-design-study.md   ← system design mapping + decisions + tradeoffs
├── 5-lessons.md        ← deviations + lessons + open questions
└── glossary.md         ← shared glossary (single source of truth)
```

Rules:
- The running order above is a default, not a cage — subsections migrate between files to fit the repo (e.g. diagram types go in one file, deployment in another).
- The coverage ledger (full table) lives in `README.md` or its own file; it never gets dropped in split mode.
- Every cross-file reference is a relative link; each file opens by naming its scope.
- Recommended for repos over ~2-3k LOC; mandatory only by user request.