#!/usr/bin/env python3
"""Repo orientation report: the Phase 0 cheap-signal sweep in one command.

Generates a markdown report of manifest, layout, git tempo, hot paths,
and structural keywords. Read-only. Output is a starting point for the
hypothesis ledger, never a substitute for tracing code.

Usage: python3 orient.py <repo-root> [--json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MANIFESTS = [
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts",
    "Gemfile", "composer.json", "requirements.txt", "mix.exs", "flake.nix",
]

DOCS = ["README.md", "README", "README.rst", "ARCHITECTURE.md", "CONTRIBUTING.md", "docs"]

CONFIG_SIGNALS = [
    "Makefile", "justfile", "docker-compose.yml", "docker-compose.yaml",
    "Dockerfile", ".github/workflows", "Taskfile.yml", "skaffold.yaml",
    "helm", "k8s", "kubernetes", "terraform", ".env.example",
]

HOT_PATH_PATTERNS = ["fix", "hotfix", "patch", "revert", "perf", "optimize", "bug"]


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout or "").strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 1, ""


def git(cmd: list[str], cwd: Path) -> str:
    _, out = run(["git"] + cmd, cwd)
    return out


def section(title: str) -> str:
    return f"\n## {title}\n"


def build_report(root: Path) -> str:
    parts: list[str] = [f"# Orientation report: {root.name}\n"]

    # --- Manifests ---
    parts.append(section("Manifests (declared problem domains)"))
    found = False
    for m in MANIFESTS:
        f = root / m
        if f.exists():
            found = True
            parts.append(f"### {m}\n```\n{f.read_text(errors='replace')[:4000]}\n```\n")
    if not found:
        parts.append("_No common manifest found at root._\n")

    # --- Layout ---
    parts.append(section("Top-level layout"))
    if (root / ".git").exists():
        _, out = run(["git", "ls-files"], root)
        if out:
            top = sorted({line.split("/")[0] for line in out.splitlines() if line})
            parts.append("```\n" + "\n".join(top) + "\n```\n")
    if not parts[-1].endswith("```\n"):
        entries = sorted(p.name for p in root.iterdir())
        parts.append("```\n" + "\n".join(entries) + "\n```\n")

    # --- Docs present ---
    parts.append(section("Docs present"))
    present = [d for d in DOCS if (root / d).exists()]
    parts.append(", ".join(present) if present else "_none found at root_\n")

    # --- Git signals ---
    if (root / ".git").exists():
        parts.append(section("Git tempo (last 30 commits)"))
        log = git(["log", "--oneline", "-30"], root)
        parts.append(f"```\n{log or '_(no commits)_'}\n```\n")

        parts.append(section("Hot paths (most-touched paths, last 300 commits)"))
        name_only = git(["log", "--name-only", "--format=", "-300"], root)
        counts: dict[str, int] = {}
        for line in name_only.splitlines():
            line = line.strip()
            if not line:
                continue
            top = line.split("/")[0]
            counts[top] = counts.get(top, 0) + 1
        for path, n in sorted(counts.items(), key=lambda kv: -kv[1])[:15]:
            parts.append(f"- `{path}` — {n} commits")

        parts.append(section("Change character (recent commit subjects)"))
        subjects = git(["log", "--format=%s", "-100"], root)
        total = len([s for s in subjects.splitlines() if s.strip()])
        for pat in HOT_PATH_PATTERNS:
            n = sum(1 for s in subjects.splitlines() if pat in s.lower())
            if n:
                parts.append(f"- `{pat}`: {n}/{total} recent commits")
        if total == 0:
            parts.append("_(no git history)_")

        parts.append(section("Contributors"))
        parts.append(f"```\n{git(['shortlog', '-sn', 'HEAD'], root) or '_(n/a)_'}\n```\n")

    # --- Ops surface ---
    parts.append(section("Ops / infra surface"))
    present = [c for c in CONFIG_SIGNALS if (root / c).exists()]
    parts.append(", ".join(present) if present else "_none found at root_\n")

    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, help="repository root")
    ap.add_argument("--json", action="store_true", help="emit raw JSON instead of markdown")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"error: {args.root} is not a directory", file=sys.stderr)
        return 1

    report = build_report(args.root)
    if args.json:
        print(json.dumps({"repo": str(args.root), "report": report}))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())