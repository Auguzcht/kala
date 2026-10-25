#!/usr/bin/env python3
"""Check current-doc links to records and portable paths (DOCS-HYGIENE).

Uses only Python's standard library and Git. Ignored local files are not
published documentation; tracked and non-ignored new docs are checked.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

TRUTH_ROOTS = ('docs/features/', 'docs/engineering/', 'docs/decisions/')
LOCAL_PATH = re.compile(r'(?<![\w])(?:/Users/|/tmp/|/private/|~/\.codex/|/Applications/|/var/folders/)[^\s<>"`|]*')
LOCAL_MARKER = 'local only, not retained'
INLINE = re.compile(r'!?\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s)]+))(?:\s+["\'][^\n]*?["\'])?\s*\)')
DEFINITION = re.compile(r'^\s{0,3}\[([^\]]+)\]:\s*(?:<([^>]+)>|(\S+))')
REFERENCE = re.compile(r'!?\[([^\]\n]+)\](?:\[([^\]\n]*)\])?(?!\()')
HTML = re.compile(r'<(?:a|img)\b[^>]*?\b(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)


def published_files(root: Path) -> list[str]:
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            cwd=root, check=True, capture_output=True)
    return sorted(set(p.decode() for p in result.stdout.split(b'\0') if p))


def truth_file(path: str) -> bool:
    return path in ('AGENTS.md', 'docs/README.md') or path.startswith(TRUTH_ROOTS)


def record_target(source: str, target: str) -> str | None:
    value = unquote(target.strip().strip('<>'))
    if value.startswith('#'):
        return None
    url = urlsplit(value)
    if url.scheme or url.netloc:
        # A repository-hosted URL must not bypass the local record boundary.
        match = re.search(r'(?:^|/)(docs/(?:archive/|work/(?:[^/]+/)*evidence/).*)', url.path)
        candidate = match.group(1) if match else ''
    else:
        path = url.path
        candidate = posixpath.normpath(path.lstrip('/') if path.startswith('/')
                                      else posixpath.join(posixpath.dirname(source), path))
    if candidate.startswith('docs/archive/') or re.match(r'docs/work/(?:[^/]+/)*evidence/', candidate):
        return candidate
    return None


def contexts(lines: list[str]) -> list[tuple[bool, bool]]:
    """Return (in fenced example, in an allowed section/Verified by field)."""
    stack: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    result = []
    for index, line in enumerate(lines):
        delimiter = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        in_fence = fence is not None
        if delimiter:
            token = delimiter.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1]:
                fence = None
            result.append((True, False))
            continue
        if not in_fence:
            heading = re.match(r'^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line)
            setext = (index + 1 < len(lines) and line.strip()
                      and re.match(r'^ {0,3}(=+|-+)\s*$', lines[index + 1]))
            if heading or setext:
                if heading:
                    level, title = len(heading.group(1)), heading.group(2).casefold()
                else:
                    level = 1 if lines[index + 1].lstrip().startswith('=') else 2
                    title = line.strip().casefold()
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
        allowed = any(re.match(r'^(historical sources|verified by)(?:\b|$)', t) for _, t in stack)
        field = bool(re.match(r'^\s*(?:[-*+]\s+)?(?:\*\*)?Verified by(?:\*\*)?\s*:', line, re.I))
        result.append((in_fence, allowed or field))
    return result


def links(lines: list[str], states: list[tuple[bool, bool]]):
    definitions = {}
    for i, line in enumerate(lines):
        if states[i][0]:
            continue
        m = DEFINITION.match(line)
        if m:
            definitions[' '.join(m.group(1).casefold().split())] = m.group(2) or m.group(3)
    for i, line in enumerate(lines):
        if states[i][0] or DEFINITION.match(line):
            continue
        line = re.sub(r'(`+).*?\1', lambda m: ' ' * len(m.group()), line)
        spans = []
        for m in INLINE.finditer(line):
            spans.append(m.span())
            yield i, m.group(1) or m.group(2)
        for m in HTML.finditer(line):
            yield i, m.group(1)
        for m in REFERENCE.finditer(line):
            if any(a <= m.start() < b for a, b in spans):
                continue
            label = m.group(2) or m.group(1)
            target = definitions.get(' '.join(label.casefold().split()))
            if target:
                yield i, target


def audit(root: Path, files: list[str] | None = None) -> dict:
    issues = []
    counts = {'documentation_files': 0, 'record_links': 0, 'record_link_violations': 0,
              'machine_local_paths': 0, 'machine_local_path_violations': 0,
              'marked_local_only_paths': 0}
    for name in files if files is not None else published_files(root):
        if name != 'AGENTS.md' and not name.startswith('docs/'):
            continue
        path = root / name
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue  # Binary artifacts are not text documentation.
        if '\0' in content:
            continue
        counts['documentation_files'] += 1
        lines = content.splitlines()
        states = contexts(lines)
        for i, line in enumerate(lines):
            occurrences = list(LOCAL_PATH.finditer(unquote(line)))
            counts['machine_local_paths'] += len(occurrences)
            if LOCAL_MARKER in line.casefold():
                counts['marked_local_only_paths'] += len(occurrences)
            else:
                counts['machine_local_path_violations'] += len(occurrences)
                for match in occurrences:
                    issues.append({'rule': 'local-path', 'file': name, 'line': i + 1,
                                   'target': match.group()})
        if truth_file(name):
            for i, target in links(lines, states):
                normalized = record_target(name, target)
                if normalized:
                    counts['record_links'] += 1
                    if not states[i][1]:
                        counts['record_link_violations'] += 1
                        issues.append({'rule': 'record-link', 'file': name,
                                       'line': i + 1, 'target': normalized})
    return {'counts': counts, 'issues': issues}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Print counts and findings as JSON')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = audit(root)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for issue in result['issues']:
            print(f"{issue['file']}:{issue['line']}: {issue['rule']}: {issue['target']}")
        print(json.dumps(result['counts'], sort_keys=True))
    return int(bool(result['issues']))


if __name__ == '__main__':
    raise SystemExit(main())
