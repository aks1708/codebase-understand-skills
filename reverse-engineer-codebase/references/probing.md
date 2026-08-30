# Probing Cookbook: sweep, language, and evidence recipes

## Contents
- Universal (git + grep probes)
- Phase 1: the full sweep (automated)
- Goal focus: the ranked reading order
- Working with framework-idiomatic code
- Entry point discovery
- Layer 2: structure without full reads
- Phase 2b: seams and runtime topology
- Data flow probes
- System design mapping probes (Phase 5)
- Decision archaeology: digging out the "why"
- Ablation probes
- Tracing one request end-to-end (the Layer 3 probe)
- Test directory as documentation
- Reading large files cheaply
- Phase 7: verifying the report against the codebase
- Selective-huge mode: deep zones + breadth-only (huge repos)

Cheap, targeted evidence-gathering commands. Layer 1/2/3 refers to the cascade in SKILL.md. The read-tier ladder: **skim**
(outline/first-pass), **analytical read** (full read with a written answer to a
named question — cheaper than full deep-read, stronger than skim; use in
SELECTIVE mode for hypothesis-critical files short of full-read tier), **full
deep-read** (the tiers the coverage ledger records). Full reads are earned by
**seams** — entry points, handoffs, data-shape changes, state transitions —
not by file size or importance: when a read hits a seam, slow down and answer
the seam's four questions (SKILL.md Phase 2); file interiors get
classification, not narration.

## Universal

```bash
git rev-parse --short HEAD && git branch --show-current   # report header stamp (date @ commit)
git log --oneline -30                       # recent activity
git log --format='%s' -200                  # theme of changes
git shortlog -sn                            # who wrote what (team signals)
git log -p --follow <file>                  # history and rationale of a file
git log --diff-filter=A -- <file>           # when a file was born
git grep -n "TODO\|FIXME\|HACK\|XXX"       # known pain points, admissions of debt
git grep -n "deprecated\|legacy\|migration\|v2\|compat" -i
ls -la scripts/ Makefile justfile docker-compose.yml .github/workflows
```

`git log -p --follow <file>` is the highest-value single probe for "why does this exist?" — commit messages plus diffs surface rationale that code cannot.

## Phase 1: the full sweep (automated)

```bash
# Full-repo coverage ledger: every file enumerated, tagged, LOC'd
python3 scripts/analyze.py sweep <repo-root> [--depth 2] [--json]

# Language census only (polyglot repos: know all the languages, not just the primary)
python3 scripts/analyze.py langs <repo-root>
```

Huge-repo flags: `--no-loc` fast enumeration (auto above 30k files — counts + tags at 100%, LOC skipped, size verdicts unavailable); `--loc` forces reads back on; `--threshold-huge-files/--threshold-huge-loc` (default 2,000 / 500k) set the selective-huge boundary, `0` disables the tier.

Read the sweep output as a map of study targets, in this order:

1. **Manifests + lockfiles** — the factual dependency tree and declared problem domains.
2. **Entry-point candidates + HTTP routes** — where flows begin; pick critical-path traces from here.
3. **Migrations / schema** — where the state model actually lives.
4. **CI / ops / deploy** — the real deployment shape (what runs where, what talks to what).
5. **Design inputs** (`.proto`, OpenAPI, GraphQL, Thrift) — machine-readable contracts; often the cleanest statement of the architecture.
6. **Generated / vendored clusters** — accounted for, inputs analyzed, outputs skipped.
7. **Unclassified bucket** — your first hypothesis-ledger Questions.

After the sweep, assign the study dispositions (`core`, `interface-adapter`, `support-util`, ...) to every top-level path — this is the judgment step that starts the coverage ledger (see `references/hypothesis-ledger.md`).

### Goal focus: the ranked reading order

The sweep answers "what exists"; `focus` answers "what matters *for this goal*". Run it right after the sweep, before spending any deep reads:

```bash
python3 scripts/analyze.py focus <repo-root> "<user's goal as stated>" [--tier core|all] [--top N] [--fast|--full] [--json]
```

Scoring, tiers, fast/full modes, and the prior-not-verdict rule are specified in SKILL.md Phase 1. Probing-specific notes:

- Zero-score files are omitted (silence = the vocabulary isn't there; re-check the repo's own terms via `skeleton` and retry with those).
- In FULL-READ mode it sequences reads so the user's goal is answered first even though everything gets read eventually.
- On follow-up questions, re-run focus with the follow-up as the query — it doubles as the "is this a new high-value question?" probe before you touch any file.

## Working with framework-idiomatic code

Modern web codebases organize by framework convention, not by system design vocabulary — Django, Rails, Next.js, NestJS, Spring. A black-box file like `app/layout.tsx` is an interface-adapter boundary, and `page.tsx` files are per-route entry points. When the sweep detects a framework (manifest + signature directories), run an idiom check so the ablation/trace layers don't misjudge convention-managed paths (DeepWiki does this implicitly via RAG over repo data):

- Django: `settings.py` (INSTALLED_APPS, middleware order), `urls.py` → view wiring (the routing table), `manage.py`.
- Rails: `config/routes.rb`, `config/application.rb`, `app/controllers/application_controller.rb` (the inheritance root).
- Next.js: `app/layout.tsx` + root `page.tsx` (framework-invoked black box = interface-adapter); API surface under `app/api/*/route.ts` or `pages/api/*`. `layout.tsx` often wires providers — treat as a composition root probe.
- NestJS: `app.module.ts` (DI graph root), `main.ts` (bootstrap), middleware/guard/interceptor registration.
- Spring: application class, `application.yml/properties`, `@Configuration` classes, component-scan roots.

Framework magic (implicit registration, DI, auto-discovery) is exactly where "no importers" ≠ dead code. Confirm the registration mechanism before any dead-suspect verdict.

## Entry point discovery

```bash
# Node / TS
cat package.json | jq '.main, .scripts, .workspaces, .dependencies'
grep -rn "require('.\../\|import .* from '\.\./" --include="*.ts" | head -20

# Python
cat pyproject.toml; rg "def main|if __name__|argparse|click.option"
grep -rn "^from \.\| ^import " --include="*.py" -h | sort | uniq -c | sort -rn | head

# Go
cat go.mod
rg "func main" --type go -l

# Rust
cat Cargo.toml
rg "fn main" --type rust -l

# Java
find . -name "*Application.java" -o -name "Main.java" -o -name "App.java"
cat pom.xml build.gradle* 2>/dev/null | grep -A2 "<dependencies>\|implementation "
```

`analyze.py sweep` also surfaces entry-point candidates by basename (`main`, `cli`, `app`, `index`, `server`, `manage`).

## Layer 2: structure without full reads

```bash
# Polyglot skeleton: classes, functions, imports, routes across ALL detected languages
python3 scripts/analyze.py skeleton <repo-root>

# Class/type skeleton (any single language)
rg "^(class|interface|struct|enum|trait|type) " -n

# Function signature listing (Python)
rg "^def |^    def " -n --no-heading | sort

# Public API surface
rg "^export (default )?(function|class|const)" --type ts -n

# Fan-in: who imports module X? (ablation probe)
rg "from .* <module>|import .* <module>" -l

# Fan-out: what does module X import?
rg "^import |^from " <module-dir> -h | sort -u
```

## Phase 2b: seams and runtime topology

The connective-tissue probes (SKILL.md Phase 2b). Import edges from the sweep/skeleton **draft** the seam inventory; these probes correct it with runtime evidence.

**Runtime topology — what actually runs:**

```bash
# Process composition: which components run in which process/container
cat docker-compose.yml docker-compose.*.yml 2>/dev/null
cat Procfile profile 2>/dev/null
ls k8s/ kubernetes/ helm/ charts/ deploy/ 2>/dev/null

# Who starts what, concurrency model
rg "exec\(|spawn|subprocess|fork|multiprocessing|tokio::spawn|go func|Worker|sidekiq|celery|bullmq|systemd" -i -l

# Singleton vs scaled: replica/worker counts in ops surfaces
rg "replicas|workers:|--concurrency|processes:|instances:" -i deploy/ k8s/ docker-compose* 2>/dev/null

# Cross-process communication: what talks over a network
rg "localhost:|127\.0\.0\.1|unix://|amqp://|redis://|kafka|DATABASE_URL|_URL|_HOST" -i --type-add 'ops:*.{yml,yaml,toml,env,conf}' -t ops -l
```

Read the compose/Procfile/k8s output as the process diagram: each service/entry is a process boundary `[process]`; each URL/port reference between them is a network edge `[network]`; each secret or external entry is a trust boundary `[trust]`.

**Seam inventory — pinning each edge:**

```bash
# Transport discovery per edge
rg "fetch\(|axios|http\.Client|requests\.|grpc\.Dial|@Client" -l   # sync HTTP/gRPC
rg "publish|subscribe|emit|enqueue|send_message|kafka|rabbit|sqs" -i -l   # async queue
rg "CREATE TABLE|__tablename__|@Entity" <shared-schema-dir> -l   # shared-table coupling

# Contract ownership: who defines the shape that crosses
rg "schema|dto|serializ|deserializ|validate|parse" -i -l <edge-endpoints>
# A published type/proto/schema on one side = owned contract; matching hand-rolled dicts on both sides = implicit convention (a finding).

# Coupling direction: who imports whom (drafts the arrow)
rg "from .*<module>|import .*<module>" -l

# Error semantics per edge
rg "try|catch|except|onError|\.catch|recover|panic" <edge-file> -n
```

Per seam, record the seam's four answers (SKILL.md Phase 2) — with worked-instance values at this hop if tracing. The output feeds report §3b and the system map's edge labels.

## Data flow probes

```bash
# HTTP surface
rg "@(Get|Post|Put|Delete|Patch)Mapping|@(app|router)\.(get|post|put|delete)|route\(" -n

# Event/queue surfaces
rg "publish\(|subscribe\(|emit\(|@.*Subscriber|kafka|rabbitmq|sqs" -i -l

# Storage surfaces
rg "CREATE TABLE|class .*Base|__tablename__|@Entity|schema\.|migrat" -i -l

# Config and env dependency
rg "process\.env\.|os\.environ|os\.Getenv|config\." -h | sort -u | head -30
```

## System design mapping probes (Phase 5)

Answer each row of the system design table (SKILL.md Phase 5) with one cheap probe:

| Question | Probe |
|---|---|
| Sync or async flow? | `rg "await \|\.then(\|go func\|tokio::spawn\|threading\|multiprocessing" -l` |
| Retries / failure handling? | `rg "retry\|backoff\|circuit.?breaker\|deadline\|timeout\|fallback" -i -l` |
| Consistency model? | migration files + `rg "transaction\|BEGIN\|COMMIT\|isolation\|serializable" -i` |
| Idempotency? | `rg "idempoten\|dedup\|exactly.?once\|at.?least.?once" -i -l` |
| Backpressure / queues? | `rg "queue\|buffer\|channel\|semaphore\|rate.?limit\|throttle" -i -l` |
| Authn/authz boundaries? | `rg "middleware\|interceptor\|guard\|policy\|authorize\|authenticate" -i -l` |
| Observability? | `rg "log\|trace\|metric\|prometheus\|opentelemetry\|datadog\|health" -i -l --stats` |
| Feature flags / config? | `rg "feature.?flag\|toggle\|env\.|config\." -i -l` |
| Horizontal scalability? | where does state live? `rg "singleton\|global\|static\|lock\|mutex\|sync\.Once" -i -l` |
| Graceful shutdown? | `rg "SIGTERM\|SIGINT\|shutdown\|graceful\|lifecycle" -i -l` |

## Decision archaeology: digging out the "why"

For each load-bearing decision, dig for three artifacts before writing §7 (SKILL.md Phase 5): the rejected alternative, the forcing constraint, the named cost.

**The rejected alternative — what did the team *not* do:**

```bash
# When did the pattern appear, and what did it replace?
git log -S "<pattern keyword>" --oneline -- <path>     # e.g. -S "circuit" or -S "outbox"
git log -p --follow <decision-file> | head -100        # birth commit + message often state the why

# Stated rationale: ADRs, design docs, admission comments
ls docs/adr* docs/decisions* design/ 2>/dev/null
rg "we tried|previously|instead of|used to|deprecated|why not|trade-?off" -i -n --type md
rg "TODO|FIXME|HACK|XXX|NOTE" <decision-file> -n

# Deviation from stack-idiomatic default = a decision made against a default (highest yield):
# know the framework's default (see "Working with framework-idiomatic code") and diff against it.
```

**The forcing constraint — what made the choice necessary:**

```bash
git shortlog -sn                                  # team size
git log --format='%ad' --date=short | sort | uniq -c   # history tempo / deadline bursts
rg "MAX_|LIMIT_|THROTTLE|RATE|POOL|TIMEOUT|WORKERS" -i -n config/ .env.example   # scale numbers
git log --oneline --follow migrations/            # schema pressure predating code
```

**The named cost:** from the tradeoff itself (probe the failure modes the choice gives up — e.g. chose AP: grep for stale-read handling, or its absence). A decision entry with no cost row means the dig didn't finish.

Where all three artifacts are missing, the rationale stays (inferred) — say so; don't manufacture plausibility.

## Ablation probes

For each major component C, answer: who would notice if C vanished?

```bash
python3 scripts/analyze.py ablation <repo-root> <module>
rg "<module_name>" -l        # every file that mentions it
rg "import .*<module>" -l    # every file that depends on it
```

- **Many importers:** load-bearing. Find the top importer; is it a hub (orchestrator) or a leaf (utility)?
- **Importers are all in one directory:** an internal implementation detail of that subsystem.
- **No importers:** (a) dead code, (b) a plugin/extension entry (`entry_points`, `conftest`, DI registration, `__init__.py` auto-import, dynamic import, reflection) — grep for dynamic loading before declaring dead, or (c) an external contract (a published package/CLI other systems consume). Evidence needed to distinguish.

## Tracing one request end-to-end (the Layer 3 probe)

Pick the flow most representative of the system's purpose, and **one worked instance** — a concrete illustrative request with sample values (e.g. "POST /charge for $42.00, user 123", values invented-but-plausible, field names from the code). Carry that instance through every hop.

1. Find the entry (handler, route, CLI command, message consumer).
2. Follow calls downward; note each boundary crossed (HTTP→app, app→domain, domain→IO).
3. At each seam, answer the four questions (SKILL.md Phase 2) — the instance's values are the shape in/out at this hop.
4. Note where errors are handled vs. propagated.
5. Note where data shapes change (DTOs, serialization) — the instance's values are the before/after pair.
6. Stop when you hit infrastructure (DB, network, disk, queue).

Record the file:line of each hop plus the per-hop data (responsibility, shape in/out, failure behavior). That record *is* the critical path section of the report — a flow story about the instance, not a bare hop list.

```bash
python3 scripts/analyze.py trace <repo-root> <symbol>   # seed the trace
```

## Test directory as documentation

- Test names are executable architecture docs: `rg "it\(|test\(|describe\(" --type ts -h | head -40`
- Fixture/conftest files show the canonical way to instantiate the system.
- e2e/integration tests reveal the real component coupling, which unit test structure often hides.
- Test directory mirroring src/ = convention. Weird test layout = investigate why.
- The sweep tags the test tree; use its LOC share as a proxy for how contract-driven the team was.

## Reading large files cheaply

```bash
rg -n "^## |^# " <file>            # markdown outline
rg -n "^(class|def|func|public|private|export)" <file>    # code outline
sed -n '100,140p' <file>           # read only the section that matters
```

Full reads are reserved for: seams on the critical path, files you'll cite extensively, and any file < 200 lines that's high-fan-in. Everything else is swept, tagged, and skimmed — the coverage ledger records which tier each file got.

## Phase 7: verifying the report against the codebase

The second pass — the draft report checked against the code it describes. Run after synthesis, before the run is called done (SKILL.md Phase 7).

**7a — mechanical citation audit (automated):**

```bash
# Every file:line anchor, cited path, cross-link, and the stamp, checked
# against the repo. Exit 0 = audit clean; exit 1 = the report doesn't ship.
python3 scripts/analyze.py verify <repo-root>                        # auto-discovers
python3 scripts/analyze.py verify <repo-root> docs/architecture/*.md  # split mode
python3 scripts/analyze.py verify <repo-root> --json                  # machine-readable
```

Findings it catches are enumerated in SKILL.md Phase 7a. **Every fix re-reads the actual source file** — never re-anchor from memory (the fix that isn't checked is how a wrong line number becomes a confidently wrong line number).

**7b — cold-eyes claim re-probe (judgment, sampled by blast radius):**

```bash
# Over-claim hunt: grep for the counterexample behind "always/never/only/guaranteed"
rg "<claimed-impossible-pattern>" -i -n --type <lang>

# Under-claim hunt: re-run the seam probes on the map's edges, diff vs §3b
rg "exec\(|spawn|subprocess|celery|bullmq|systemd|amqp://|redis://" -i -l

# Worked instance re-walk: open the cited hops in order, values verbatim
sed -n '<line>,<line>p' <cited-file>    # hop by hop, does the story hold?

# Refuted-hypothesis regression: claims matching a Refuted ledger row
rg "<refuted-pattern>" -i -n            # the report must not quietly re-assert it
```

Re-probe one load-bearing claim per section, prioritized: §5 mapping rows, §7 decisions, §8 deviations, everything the user's goal asked about, and the worked instance end to end. Soften or delete what the code doesn't support; upgrade `(inferred)` where a probe has since confirmed. Then **re-run 7a on the final text** — the audit that matters is the one run after all edits.

## Selective-huge mode: deep zones + breadth-only (huge repos)

Trigger and tier rules: SKILL.md deep-read policy. Sweep breadth stays 100%; depth concentrates into 1–3 **deep zones**.

**Picking zones (when auto-picking or sanity-checking the user's pick):**

```bash
python3 scripts/analyze.py sweep <repo-root> --json       # dir census: LOC + disposition per top-level path
python3 scripts/analyze.py focus <repo-root> "<goal>"     # goal-signal density (fast mode fine here)
python3 scripts/analyze.py skeleton <top-dir>             # per-zone structure, no direction from import graphs yet
```

Score each top-level candidate: goal-signal density × fan-in (who depends on it) × state ownership (has migrations/schema?). Zone the flow the user's goal names; when the goal is broad, zone the **stable spine** — the gateway/dispatch + the domain core everything imports. Zone rows go in the coverage ledger with the tier; everything else is `breadth-only`.

**Breadth-only probe set (zones-exempt, still mandatory):** entry-point discovery, `skeleton` at depth 1 per top dir, seam discovery from ops surfaces (compose/Procfile/k8s/queue configs), migration + config reads, and ablation on the honest-fan-in candidates. This is enough for the system map, the seams table, and structural claims — nothing behavioral.

**Zone probes (full depth):** everything in the standard workflow — Layer 2/3 reads, the worked-instance trace (it must live inside a zone), Phase-2b seam correction, ablation within the zone.

**Scope discipline:** the worked instance, contrast flow, and decision archaeology all stay inside zones. A question that surfaces outside a zone gets one of two answers: structural (from the breadth probe set) or it goes in Open questions with the zone it would need. The Phase-7 re-probe checks §0b against this partition — depth outside zones is the regression it hunts.