#!/usr/bin/env python3
"""Static analysis of a repo: full sweep, structure, skeleton, and ablation probes.

Seven subcommands feeding the reverse-engineering workflow (see SKILL.md):

  sweep      Full-repo coverage sweep: EVERY file enumerated, counted, LOC'd,
             and tagged with a disposition. Output = the coverage ledger.
             Enforces the coverage contract: 100% of the repo accounted for.
             Three deep-read verdicts: full-read / selective / selective-huge
             (>2k source files or >500k source LOC — concentrate depth into
             1-3 deep zones). Above 30k files LOC reads are skipped for speed
             (fast mode: counts + tags stay 100%; --loc forces reads back on).
  langs      Language census only (files + LOC per language).
  skeleton   Layer-2 structural outline across ALL detected languages:
             classes, functions, imports, routes.
  ablation   Ablation probe: who imports/mentions a module (fan-in analysis).
  trace      Layer-3 helper: list files containing a symbol (starting points
             for a manual end-to-end trace).
  focus      Query-ranked reading order: score every file against the user's
             stated goal and emit the deep-read queue. Auto fast mode on
             huge repos (path/symbol/header scoring only; --full to force
             the exact pass).
  verify     Phase-7 citation audit: extract every `file:line` anchor, cited
             path, and cross-link from the draft report and check each
             against the repo — file exists, line in range, anchor not
             blank, link resolves. Exit 1 on any failure or a citation-free
             report: the report doesn't ship until the audit runs clean.

Read-only. Cheap by design: grep + parsing, no code execution from the repo.
Vendored/generated trees are counted and tagged, but their LOC is not read.

Usage:
  python3 analyze.py sweep <repo-root> [--depth 2] [--json]
                           [--threshold-files 100] [--threshold-loc 50000]
                           [--threshold-huge-files 2000] [--threshold-huge-loc 500000]
                           [--no-loc | --loc]
  python3 analyze.py langs <repo-root>
  python3 analyze.py skeleton <repo-root> [--lang auto|python|ts|js|go|rust|java|...]
  python3 analyze.py ablation <repo-root> <module-name> [--lang ...]
  python3 analyze.py trace <repo-root> <symbol> [--lang ...]
  python3 analyze.py focus <repo-root> "<query>" [--tier core|all] [--top N]
                           [--fast | --full] [--json]
  python3 analyze.py verify <repo-root> [report ...] [--json] [--all]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from collections import Counter

# ---------------------------------------------------------------- languages

LANG_PATTERNS: dict[str, dict] = {
    "python": {
        "extension": ".py",
        "class": r"^\s*class\s+(\w+)",
        "func": r"^\s*(?:async\s+)?def\s+(\w+)",
        "import": r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))",
    },
    "ts": {
        "extension": [".ts", ".tsx"],
        "class": r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)",
        "func": r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)",
        "import": r"^\s*import\s+.*from\s+['\"]([^'\"]+)['\"]",
        "route": r"@?(?:Get|Post|Put|Delete|Patch)?\s*(?:app|router)\.(get|post|put|delete|patch)\(",
    },
    "js": {
        "extension": ".js",
        "class": r"^\s*(?:export\s+)?class\s+(\w+)",
        "func": r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)",
        "import": r"(?:require\(['\"]([^'\"]+)['\"]\)|import\s+.*from\s+['\"]([^'\"]+)['\"])",
        "route": r"(?:app|router)\.(get|post|put|delete|patch)\(",
    },
    "go": {
        "extension": ".go",
        "class": r"^type\s+(\w+)\s+struct",
        "func": r"^func\s+(?:\([^)]+\)\s+)?(\w+)\(",
        "import": r'^\s*(?:"([^"]+)"|\w+\s+"([^"]+)")$',
    },
    "rust": {
        "extension": ".rs",
        "class": r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+(\w+)",
        "func": r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)",
        "import": r"^\s*use\s+([\w:]+)",
    },
    "java": {
        "extension": ".java",
        "class": r"^\s*(?:public|private|protected)?\s*(?:abstract\s+|final\s+)?class\s+(\w+)",
        "func": r"^\s*(?:public|private|protected)\s+\w[\w<>\[\],\s]*\s+(\w+)\(",
        "import": r"^\s*import\s+([\w\.]+)",
    },
    "kotlin": {
        "extension": [".kt", ".kts"],
        "class": r"^\s*(?:\w+\s+)*(?:class|object|interface)\s+(\w+)",
        "func": r"^\s*(?:\w+\s+)*fun\s+(\w+)",
        "import": r"^\s*import\s+([\w\.]+)",
    },
    "swift": {
        "extension": ".swift",
        "class": r"^\s*(?:\w+\s+)*(?:class|struct|enum|protocol|actor)\s+(\w+)",
        "func": r"^\s*(?:\w+\s+)*func\s+(\w+)",
        "import": r"^\s*import\s+(\w+)",
    },
    "ruby": {
        "extension": [".rb"],
        "class": r"^\s*(?:class|module)\s+(\w+)",
        "func": r"^\s*def\s+(\w+)",
        "import": r"^\s*require(?:_relative)?\s+['\"]([^'\"]+)['\"]",
    },
    "php": {
        "extension": ".php",
        "class": r"^\s*(?:abstract\s+|final\s+)?class\s+(\w+)",
        "func": r"^\s*(?:\w+\s+)*function\s+(\w+)",
        "import": r"^\s*use\s+([\w\\]+)",
    },
    "csharp": {
        "extension": ".cs",
        "class": r"^\s*(?:\w+\s+)*(?:class|struct|interface|record)\s+(\w+)",
        "func": r"^\s*(?:\w+\s+)*[\w<>\[\],\s]+\s+(\w+)\s*\(",
        "import": r"^\s*using\s+([\w\.]+)",
    },
    "c": {
        "extension": [".c", ".h"],
        "class": r"^\s*(?:typedef\s+)?struct\s+(\w+)",
        "import": r"^\s*#include\s+[<\"]([^>\"]+)[>\"]",
    },
    "cpp": {
        "extension": [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"],
        "class": r"^\s*(?:class|struct)\s+(\w+)",
        "func": r"^\s*(?:\w+\s+)+\**(\w+)\s*\(",
        "import": r"^\s*#include\s+[<\"]([^>\"]+)[>\"]",
    },
}

LANG_BY_EXT: dict[str, str] = {}
for _lang, _pats in LANG_PATTERNS.items():
    ext = _pats["extension"]
    for e in ([ext] if isinstance(ext, str) else ext):
        LANG_BY_EXT[e] = _lang

MANIFEST_LANG = [
    ("package.json", "ts"), ("pyproject.toml", "python"), ("setup.py", "python"),
    ("go.mod", "go"), ("Cargo.toml", "rust"), ("pom.xml", "java"),
    ("build.gradle", "java"), ("Gemfile", "ruby"), ("composer.json", "php"),
    ("mix.exs", "ruby"), ("*.csproj", "csharp"), ("*.sln", "csharp"),
]

# ---------------------------------------------------------------- sweep tags

MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "go.mod",
    "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile",
    "composer.json", "requirements.txt", "requirements-dev.txt", "mix.exs",
    "flake.nix", "default.nix", "shard.yml", "Paket.dependencies",
}
LOCKFILE_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "Cargo.lock", "go.sum", "poetry.lock", "Pipfile.lock", "Gemfile.lock",
    "composer.lock", "composer.lock.json", "Podfile.lock", "flake.lock",
}
ENTRY_BASENAMES = {
    "main", "__main__", "cli", "app", "index", "server", "wsgi", "asgi",
    "manage", "program", "application", "service",
}
ENTRY_EXTS = {".py", ".go", ".rs", ".js", ".ts", ".tsx", ".java", ".cs",
              ".kt", ".swift", ".rb", ".php", ".c", ".cpp"}

OPS_NAMES = {
    "makefile", "gnumakefile", "justfile", "taskfile.yml", "taskfile.yaml",
    "jenkinsfile", "procfile", "dockerfile", "cmakelists.txt", "meson.build",
    "docker-compose.yml", "docker-compose.yaml", "docker-compose.override.yml",
    ".gitlab-ci.yml", "skaffold.yaml", "vercel.json", "netlify.toml",
    "serverless.yml", "railway.json", "render.yaml", "fly.toml", "heroku.yml",
    "nginx.conf", ".nvmrc", ".tool-versions", "crossplane.yaml",
}
OPS_DIRS = {".github", ".circleci", ".gitlab", "k8s", "kubernetes", "helm",
            "charts", "terraform", "infra", "infrastructre", "deploy",
            "deployment", "deployments", "docker", "ops", "provisioning",
            ".terraform", "systemd", "nomad", "consul.d"}
OPS_EXTS = {".tf", ".tfvars", ".service", ".conf", ".mk"}

CONFIG_EXTS = {".toml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".env",
               ".editorconfig", ".plist"}
CONFIG_NAME_HINTS = ("tsconfig", "jsconfig", "eslint", "prettier", "babel",
                     "webpack", "vite", "rollup", "jest", "vitest", "next.config",
                     "nuxt.config", "tailwind", "postcss", "karma", "metro",
                     ".env", "babel.config", "turbo.json", "nx.json", "pnpm-workspace",
                     "lerna.json", "rust-toolchain", "rustfmt", "clippy",
                     "setup.cfg", "mypy.ini", "pytest.ini", "tox.ini", "ruff",
                     ".pre-commit-config", "renovate.json", "dependabot")

MIGRATION_DIRS = {"migrations", "migration", "migrate", "db", "sql", "schema",
                  "schemas", "alembic", "liquibase", "flyway", "prisma",
                  "diesel", "sqlx", "entityframework"}
MIGRATION_NAME_HINTS = ("migration", "migrate", "schema", "flyway", "liquibase", "alembic")
MIGRATION_EXTS = {".sql", ".ddl", ".prisma"}

GENERATED_DIRS = {"dist", "build", "out", "generated", "__generated__", "gen",
                  ".next", "nuxt-dist", "coverage", "target", "vendor", "third_party",
                  "thirdparty", "node_modules", "site-packages", "bazel-out", ".dart_tool",
                  "cmake-build-debug", "cmake-build-release", "__pycache__", ".venv", "venv"}
GENERATED_SUFFIXES = (".pb.go", ".pb.cc", ".pb.h", "_pb2.py", "_pb2_grpc.py",
                      ".generated.ts", ".generated.tsx", ".generated.js",
                      ".generated.rs", ".generated.cs", ".g.cs", ".g.dart",
                      "_gen.go", ".gen.ts", ".graphql-generated.ts", ".designer.cs",
                      ".designer.vb", ".pb.swift", "_pb.rb", "_pb.php")
GENERATED_NAMES = {"package-lock.json"}  # lockfiles counted as generated below

DESIGN_INPUT_EXTS = {".proto", ".graphql", ".graphqls", ".thrift", ".capnp",
                     ".avsc", ".fbs", ".avdl", ".wsdl"}
DESIGN_INPUT_HINTS = ("openapi", "swagger", "asyncapi", "apidocs")

TEST_DIR_HINTS = {"test", "tests", "spec", "specs", "__tests__", "e2e",
                  "integration", "unittests", "testing"}
TEST_PATTERNS = (
    re.compile(r"^test_.+\.py$"), re.compile(r".+_test\.py$"),
    re.compile(r".+_test\.go$"), re.compile(r"^test\d+_.*\.go$"),
    re.compile(r".+\.(test|spec)\.(ts|tsx|js|jsx|mjs)$"),
    re.compile(r".+_test\.(rs|kt|swift|php|rb|java|cs)$"),
    re.compile(r".+_spec\.(rb|js|ts)$"),
    re.compile(r".*(test|tests|spec)\.java$"),
    re.compile(r"^(conftest|testhelper|test_utils|testhelpers)\.py$"),
)

DOCS_EXTS = {".md", ".mdx", ".rst", ".adoc", ".asciidoc", ".txt", ".org"}
DOCS_NAMES = {"license", "licence", "notice", "changelog", "changes", "authors",
             "contributors", "code_of_conduct", "security.md", "history"}

DATA_EXTS = {".csv", ".tsv", ".jsonl", ".ndjson", ".parquet", ".sqlite",
             ".db", ".sqlite3", ".dat", ".feather", ".h5", ".pkl", ".pickle"}
DATA_DIRS = {"fixtures", "testdata", "test-data", "test_fixtures", "seeds",
             "seed", "examples", "samples", "mocks", "stubs", "data"}

ASSET_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
              ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".mov",
              ".webm", ".wav", ".flac", ".pdf", ".zip", ".tar", ".gz", ".tgz",
              ".bz2", ".xz", ".7z", ".bin", ".exe", ".dll", ".so", ".dylib",
              ".class", ".jar", ".pyc", ".wasm", ".psd", ".sketch", ".afphoto",
              ".blend", ".obj", ".glb", ".gltf", ".stl", ".fbx"}

# Dispositions, in primary-tag priority order.
DISPOSITIONS = [
    "design-input", "schema-migration", "manifest", "test", "generated",
    "vendored", "config-ops", "data-fixture", "asset", "docs", "source", "unclassified",
]

# .git is VCS metadata: excluded from enumeration (noted in output, not analyzed).
SKIP_DIRS = {".git"}
# Trees counted + tagged but not LOC-read (too big, low signal).
NO_LOC_DIRS = GENERATED_DIRS | {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache",
                               ".idea", ".vscode", ".tox", ".bundle"}


def is_text(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(1024)
        return b"\0" not in head
    except OSError:
        return False


def loc_of(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def tag_file(rel: PurePosixPath, suffix: str) -> list[str]:
    """Return all disposition tags for a file (caller picks primary by priority)."""
    parts = [p.lower() for p in rel.parts]
    name = parts[-1] if parts else ""
    base = name.rsplit(".", 1)[0] if "." in name else name
    stem = parts[-2] if len(parts) >= 2 else ""
    dirs = set(parts[:-1])
    tags: set[str] = set()

    # design inputs (proto/openapi/graphql/thrift...) — study gold
    if suffix in DESIGN_INPUT_EXTS or any(h in name for h in DESIGN_INPUT_HINTS):
        tags.add("design-input")
    # migrations & schema
    if dirs & MIGRATION_DIRS or suffix in MIGRATION_EXTS or any(
            h in name for h in MIGRATION_NAME_HINTS):
        tags.add("schema-migration")
    # manifests & lockfiles
    if name in MANIFEST_NAMES or suffix in {".csproj", ".sln", ".gemspec", ".podspec"}:
        tags.add("manifest")
    if name in LOCKFILE_NAMES or name.endswith(".lock"):
        tags.add("generated")
    # generated code
    if any(name.endswith(s) for s in GENERATED_SUFFIXES) or name in GENERATED_NAMES:
        tags.add("generated")
    if dirs & GENERATED_DIRS and "design-input" not in tags:
        tags.add("vendored" if dirs & {"vendor", "third_party", "thirdparty", "node_modules", "site-packages"} else "generated")
    # tests
    if dirs & TEST_DIR_HINTS or any(rx.match(name) for rx in TEST_PATTERNS):
        tags.add("test")
    # ops / CI
    if name in OPS_NAMES or dirs & OPS_DIRS or suffix in OPS_EXTS or (
            suffix in {".yml", ".yaml"} and any(x in dirs for x in (".github", ".gitlab"))):
        tags.add("config-ops")
    # shell scripts are ops/config surface (build, ci, dev tooling)
    if suffix in {".sh", ".bash", ".zsh", ".fish"} or name == "Makefile":
        if "test" not in tags and "design-input" not in tags:
            tags.add("config-ops")
    # config files
    if suffix in CONFIG_EXTS or any(h in name for h in CONFIG_NAME_HINTS):
        if "manifest" not in tags:
            tags.add("config-ops")
    # entry points (flag, not a disposition)
    if base in ENTRY_BASENAMES and suffix in ENTRY_EXTS:
        tags.add("entry-candidate")
    if suffix == ".sql":
        tags.add("schema-migration")
    # data & fixtures
    if dirs & DATA_DIRS or suffix in DATA_EXTS:
        if "schema-migration" not in tags:
            tags.add("data-fixture")
    if suffix in ASSET_EXTS:
        tags.add("asset")
    # docs
    if suffix in DOCS_EXTS or name in DOCS_NAMES:
        if "schema-migration" not in tags and "test" not in tags and "config-ops" not in tags:
            tags.add("docs")
    # source
    if suffix in LANG_BY_EXT:
        if "test" not in tags and "generated" not in tags and "vendored" not in tags:
            tags.add("source")

    if not tags:
        tags.add("unclassified")
    return sorted(tags & set(DISPOSITIONS) | (tags & {"entry-candidate"}))


def primary_disposition(tags: list[str], count: Counter | None = None) -> str:
    """Most frequent tag wins; ties broken by DISPOSITIONS priority order."""
    present = set(tags)
    if count:
        best = max(present, key=lambda d: (count[d], -DISPOSITIONS.index(d)))
        return best
    for d in DISPOSITIONS:
        if d in present:
            return d
    return "unclassified"


# ---------------------------------------------------------------- sweep core

def walk_repo(root: Path, read_loc: bool = True):
    """Yield (path, rel, suffix, tags, loc) for every file. 100% coverage.

    read_loc=False skips per-file byte reads (fast enumeration for huge
    repos): disposition tagging is unaffected, all LOC comes back None.
    """
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        rel = PurePosixPath(p.relative_to(root))
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        suffix = p.suffix.lower()
        tags = tag_file(rel, suffix)
        loc = None
        if read_loc:
            heavy = any(part in NO_LOC_DIRS for part in rel.parts)
            if not heavy and is_text(p):
                loc = loc_of(p)
        yield p, rel, suffix, tags, loc


# Above this file count, sweep drops per-file LOC reads (enumeration tags and
# counts stay 100%; LOC columns run on the best-effort sample that remains).
FAST_SWEEP_FILES = 30_000


def cmd_sweep(root: Path, depth: int, as_json: bool,
              threshold_files: int = 100, threshold_loc: int = 50000,
              huge_files: int = 2000, huge_loc: int = 500_000,
              loc_mode: str = "auto") -> int:
    # Fast-enumeration pre-census: above FAST_SWEEP_FILES, reading every file's
    # bytes costs minutes for no classification benefit — loc_mode forces it.
    auto_no_loc = False
    if loc_mode == "no-loc":
        read_loc = False
    elif loc_mode == "loc":
        read_loc = True
    else:
        read_loc = True
        n_files = sum(1 for p in root.rglob("*") if p.is_file()
                      and not any(part in SKIP_DIRS for part in p.relative_to(root).parts))
        if n_files > FAST_SWEEP_FILES:
            read_loc = False
            auto_no_loc = True
    if not read_loc:
        # LOC-less runs can't measure size tiers: no full-read (never proven
        # affordable), no huge tier (source LOC unknown). Files still count;
        # verdict floors to selective because neither tier is measurable.
        threshold_files = -1
        huge_files = huge_loc = -1
    records = []
    total_loc = 0
    locd_files = 0
    lang_files: Counter = Counter()
    lang_loc: Counter = Counter()
    source_files = 0          # disposition `source` only — deep-read candidates
    source_loc = 0
    unclassified: list[str] = []
    design_surface = {
        "manifests": [], "entry_points": [], "migrations": [], "ops": [],
        "design_inputs": [], "lockfiles": [],
    }

    for p, rel, suffix, tags, loc in walk_repo(root, read_loc=read_loc):
        records.append((rel, suffix, tags, loc))
        lang = LANG_BY_EXT.get(suffix)
        if lang and loc is not None:
            lang_files[lang] += 1
            lang_loc[lang] += loc
            total_loc += loc
            locd_files += 1
        elif lang and loc is None:
            lang_files[lang] += 1
        if loc is not None and lang is None:
            total_loc += loc
            locd_files += 1
        if "source" in tags:
            source_files += 1
            source_loc += loc or 0
        if "unclassified" in tags:
            unclassified.append(str(rel))
        r = str(rel)
        if "manifest" in tags:
            design_surface["manifests"].append(r)
        if "entry-candidate" in tags:
            design_surface["entry_points"].append(r)
        if "schema-migration" in tags:
            design_surface["migrations"].append(r)
        if "config-ops" in tags:
            design_surface["ops"].append(r)
        if "design-input" in tags:
            design_surface["design_inputs"].append(r)
        if r in (str(x) for x in [rel.name]) and (rel.name in LOCKFILE_NAMES
                                                 or rel.name.endswith(".lock")):
            design_surface["lockfiles"].append(r)

    n = len(records)

    # aggregate by directory at requested depth
    def depth_key(rel: PurePosixPath, d: int) -> str:
        parts = rel.parts
        return "/".join(parts[:d]) if len(parts) > d else "/".join(parts)

    dir_stats: dict[str, dict] = {}
    for rel, suffix, tags, loc in records:
        key = depth_key(rel, depth)
        st = dir_stats.setdefault(key, {"files": 0, "loc": 0, "disp": Counter(),
                                        "exts": Counter(), "langs": Counter()})
        st["files"] += 1
        if loc:
            st["loc"] += loc
        for t in tags:
            if t in DISPOSITIONS:
                st["disp"][t] += 1
        if suffix:
            st["exts"][suffix] += 1
        if suffix in LANG_BY_EXT:
            st["langs"][LANG_BY_EXT[suffix]] += 1

    # disposition summary
    disp_files: Counter = Counter()
    for _, _, tags, _ in records:
        disp_files[primary_disposition(tags)] += 1

    # deep-read policy: three tiers, decided by source-file count + source LOC
    if full_read := (source_files <= threshold_files and source_loc <= threshold_loc):
        policy = "full-read"
        policy_why = (f"{source_files} source files, {source_loc:,} source LOC "
                      f"≤ thresholds ({threshold_files} files / {threshold_loc:,} LOC)")
    elif (huge_files > 0 or huge_loc > 0) and (
            (huge_files > 0 and source_files > huge_files)
            or (huge_loc > 0 and source_loc > huge_loc)):
        policy = "selective-huge"
        over = []
        if huge_files > 0 and source_files > huge_files:
            over.append(f"files: {source_files:,} > {huge_files:,}")
        if huge_loc > 0 and source_loc > huge_loc:
            over.append(f"LOC: {source_loc:,} > {huge_loc:,}")
        policy_why = ("; ".join(over)
                      + f" | huge thresholds: {huge_files:,} files / {huge_loc:,} LOC")
    else:
        policy = "selective"
        over = []
        if source_files > threshold_files >= 0:
            over.append(f"files: {source_files} > {threshold_files}")
        if source_loc > threshold_loc >= 0:
            over.append(f"LOC: {source_loc:,} > {threshold_loc:,}")
        policy_why = "; ".join(over) if over else \
            "size tiers unmeasurable (fast mode: LOC not read)"

    if as_json:
        out = {
            "repo": str(root), "total_files": n, "total_loc": total_loc,
            "languages": {k: {"files": v, "loc": lang_loc[k]} for k, v in lang_files.items()},
            "dirs": {k: {kk: (dict(vv) if isinstance(vv, Counter) else vv)
                         for kk, vv in st.items()} for k, st in dir_stats.items()},
            "dispositions": dict(disp_files),
            "unclassified": unclassified,
            "design_surface": design_surface,
            "deep_read_policy": {
                "policy": policy,
                "source_files": source_files,
                "source_loc": source_loc,
                "threshold_files": threshold_files,
                "threshold_loc": threshold_loc,
                "huge_files": huge_files,
                "huge_loc": huge_loc,
                "fast_mode": not read_loc,
                "reason": policy_why,
            },
        }
        print(json.dumps(out, indent=1))
        return 0

    parts: list[str] = []
    parts.append(f"# Sweep: {root.name}\n")
    fast_note = ""
    if not read_loc:
        why = "auto: >30k files" if auto_no_loc else "forced via --no-loc"
        fast_note = (f" · **fast mode: LOC not read** ({why}; counts + tags stay 100% — "
                     "size-tier verdicts unavailable, policy = selective)")
    parts.append(f"**{n} files · {total_loc:,} LOC · {len(lang_files)} languages · "
                 f"coverage: 100% of repo enumerated{fast_note}**\n")

    parts.append("\n## Deep-read policy\n")
    if policy == "full-read":
        parts.append(f"**FULL-READ** — read every source file in full before synthesis. "
                     f"The sweep proved it affordable: {policy_why}. "
                     "Generated/vendored trees stay swept-only; tests/docs/config follow "
                     "their normal rules.")
    elif policy == "selective-huge":
        parts.append(f"**SELECTIVE-HUGE** — too big for standard selective depth "
                     f"({policy_why}). Sweep breadth stays 100% (non-negotiable), but "
                     "depth must be concentrated: pick **1–3 deep zones** (goal-aligned "
                     "subsystems — high fan-in × focus score) and deep-read only those; "
                     "everything else is breadth-only (structure + seams + load-bearing "
                     "config, no file interiors). Ask the user to choose zones if the "
                     "goal is broad. Coverage ledger records the partition: zone paths "
                     "earn full/skimmed; the rest record `breadth-only`. Report §1 "
                     "carries a Scope & confidence statement; claims must not exceed it.")
    else:
        parts.append(f"**SELECTIVE** — deep reads follow hypothesis value, not file order "
                     f"({policy_why}). Sweep breadth stays mandatory; the coverage ledger "
                     "records which paths earn deep reads.")

    parts.append("\n## Language census\n")
    parts.append("| Language | Files | LOC | LOC share |")
    parts.append("|---|---|---|---|")
    for lang, files in lang_files.most_common():
        share = (lang_loc[lang] / total_loc * 100) if total_loc else 0
        parts.append(f"| {lang} | {files} | {lang_loc[lang]:,} | {share:.0f}% |")

    ## Package-signal aggregation (H2 fix): package trees that bundle their own
    ## tests (libs/foo/{pkg,test}/...) mislabel as `test` because test files
    ## outcount source files. A manifest + real source share = a package; its
    ## primary disposition is the source-side majority, never `test`.
    pkg_dirs = set()
    for m in design_surface["manifests"]:
        parts_ = PurePosixPath(m).parts
        if len(parts_) >= 2:
            pkg_dirs.add("/".join(parts_[:2]))

    def dir_disposition(st: dict) -> str:
        disp: Counter = st["disp"]
        if not disp:
            return "unclassified"
        if "manifest" in disp and (disp["source"] or st["loc"]):
            filtered = Counter(t for t in disp.elements() if t != "test")
            return primary_disposition(list(filtered), count=filtered)
        return disp.most_common(1)[0][0]

    parts.append("\n## Coverage ledger (depth {})\n".format(depth))
    parts.append("| Path | Files | LOC | Primary disposition | Ext mix |")
    parts.append("|---|---|---|---|---|")
    for key in sorted(dir_stats, key=lambda k: (-dir_stats[k]["files"], k)):
        st = dir_stats[key]
        exts = ", ".join(f"{e}×{c}" for e, c in st["exts"].most_common(4))
        rel_key = key if not key.startswith("libs/") else "/".join(key.split("/")[:2])
        disp = dir_disposition(dir_stats[rel_key]) if rel_key in pkg_dirs and rel_key in dir_stats else dir_disposition(st)
        parts.append(f"| `{key or '.'}` | {st['files']} | {st['loc']:,} | "
                     f"{disp} | {exts} |")

    parts.append("\n## Design surface\n")
    for label, items in (
        ("Manifests", design_surface["manifests"]),
        ("Entry-point candidates", design_surface["entry_points"]),
        ("Migrations / schema", design_surface["migrations"]),
        ("CI / ops / deploy", design_surface["ops"]),
        ("Generated inputs (.proto/.graphql/OpenAPI — design artifacts)",
         design_surface["design_inputs"]),
        ("Lockfiles (pins the factual dependency tree)", design_surface["lockfiles"]),
    ):
        parts.append(f"**{label}** ({len(items)}):")
        if items:
            shown = ", ".join(f"`{i}`" for i in items[:25])
            parts.append(f"  {shown}" + (f" + {len(items) - 25} more" if len(items) > 25 else ""))
        parts.append("")

    parts.append("\n## Unclassified bucket\n")
    if unclassified:
        parts.append(f"{len(unclassified)} files have no disposition. Assign one "
                     "(or justify ignoring) before synthesis — these are explicit "
                     "ledger Questions:\n")
        for u in unclassified[:50]:
            parts.append(f"- `{u}`")
        if len(unclassified) > 50:
            parts.append(f"- ... and {len(unclassified) - 50} more")
    else:
        parts.append("_Empty — every file has a disposition._")

    parts.append("\n## Disposition summary (must total 100%)\n")
    parts.append("| Disposition | Files | Share |")
    parts.append("|---|---|---|")
    for d in DISPOSITIONS:
        c = disp_files.get(d, 0)
        if c:
            parts.append(f"| {d} | {c} | {c / n * 100:.1f}% |")
    accounted = sum(disp_files.values())
    parts.append(f"\nAccounted: {accounted}/{n} files "
                 f"({accounted / n * 100:.1f}%). `.git` excluded as VCS metadata.")

    print("\n".join(parts))
    return 0


def cmd_langs(root: Path) -> int:
    lang_files: Counter = Counter()
    lang_loc: Counter = Counter()
    for p, rel, suffix, tags, loc in walk_repo(root):
        lang = LANG_BY_EXT.get(suffix)
        if lang:
            lang_files[lang] += 1
            if loc:
                lang_loc[lang] += loc
    print("| Language | Files | LOC |")
    print("|---|---|---|")
    for lang, files in lang_files.most_common():
        print(f"| {lang} | {files} | {lang_loc[lang]:,} |")
    return 0


# ---------------------------------------------------------------- probing

def detect_langs(root: Path, override: str | None) -> list[str]:
    if override and override != "auto":
        return [override]
    counts: Counter = Counter()
    for manifest, lang in MANIFEST_LANG:
        if any(root.glob(manifest)):
            counts[lang] += 1000  # manifests outweigh file counts
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in LANG_BY_EXT:
            if not any(part in NO_LOC_DIRS or part in SKIP_DIRS for part in p.parts):
                counts[LANG_BY_EXT[p.suffix]] += 1
    return [lang for lang, _ in counts.most_common()] or ["python"]


def iter_source(root: Path, langs: list[str]):
    exts: set[str] = set()
    for lang in langs:
        e = LANG_PATTERNS[lang]["extension"]
        exts.update([e] if isinstance(e, str) else e)
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in exts:
            continue
        if any(part in SKIP_DIRS or part in NO_LOC_DIRS for part in p.parts):
            continue
        yield p


def compile_patterns(lang: str, kinds: list[str]):
    pats = LANG_PATTERNS[lang]
    return {k: re.compile(pats[k]) for k in kinds if pats.get(k)}


def _first_group(m: re.Match) -> str:
    for g in m.groups():
        if g:
            return g
    return ""


_NO_MATCH = re.compile(r"(?!x)x")  # never-matching pattern for missing kinds


def cmd_skeleton(root: Path, lang_name: str) -> int:
    langs = detect_langs(root, lang_name)
    classes: Counter = Counter()
    funcs: Counter = Counter()
    imports: Counter = Counter()
    routes: list[str] = []
    file_count = 0

    import_rxs = []
    for lang in langs:
        pats = LANG_PATTERNS[lang]
        import_rxs.append(re.compile(pats["import"]))

    for p in iter_source(root, langs):
        file_count += 1
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        for lang in langs:
            pats = compile_patterns(lang, ["class", "func", "route"])
            for m in pats["class"].finditer(text):
                classes[m.group(1)] += 1
            for m in pats["func"].finditer(text):
                funcs[m.group(1)] += 1
            for m in pats.get("route", _NO_MATCH).finditer(text):
                routes.append(f"{p.relative_to(root)}: {m.group(0).strip()[:80]}")
        for rx in import_rxs:
            for m in rx.finditer(text):
                val = _first_group(m)
                if val:
                    imports[val] += 1

    print(f"# Skeleton (langs: {', '.join(langs)}, {file_count} files)\n")
    if routes:
        print("## HTTP routes\n")
        for r in sorted(routes)[:40]:
            print(f"- {r}")
        print()
    if classes:
        print("## Classes/types (by multiplicity)\n")
        for name, n in classes.most_common(25):
            print(f"- {name} ({n})")
        print()
    if imports:
        print("## External dependencies (import frequency)\n")
        for name, n in imports.most_common(30):
            print(f"- {name} ({n})")
        print()
    if funcs:
        print("## Top function names (shared vocabulary)\n")
        for name, n in funcs.most_common(25):
            if n >= 2:
                print(f"- {name} ({n})")
    return 0


def cmd_ablation(root: Path, module: str, lang_name: str) -> int:
    langs = detect_langs(root, lang_name)
    import_rxs = [re.compile(LANG_PATTERNS[l]["import"]) for l in langs]
    sym_rx = re.compile(
        r"^\s*from\s+[\w\.]+\s+import\s+([^\(\)#\n]+)"   # python: from X import a, b
    )
    importers: list[tuple[Path, str]] = []
    mentions: list[Path] = []

    for p in iter_source(root, langs):
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        if module in text:
            mentions.append(p)
        for rx in import_rxs:
            matched = False
            for m in rx.finditer(text):
                val = _first_group(m)
                if module and module in val:
                    importers.append((p, val))
                    matched = True
                    break
            if matched:
                break
        if any(imp.strip() == module for imp in sym_rx.findall(text)):
            importers.append((p, f"from ... import {module}"))

    target = module.strip("/") or "<empty>"
    print(f"# Ablation probe: `{target}`\n")
    print(f"## Direct importers ({len(importers)})\n")
    for p, val in importers:
        print(f"- `{p.relative_to(root)}` imports `{val}`")
    if not importers:
        print("_(none found via static import)_")
        print("\n**Before declaring dead code, check dynamic loading:**")
        print("- DI registration, entry_points, plugin loaders, `__import__`/`importlib`,")
        print("  `require` with computed paths, reflection, framework auto-discovery")
        print("- Also check: is this an external contract (published package / CLI)?")

    print(f"\n## Files mentioning `{target}` in any capacity: {len(mentions)}\n")
    for p in mentions[:30]:
        print(f"- `{p.relative_to(root)}`")
    return 0


def cmd_trace(root: Path, symbol: str, lang_name: str) -> int:
    """Find files defining/calling a symbol — the seed for end-to-end tracing."""
    hits: list[tuple[Path, int, str]] = []
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    for p in iter_source(root, detect_langs(root, lang_name)):
        try:
            lines = p.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                hits.append((p, i, line.strip()[:120]))
    print(f"# Trace seed: `{symbol}` — {len(hits)} occurrences\n")
    for p, i, line in hits[:60]:
        print(f"- `{p.relative_to(root)}:{i}`: {line}")
    if len(hits) > 60:
        print(f"- ... and {len(hits) - 60} more")
    return 0


# ---------------------------------------------------------------- query focus

# Goal-language words: appear in nearly every stated goal, zero discriminative
# power ("explain how the system works"). Filtered before scoring.
STOP_TOKENS = {
    "how", "what", "why", "when", "where", "which", "who", "does", "did",
    "and", "for", "with", "this", "that", "from", "are", "was", "were",
    "the", "its", "there", "then", "than", "them", "they", "our", "your",
    "can", "could", "should", "would", "will", "into", "about",
    "work", "works", "code", "codebase", "repo", "repository", "project",
    "system", "understand", "understanding", "explain", "learn", "study",
    "want", "like",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", (text or "").lower())
            if len(t) >= 3]


def _stem(token: str) -> str:
    """Very small suffix stripper so 'authenticate' matches 'authentication'."""
    for suf in ("ization", "ations", "ation", "ments", "ment", "ings", "ing",
                "ies", "ers", "ed", "es", "s"):
        if len(token) > len(suf) + 2 and token.endswith(suf):
            return token[: -len(suf)]
    return token


def _query_tokens(query: str) -> tuple[list[str], set[str]]:
    """Split a goal into (ordered non-stop tokens, stemmed set)."""
    toks = [t for t in _tokenize(query) if not (_stem(t) in STOP_TOKENS or t in STOP_TOKENS)]
    return toks, {_stem(t) for t in toks}


def score_against_query(text: str, rel: PurePosixPath, qtoks: list[str],
                        qset: set[str], body: bool = True) -> dict:
    """Score one file's text + path against the stemmed query set.

    body=False (fast mode) skips full-body tokenization — the expensive pass —
    and scores path/name + symbol + opening-15-lines hits only. Rankings get
    coarser; that's the tradeoff on huge repos.
    """
    path_toks = [p for part in rel.parts for p in _tokenize(part)]

    # read once: index lines, walk tokens
    lines = text.splitlines()
    head_hits: list[str] = []          # query terms in the opening lines
    sym_hits: set[str] = set()         # def/class names matching the query
    body_counts: dict[str, int] = {}
    sym_rxs = (re.compile(r"^\s*(?:async\s+)?(?:def|fn|func(?:tion)?)\s+(\w+)"),
               re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)"))
    body_cap = None if body else 15
    for i, line in enumerate(lines):
        if body_cap is None or i < body_cap:
            for tok in _tokenize(line):
                body_counts[_stem(tok)] = body_counts.get(_stem(tok), 0) + 1
        if i < 15 and len(head_hits) < 3:
            if any(_stem(tok) in qset for tok in _tokenize(line)):
                head_hits.append(line.strip()[:80])
        for rx in sym_rxs:
            for m in rx.finditer(line):
                if _stem(m.group(1).lower()) in qset:
                    sym_hits.add(m.group(1))
    body_hits = sorted({t for t in qtoks if _stem(t) in body_counts})
    path_score = min(len(path_hits), 3) * 3 if (path_hits := sorted(
        {t for t in path_toks if _stem(t) in qset})) else 0

    # scoring: signal mix matches read-tier ladder —
    #   token coverage (what's inside) + path/name match (what it is) +
    #   symbol match (its API) + head hits (is the point stated upfront?)
    cov = len(body_hits) / max(len(qset), 1)
    path_score = min(len(path_hits), 3) * 3
    sym_score = min(len(sym_hits), 5) * 2
    head_score = 8 if head_hits else 0
    score = cov * 60 + path_score + sym_score + head_score
    return {
        "score": round(score, 1),
        "coverage": round(cov, 3),
        "path_hits": path_hits,
        "symbol_hits": sorted(sym_hits)[:6],
        "head_hits": head_hits,
        "matched_terms": body_hits[:12],
    }


def cmd_focus(root: Path, query: str, tier: str, top: int,
              as_json: bool, fast: bool | None = None) -> int:
    qtoks, qset = _query_tokens(query)
    if not qtoks:
        print("error: query produced no usable tokens", file=sys.stderr)
        return 1

    # fast mode (auto above FAST_FOCUS_FILES core files): skip full-body
    # tokenization — a coarse ranking beats a minutes-long scoring pass.
    FAST_FOCUS_FILES = 2_000
    if fast is None:
        wg = (root.rglob("*"))
        core_files_seen = 0
        for p0 in wg:
            if p0.is_dir():
                continue
            rel0 = PurePosixPath(p0.relative_to(root))
            if any(part in SKIP_DIRS or part in NO_LOC_DIRS for part in rel0.parts):
                continue
            if primary_disposition(tag_file(rel0, p0.suffix.lower())) in ("source", "design-input"):
                core_files_seen += 1
        fast = core_files_seen > FAST_FOCUS_FILES
    body = not fast

    rows: list[dict] = []
    for p, rel, suffix, tags, loc in walk_repo(root, read_loc=False):
        disp = primary_disposition(tags)
        if tier == "core" and disp not in ("source", "design-input"):
            continue
        if disp in ("generated", "vendored", "asset"):
            continue
        # dependency trees (.venv/site-packages, __pycache__…): accounted for by
        # the sweep, but never reading-order candidates — interfaces, not sources
        if any(part in NO_LOC_DIRS or part in SKIP_DIRS for part in rel.parts):
            continue
        if not is_text(p):
            continue
        try:
            text = p.read_text(errors="replace", encoding="utf-8")
        except OSError:
            continue
        s = score_against_query(text, rel, qtoks, qset, body=body)
        if s["score"] > 0:
            rows.append({
                "path": str(rel), "disposition": disp, "loc": loc or 0, **s,
            })

    rows.sort(key=lambda r: (-r["score"], r["path"]))
    n = len(rows)

    if as_json:
        print(json.dumps({
            "query": query,
            "tier": tier,
            "files_scored_positive": n,
            "reading_order": rows[:top],
        }, indent=1))
        return 0

    print(f"# Focus: reading order for “{query}”\n")
    fast_note = (" · **fast mode** (path/symbol/header scoring only — body "
                 "tokenization skipped; raise --full for the exact pass)"
                 if fast else "")
    print(f"**Tier:** {tier} · **Files scored > 0:** {n} · "
          f"**Query terms:** {', '.join(qtoks) or '—'}{fast_note}\n")
    if not rows:
        print("_No file scored against this query — check terms against the "
              "repo's vocabulary (see glossary/skeleton output)._")
        return 0

    print("| # | Score | Tier | File | LOC | Why |")
    print("|---|---|---|---|---|---|")
    for i, r in enumerate(rows[:top], 1):
        why = []
        if r["coverage"]:
            why.append(f"cov {r['coverage']:.0%}")
        if r["path_hits"]:
            why.append("path:" + ",".join(r["path_hits"][:2]))
        if r["symbol_hits"]:
            why.append("sym:" + ",".join(r["symbol_hits"][:2]))
        if r["head_hits"]:
            why.append("head")
        t = "core" if r["disposition"] == "source" else r["disposition"]
        print(f"| {i} | {r['score']} | {t} | `{r['path']}` | {r['loc'] or '—'} | "
              f"{'; '.join(why) or '—'} |")
    if n > top:
        print(f"\n_...and {n - top} more scored files (raise --top to see)_")
    return 0


# ---------------------------------------------------------------- verify (Phase 7)

# Citation forms the audit recognizes inside a report's text:
#   path/file.py:123   path/file.py:L123   path/file.py:123-130
#   `file.py`          <path/file.py>      [path/file.py]
# Bare `file.py:123` (no directory) is resolved against the repo tree.
CITE_FILELINE_RX = re.compile(
    r"`(?P<p1>[A-Za-z0-9_./-]+?):(?P<l1a>\d+)(?:-?(?P<l1b>\d+))?`"   # `a/b.py:12` / `:12-14`
    r"|(?<![A-Za-z0-9_./-])(?P<p2>[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]*):(?P<l2a>\d+)(?:-?(?P<l2b>\d+))?(?![\d])"
    r"|(?<![A-Za-z0-9_./-])(?P<p3>[A-Za-z0-9_.-]+\.[A-Za-z0-9]+):(?P<l3a>\d+)(?:-?(?P<l3b>\d+))?(?![\d])")
CITE_PATH_RX = re.compile(r"`(?P<p>[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`")
LINK_RX = re.compile(r"\]\((?P<href>[^)\s]+)\)")
STAMP_RX = re.compile(r"Generated\s+(?P<date>\d{4}-\d{2}-\d{2}|\w+ \d{1,2},? \d{4}|\d{1,2} \w+ \d{4})"
                      r"(?:\s+at commit|@|at)?\s+(?P<commit>[0-9a-f]{7,40})?",
                      re.IGNORECASE)


def _candidate_paths(root: Path) -> dict[str, str]:
    """Basename → posix rel path, first match wins (ties resolved by shortest path)."""
    index: dict[str, str] = {}
    for p, rel, *_ in walk_repo(root):
        name = rel.name
        if name not in index or len(rel.parts) < len(PurePosixPath(index[name]).parts):
            index[name] = str(rel)
    return index


def root_all_md(root: Path):
    """All markdown files under the repo root, excluding vendored/generated trees."""
    for p, rel, *_ in walk_repo(root):
        if rel.suffix.lower() in DOCS_EXTS and not any(
                part in NO_LOC_DIRS or part in SKIP_DIRS for part in rel.parts):
            yield p


def _resolve_cited(root: Path, index: dict[str, str], cited: str) -> tuple[str, str | None]:
    """Return (status, resolved_rel_or_none). Status: ok / missing."""
    if cited.startswith("/"):
        return ("ok", cited[1:]) if (root / cited[1:]).is_file() else ("missing", None)
    direct = root / cited
    if direct.is_file():
        return ("ok", cited)
    if "/" in cited:            # `dir/file` cited with a different case? try exact only
        return ("missing", None)
    return ("ok", index[cited]) if cited in index else ("missing", None)


def _line_no(text: str, lineno: int) -> tuple[bool, bool, str]:
    """Return (line_in_range, is_blank, line_text) for 1-based lineno."""
    lines = text.splitlines()
    if 1 <= lineno <= len(lines):
        lt = lines[lineno - 1]
        return True, not lt.strip(), lt
    return False, False, ""


def extract_citations(lines: list[str], index: dict[str, str]) -> dict:
    """Walk the report text and collect every citation, per report section and line."""
    citations: list[dict] = []
    paths: set[str] = set()
    links: list[str] = []
    stamp: dict | None = None
    section = ""
    for i, raw in enumerate(lines, 1):
        if raw.lstrip().startswith("#"):                       # heading = current section
            section = raw.lstrip().lstrip("#").strip() or section
        m = STAMP_RX.search(raw)
        if m and stamp is None:
            stamp = {"date": m.group("date"), "commit": m.group("commit") or "", "line": i}
        for m2 in CITE_FILELINE_RX.finditer(raw):
            groups = m2.groupdict()
            path = groups.get("p1") or groups.get("p2") or groups.get("p3")
            la = groups.get("l1a") or groups.get("l2a") or groups.get("l3a")
            lb = groups.get("l1b") or groups.get("l2b") or groups.get("l3b")
            if path and la:
                citations.append({
                    "kind": "file:line", "path": path,
                    "line": int(la), "line_end": int(lb) if lb else None,
                    "report_line": i, "section": section,
                })
        for m2 in CITE_PATH_RX.finditer(raw):
            pth = m2.group("p")
            # skip bare URLs / domains (e.g. `example.com`), accept only repo-shaped paths
            if "/" in pth or pth.endswith(tuple(LANG_BY_EXT)) or pth in MANIFEST_NAMES:
                paths.add(pth)
        for m2 in LINK_RX.finditer(raw):
            href = m2.group("href")
            if not href.startswith(("http://", "https://", "#", "mailto:")):
                links.append({"href": href, "report_line": i, "section": section})
    return {"citations": citations, "paths": sorted(paths), "links": links, "stamp": stamp}


def cmd_verify(root: Path, report_paths: list[Path], as_json: bool,
               show_all: bool) -> int:
    # Default: the conventional artifacts at repo root (split-mode wiki handled
    # by passing docs/architecture/ files explicitly or --all auto-discovery).
    if not report_paths:
        hits = [root / n for n in ("ARCHITECTURE.md", "PRIOR-ART.md")]
        report_paths = [h for h in hits if h.is_file()]
        if not report_paths:
            wiki = sorted(root.glob("docs/architecture/*.md")) + \
                   sorted(root.glob("wiki/*.md")) + \
                   sorted(root.glob("docs/architecture/**/*.md"))
            report_paths = sorted(set(wiki))
        if not report_paths:
            print("error: no report found (looked for ARCHITECTURE.md, "
                  "PRIOR-ART.md, docs/architecture/*.md) and none passed",
                  file=sys.stderr)
            return 1

    index = _candidate_paths(root)
    findings: list[dict] = []
    per_report: dict[str, dict] = {}
    total_cites = 0

    for rp in report_paths:
        rel_rp = str(rp.relative_to(root)) if rp.is_relative_to(root) else str(rp)
        if not rp.is_file():
            findings.append({"report": rel_rp, "kind": "report-missing", "detail": str(rp)})
            per_report[rel_rp] = {"citations": 0}
            continue
        lines = rp.read_text(encoding="utf-8", errors="replace").splitlines()
        extr = extract_citations(lines, index)
        rp_findings: list[dict] = []
        stamp = extr["stamp"]
        if stamp is None:
            rp_findings.append({"report": rel_rp, "kind": "stamp-missing",
                                 "detail": "no 'Generated <date> at commit <hash>' header"})
        for c in extr["citations"]:
            status, resolved = _resolve_cited(root, index, c["path"])
            note = ""
            if status == "missing":
                rp_findings.append({"report": rel_rp, "kind": "anchor-missing",
                                     "detail": f"{c['path']}:{c['line']} — file not in repo"})
                continue
            text = (root / resolved).read_text(encoding="utf-8", errors="replace")
            in_range, is_blank, lt = _line_no(text, c["line"])
            if not in_range:
                rp_findings.append({"report": rel_rp, "kind": "line-out-of-range",
                                     "detail": f"{c['path']}:{c['line']} — file has "
                                               f"{len(text.splitlines())} lines"})
                continue
            if is_blank:
                rp_findings.append({"report": rel_rp, "kind": "line-blank",
                                     "detail": f"{c['path']}:{c['line']} — cited line is blank"})
            if c["line_end"] and not (1 <= c["line_end"] <= len(text.splitlines())):
                rp_findings.append({"report": rel_rp, "kind": "line-out-of-range",
                                     "detail": f"{c['path']}:{c['line']}-{c['line_end']} — "
                                               f"range end beyond EOF"})
            total_cites += 1
        for pth in extr["paths"]:
            status, resolved = _resolve_cited(root, index, pth)
            if status == "missing":
                rp_findings.append({"report": rel_rp, "kind": "path-missing",
                                     "detail": f"`{pth}` cited but not found in repo"})
        for lk in extr["links"]:
            href = lk["href"]
            if href.startswith("#"):                # internal anchor, not a file
                continue
            target = root / href.split("#", 1)[0]
            if not target.exists():
                rp_findings.append({"report": rel_rp, "kind": "link-broken",
                                     "detail": f"({href}) at report line {lk['report_line']}"
                                               f" — target not found"})
        per_report[rel_rp] = {
            "citations": len(extr["citations"]),
            "paths": len(extr["paths"]),
            "links": len(extr["links"]),
            "stamp": extr["stamp"],
            "findings": rp_findings,
        }
        findings.extend(rp_findings)

    ok = not findings
    if as_json:
        print(json.dumps({
            "reports": [{"report": k, **{kk: vv for kk, vv in v.items()}} for k, v in per_report.items()],
            "total_file_line_citations": total_cites,
            "findings": findings,
            "passed": ok,
        }, indent=1))
    else:
        print("# Verify: Phase-7 citation audit\n")
        for k, v in per_report.items():
            stamp_s = ""
            if v.get("stamp"):
                stamp_s = f" · stamped {v['stamp']['date']}" + \
                          (f" @ {v['stamp']['commit'][:12]}" if v['stamp'].get("commit") else "")
            print(f"**{k}** — {v.get('citations', 0)} file:line citations · "
                  f"{v.get('paths', 0)} paths · {v.get('links', 0)} links{stamp_s}")
        if findings:
            print("\n**Findings:**\n")
            for f in findings:
                print(f"- [{f['kind']}] {f['report']}: {f['detail']}")
        else:
            print("\n**Audit clean.** Every citation, path, and link resolves.")
        if total_cites == 0:
            print("\n**Zero file:line citations** — a report with no anchors fails "
                  "the anti-hallucination contract by definition; add evidence or "
                  "re-run the analysis.")
    return 0 if ok and total_cites > 0 else 1


# ---------------------------------------------------------------- cli

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("sweep", help="full-repo coverage sweep (the coverage ledger)")
    sp.add_argument("root", type=Path)
    sp.add_argument("--depth", type=int, default=2)
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--threshold-files", type=int, default=100,
                    help="source-file count at/below which full-read mode triggers "
                         "(default 100; use --threshold-files 0 to force selective)")
    sp.add_argument("--threshold-loc", type=int, default=50000,
                    help="source LOC at/below which full-read mode triggers "
                         "(default 50000; use --threshold-loc 0 to force selective)")
    sp.add_argument("--threshold-huge-files", type=int, default=2000,
                    help="source-file count above which selective-huge mode triggers "
                         "(default 2000; 0 disables the huge tier)")
    sp.add_argument("--threshold-huge-loc", type=int, default=500_000,
                    help="source LOC above which selective-huge mode triggers "
                         "(default 500000; 0 disables the huge tier)")
    sp.add_argument("--no-loc", action="store_true",
                    help="fast enumeration: count + tag every file, never read bytes "
                         "(auto-enabled above 30k files; imply no size-tier verdicts)")
    sp.add_argument("--loc", action="store_true",
                    help="force per-file LOC reads even above the 30k auto cutoff")

    sp = sub.add_parser("langs", help="language census")
    sp.add_argument("root", type=Path)

    sp = sub.add_parser("trace", help="trace seeds: files containing a symbol")
    sp.add_argument("root", type=Path)
    sp.add_argument("symbol")
    sp.add_argument("--lang", default="auto",
                    choices=["auto"] + list(LANG_PATTERNS.keys()))

    sp = sub.add_parser("focus", help="query-ranked reading order (goal → files that matter)")
    sp.add_argument("root", type=Path)
    sp.add_argument("query", help="the user's stated goal, e.g. 'how does auth work'")
    sp.add_argument("--tier", choices=["core", "all"], default="core",
                    help="core = source + design-input only (default); all = every readable file")
    sp.add_argument("--top", type=int, default=25, help="rows to show (default 25)")
    sp.add_argument("--json", action="store_true")
    fast_group = sp.add_mutually_exclusive_group()
    fast_group.add_argument("--fast", action="store_true", default=None,
                            help="score path/symbol/header hits only — skip body "
                                 "tokenization (auto-enabled above 2k core files)")
    fast_group.add_argument("--full", dest="fast", action="store_false",
                            help="force the exact (body-tokenized) scoring pass")

    sp = sub.add_parser("verify", help="Phase-7 citation audit: check the draft report's "
                                       "file:line anchors, cited paths, and links against the repo")
    sp.add_argument("root", type=Path)
    sp.add_argument("report", nargs="*", type=Path,
                    help="report file(s); default: ARCHITECTURE.md | PRIOR-ART.md | "
                         "docs/architecture/*.md at repo root")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--all", action="store_true",
                    help="auto-discover all markdown reports under the repo root")

    for name in ("skeleton", "ablation"):
        sp = sub.add_parser(name)
        sp.add_argument("root", type=Path)
        sp.add_argument("module", nargs="?")
        sp.add_argument("--lang", default="auto",
                        choices=["auto"] + list(LANG_PATTERNS.keys()))
        if name != "skeleton":
            sp.add_argument("symbol", nargs="?")

    args = ap.parse_args()
    if not args.root.is_dir():
        print(f"error: {args.root} is not a directory", file=sys.stderr)
        return 1
    if args.cmd == "sweep":
        loc_mode = "no-loc" if args.no_loc else ("loc" if args.loc else "auto")
        if args.no_loc and args.loc:
            print("error: --no-loc and --loc are mutually exclusive", file=sys.stderr)
            return 1
        return cmd_sweep(args.root, args.depth, args.json,
                         args.threshold_files, args.threshold_loc,
                         args.threshold_huge_files, args.threshold_huge_loc,
                         loc_mode)
    if args.cmd == "langs":
        return cmd_langs(args.root)
    if args.cmd == "focus":
        return cmd_focus(args.root, args.query, args.tier, args.top, args.json,
                         args.fast)
    if args.cmd == "verify":
        reports = args.report
        if args.all:
            reports = [p for p in root_all_md(args.root)]
            if not reports:
                print("error: --all found no markdown reports", file=sys.stderr)
                return 1
        return cmd_verify(args.root, reports, args.json, args.all)
    if args.cmd == "skeleton":
        return cmd_skeleton(args.root, args.lang)
    target = getattr(args, "symbol", None) or getattr(args, "module", None)
    if not target:
        print(f"error: '{args.cmd}' requires a module/symbol name", file=sys.stderr)
        return 1
    if args.cmd == "ablation":
        return cmd_ablation(args.root, target, args.lang)
    return cmd_trace(args.root, target, args.lang)


if __name__ == "__main__":
    sys.exit(main())