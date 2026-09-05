# Codebase Understanding Skills

An agent skill that turns any repository into a system design lesson, taught live from the code, with archify rendering the diagrams.

```
any repo ───▶ teach-architecture        archify
             (prep pass + teach)  ───▶ renders the map + flow
             runs the tests live       as interactive HTML
```

## teach-architecture

Turn any repository into an interactive terminal lesson. The codebase is the single source of truth, read live — a bounded prep pass builds the syllabus, and every claim taught is anchored to `file:line` evidence read aloud at its beat. The lesson lives in the conversation; its two big diagrams (the system map and the critical-path flow) are rendered by the **archify** skill as interactive HTML in the repo.

**Key ideas:**

- **Teaches the code directly.** A bounded, goal-directed prep pass (entry points, config, migrations, main modules, tests) builds the teaching ledger in working notes — nothing else is written to disk.
- **Runs the tests live.** When the repo has tests, prep builds the environment (Python: `venv` + install packages; Node/Go/Rust: the stack's own tooling) and the guided-flow beat runs the critical-path test in front of the learner — predict what it asserts, run it, read the real output together. Test-fixture values become the worked instance. Failed setups are reported honestly; the test source read statically is the fallback.
- **Absolute first principles.** Fixed level: assume zero vocabulary — every technical term, down to *queue* and *cache*, is built from plain words at first use. Problem → naive fix and why it fails → mechanism → name → cost. Mechanics before jargon; definitions never lean on undefined terms.
- **Teach by asking.** Predict-before-reveal on every mechanism; live code reads and the test run each carry a prediction question.
- **One worked instance.** A single concrete request (the `$42.00`) carried through every flow stop, failure lane, and section checks — input data taken from the test file that exercises the critical path (read from the test source, run or not), otherwise a labeled illustrative input built from the code's field names. Its payload rides the flow diagram's first message and its values every message after.
- **Honest costs.** Every tradeoff is drawn as a dial with its marker; every "pattern to steal" ships with steal-when / reject-when; open questions close the lesson as visible homework.
- **Section checks, not a final exam.** Every module ends with its own 1–3 question check (8–12 total), answers isolated, graded cumulatively with a per-miss breakdown.

**Arc:** Frame → Map → Component tour → Guided flow (with the live test run) → Tradeoff dials → Conventions & deviations → Patterns to steal → Close. 30–50 minutes.

The **archify** skill renders the interactive diagrams: teach-architecture renders its system map (`architecture`) and critical-path flow (`sequence`) with archify by default, delivered in the repo. Archify renders verified facts only — it is a renderer, not a second analysis.

## Install Archify

[Install Archify](https://tt-a1i.github.io/archify/start.html?type=architecture&agent=codex&source=direct&input=description)