# Codebase Understanding Skills

Two opencode skills that turn any repository into a system design study — one analyzes the codebase, the other teaches what the analysis found. The approach takes inspiration from the [ArchAgent paper](https://arxiv.org/pdf/2602.22425) (Gupta et al.).

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
- **Hypothesis-driven depth.** Falsifiable theories about design intent are probed with cheap evidence; refuted hypotheses are as valuable as confirmed ones. Deep reads are spent only where they earn insight.
- **Seams over files.** The unit of study is the connection — how components tie together (transport, contract, coupling, error semantics), not file interiors.
- **Map to system design.** Every component gets a role (gateway, orchestrator, persistence, ...), every decision names its tradeoff, and every claim cites `file:line` or is marked `(inferred)`.

**Output:** `ARCHITECTURE.md` (or `PRIOR-ART.md` / `docs/architecture/` wiki) — system map, component inventory, critical-path trace, decision rationale, lessons, and a coverage ledger proving the full sweep. Bundled scripts: `orient.py` and `analyze.py` (Python 3, stdlib only).

## teach-architecture

Turn an existing report into an interactive terminal lesson. The report is the single source of truth — if it doesn't say it, the lesson doesn't teach it. Nothing is written to disk; the lesson lives in the conversation.

**Key ideas:**

- **Needs a report.** No analysis, no lesson — teaching un-analyzed code invites hallucination.
- **Ask the lens.** Build-my-own, interview-prep, onboarding, or pure-study — it sets which modules go deep.
- **First principles.** Fixed level: CS student / junior engineer. Problem → naive fix and why it fails → pattern name → cost. Mechanics before jargon.
- **Teach by asking.** Predict-before-reveal on every mechanism; live code reads with a prediction question attached.
- **One worked instance.** A single concrete request (the `$42.00`) carried through every flow stop, failure lane, and final exam.
- **Honest costs.** Every tradeoff is drawn as a dial with its marker; every "pattern to steal" ships with steal-when / reject-when; open questions close the lesson as visible homework.
- **Final exam.** 8 generated questions — one at a time, answers isolated, graded with a breakdown.

**Arc:** Frame → Map → Component tour → Guided flow → Tradeoff dials → Conventions & deviations → Patterns to steal → Final exam → Close. 20–40 minutes.

## How they fit together

| | reverse-engineer-codebase | teach-architecture |
|---|---|---|
| **Role** | Analyst | Teacher |
| **Input** | A repo + a goal | A report + a lens |
| **Output** | Study document on disk | Live lesson in the conversation |
| **Register** | Experienced engineer | First principles |

Run the analysis first; the report becomes the lesson's source of truth.