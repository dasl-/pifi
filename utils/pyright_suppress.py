#!/usr/bin/env python3
"""
One-shot tool to add `# pyright: ignore[...]` comments for every existing
pyright violation in the repo, so we can land pyright as a CI gate without
a multi-day cleanup. The intent is "freeze current debt, prevent new debt."

To remove a suppression, delete the comment, run pyright on that file, and
fix what comes up:

    grep -rn "pyright: ignore" pifi/ tests/ utils/

For file-level diagnostics (import cycles) we prepend a per-file header
instead of a per-line comment, because the diagnostic has no specific line.
"""

import json
import os
import subprocess
import sys
from collections import defaultdict


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)

    print("Running pyright to collect diagnostics...")
    result = subprocess.run(['pyright', '--outputjson'], capture_output=True, text=True)
    if not result.stdout:
        print("pyright produced no output.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return 1

    data = json.loads(result.stdout)
    diags = data['generalDiagnostics']
    print(f"  {len(diags)} diagnostics across {len(set(d['file'] for d in diags))} files")

    line_level: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    file_level: dict[str, set[str]] = defaultdict(set)

    for diag in diags:
        rule = diag.get('rule')
        if not rule:
            continue
        path = diag['file']
        if 'range' in diag:
            # 0-based line in JSON; convert to 1-based for clarity
            line = diag['range']['start']['line'] + 1
            line_level[path][line].add(rule)
        else:
            file_level[path].add(rule)

    files_changed = 0
    suppressions_added = 0

    for path, line_rules in line_level.items():
        with open(path, 'r') as f:
            lines = f.readlines()

        for line_num, rules in line_rules.items():
            idx = line_num - 1
            if idx >= len(lines):
                print(f"  WARN: {path}:{line_num} out of range", file=sys.stderr)
                continue
            line = lines[idx]
            stripped_nl = line.rstrip('\n')
            ending = '\n' if line.endswith('\n') else ''
            rule_list = ', '.join(sorted(rules))
            comment = f'  # pyright: ignore[{rule_list}]'

            if 'pyright: ignore[' in stripped_nl:
                print(f"  SKIP: {path}:{line_num} already has pyright: ignore", file=sys.stderr)
                continue

            lines[idx] = stripped_nl + comment + ending
            suppressions_added += 1

        if path in file_level:
            file_rules = sorted(file_level[path])
            header_lines = [f'# pyright: {r}=false\n' for r in file_rules]
            insert_at = 0
            if lines and lines[0].startswith('#!'):
                insert_at = 1
            for i, h in enumerate(header_lines):
                lines.insert(insert_at + i, h)
            suppressions_added += len(header_lines)

        with open(path, 'w') as f:
            f.writelines(lines)
        files_changed += 1

    for path, file_rules in file_level.items():
        if path in line_level:
            continue
        with open(path, 'r') as f:
            lines = f.readlines()
        rules_sorted = sorted(file_rules)
        header_lines = [f'# pyright: {r}=false\n' for r in rules_sorted]
        insert_at = 1 if lines and lines[0].startswith('#!') else 0
        for i, h in enumerate(header_lines):
            lines.insert(insert_at + i, h)
        with open(path, 'w') as f:
            f.writelines(lines)
        files_changed += 1
        suppressions_added += len(header_lines)

    print(f"Added {suppressions_added} suppressions across {files_changed} files.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
