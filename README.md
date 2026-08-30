# Codebase Understanding Skills

Agent skills that turn any repository into a system design study — one analyzes the codebase, the other teaches what the analysis found. The approach takes inspiration from the [ArchAgent paper](https://arxiv.org/pdf/2602.22425) (Gupta et al.).

```
reverse-engineer-codebase     ───▶     teach-architecture
        (analyze)       report             (teach)
                     is the input
```

## reverse-engineer-codebase

Reverse engineer one repository into an evidence-bound architecture study.

**Key ideas:**

- **Ask the goal first.** The user states what they want to learn; the goal drives reading order, hypotheses, and report emphasis.
- **Sweep everything.** 100% of the repo is enumerated and classified — config, migrations, and scripts often hold the *factual* architecture.
- **Deep reads follow the sweep's verdict.** Small repos get every source file read; large repos get hypothesis-driven depth; huge repos (>2k files / >500k LOC) concentrate depth into 1–3 user-chosen deep zones, everything else breadth-only — with the scope stated in the report.
- **Hypothesis-driven depth.** Falsifiable theories about design intent are probed with cheap evidence; refuted hypotheses are as valuable as confirmed ones. Deep reads are spent only where they earn insight.
- **Seams over files.** The unit of study is the connection — how components tie together (transport, contract, coupling, error semantics), not file interiors.
- **Map to system design.** Every component gets a role (gateway, orchestrator, persistence, ...), every decision names its tradeoff, and every claim cites `file:line` or is marked `(inferred)`.
- **Verify the report.** A mandatory second pass audits the draft against the codebase — every `file:line` anchor, path, and link mechanically checked (`analyze.py verify`), and the load-bearing claims re-probed cold before the report ships.

**Output:** `ARCHITECTURE.md` (or `PRIOR-ART.md` / `docs/architecture/` wiki) — system map, component inventory, critical-path trace, decision rationale, lessons, and a coverage ledger proving the full sweep. Bundled scripts: `orient.py` and `analyze.py` (Python 3, stdlib only).

## teach-architecture

Turn an existing report into an interactive terminal lesson. The report is the single source of truth — if it doesn't say it, the lesson doesn't teach it. Nothing is written to disk; the lesson lives in the conversation.

**Key ideas:**

- **Needs a report.** No analysis, no lesson — teaching un-analyzed code invites hallucination.
- **Derive the lens.** The report already says what the user wanted (template type + §0 goal): build-my-own for design-lessons/PRIOR-ART, onboarding for specific-flow goals. Ask only when the report leaves it ambiguous.
- **Absolute first principles.** Fixed level: assume zero vocabulary — every technical term, down to *queue* and *cache*, is built from plain words at first use. Problem → naive fix and why it fails → mechanism → name → cost. Mechanics before jargon; definitions never lean on undefined terms.
- **Teach by asking.** Predict-before-reveal on every mechanism; live code reads with a prediction question attached.
- **One worked instance.** A single concrete request (the `$42.00`) carried through every flow stop, failure lane, and final exam.
- **Honest costs.** Every tradeoff is drawn as a dial with its marker; every "pattern to steal" ships with steal-when / reject-when; open questions close the lesson as visible homework.
- **Final exam.** 8 generated questions — one at a time, answers isolated, graded with a breakdown.

**Arc:** Frame → Map → Component tour → Guided flow → Tradeoff dials → Conventions & deviations → Patterns to steal → Final exam → Close. 30–50 minutes.

## How they fit together

| | reverse-engineer-codebase | teach-architecture |
|---|---|---|
| **Role** | Analyst | Teacher |
| **Input** | A repo + a goal | A report + a lens |
| **Output** | Study document on disk | Live lesson in the conversation |
| **Register** | Experienced engineer | First principles |

Run the analysis first; the report becomes the lesson's source of truth.