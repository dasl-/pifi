#!/usr/bin/env python3
"""
Reconcile the pyright suppression baseline with the current pyright output.

Idempotent: each run both ADDS `# pyright: ignore[...]` comments for new
violations and STRIPS rules that pyright reports as unnecessary
(reportUnnecessaryTypeIgnoreComment) — so the committed baseline stays
accurate as code and the environment change. Run it via the project venv so
imports resolve consistently:

    uv run utils/pyright_suppress.py

The whole backlog is greppable:

    grep -rn "pyright: ignore" pifi/ tests/ utils/

To pay down debt by hand: delete a comment, run pyright on that file, fix
what surfaces. File-level diagnostics (import cycles) get a per-file
`# pyright: <rule>=false` header instead of a per-line comment.
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict


IGNORE_RE = re.compile(r' *# pyright: ignore\[([^\]]*)\]')
UNNECESSARY_RULE_RE = re.compile(r'rule: "([^"]+)"')


def apply_line_edit(line: str, add_rules: set[str], remove_rules: set[str]) -> str:
    """Add/remove rules in a line's `# pyright: ignore[...]` comment.

    Removing the last rule drops the whole comment. Returns the new line
    (newline preserved).
    """
    ending = '\n' if line.endswith('\n') else ''
    body = line[: -len(ending)] if ending else line

    m = IGNORE_RE.search(body)
    if m:
        existing = [r.strip() for r in m.group(1).split(',') if r.strip()]
        base = body[: m.start()]
    else:
        existing = []
        base = body

    rules = sorted((set(existing) | add_rules) - remove_rules)
    if rules:
        return f'{base}  # pyright: ignore[{", ".join(rules)}]{ending}'
    return f'{base}{ending}'


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)

    print("Running pyright to collect diagnostics...")
    result = subprocess.run(['pyright', '--outputjson'], capture_output=True, text=True)
    if not result.stdout:
        print("pyright produced no output.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return 1

    diags = json.loads(result.stdout)['generalDiagnostics']

    line_adds: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    line_removes: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    file_adds: dict[str, set[str]] = defaultdict(set)

    for diag in diags:
        rule = diag.get('rule')
        if not rule:
            continue
        path = diag['file']
        if 'range' not in diag:
            file_adds[path].add(rule)
            continue
        line = diag['range']['start']['line'] + 1
        if rule == 'reportUnnecessaryTypeIgnoreComment':
            m = UNNECESSARY_RULE_RE.search(diag.get('message', ''))
            if m:
                line_removes[path][line].add(m.group(1))
        else:
            line_adds[path][line].add(rule)

    paths = set(line_adds) | set(line_removes) | set(file_adds)
    files_changed = 0
    added = removed = 0

    for path in paths:
        with open(path) as f:
            lines = f.readlines()

        # In-place line edits first (these never shift line numbers), so the
        # 1-based line numbers from pyright stay valid across the loop.
        touched = set(line_adds[path]) | set(line_removes[path])
        for line_num in touched:
            idx = line_num - 1
            if idx >= len(lines):
                print(f"  WARN: {path}:{line_num} out of range", file=sys.stderr)
                continue
            adds = line_adds[path].get(line_num, set())
            removes = line_removes[path].get(line_num, set())
            lines[idx] = apply_line_edit(lines[idx], adds, removes)
            added += len(adds)
            removed += len(removes)

        # File-level headers shift line numbers, so insert them last.
        if path in file_adds:
            insert_at = 1 if lines and lines[0].startswith('#!') else 0
            for i, r in enumerate(sorted(file_adds[path])):
                lines.insert(insert_at + i, f'# pyright: {r}=false\n')
                added += 1

        with open(path, 'w') as f:
            f.writelines(lines)
        files_changed += 1

    print(f"Added {added}, removed {removed} suppressions across {files_changed} files.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
