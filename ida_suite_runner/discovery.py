# -*- coding: utf-8 -*-
"""
Case discovery and selection utilities.

"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def _find_case_idm_in_dir(dir_path: Path) -> Optional[Path]:
    """Return the canonical case .idm whose stem matches the case folder."""
    dirname = dir_path.name.lower()
    for idm in list(dir_path.glob("*.idm")) + list(dir_path.glob("*.IDM")):
        if idm.stem.lower() == dirname:
            return idm
    return None


def discover_cases(suite_root: Path,*,include: Iterable[str] = (),exclude: Iterable[str] = ()) -> List[Path]:
    """
    Walk suite_root and collect only case IDMs that match the parent-folder name.
    include/exclude are glob patterns on the relative case path.


    """
    suite_root = suite_root.resolve()
    cases: List[Path] = []

    def _match_any(rel: str, patterns: Iterable[str]) -> bool:
        for pat in patterns:
            if fnmatch.fnmatch(rel, pat):
                return True
        return False

    for d in sorted((path for path in suite_root.iterdir() if path.is_dir()), key=lambda p: p.name.lower()):
        idm = _find_case_idm_in_dir(d)
        if idm is None:
            continue
        try:
            rel_case = idm.parent.relative_to(suite_root)
        except Exception:
            rel_case = idm.parent
        rel_str = str(rel_case).replace("/", "\\")
        if include and not _match_any(rel_str, include):
            continue
        if exclude and _match_any(rel_str, exclude):
            continue
        cases.append(idm)

    cases.sort(key=lambda p: str(p).lower())

    print(f"[suite] Found {len(cases)} case(s) under {suite_root}")
    for i, p in enumerate(cases, 1):
        try:
            rel = p.parent.relative_to(suite_root)
        except Exception:
            rel = p.parent
        print(f"  {i:02d}. {rel}\\{p.name}")
    return cases


def _read_cases_file(path: Path) -> List[str]:
    """
    Read a text file with one case per line.

    - Empty lines and lines starting with '#' are ignored.
    - Lines optionally quoted with single or double quotes are unwrapped.
    - Encoding fallback matches original behavior: try utf-8, then utf-8-sig.
    """
    lines: List[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1]
        lines.append(s)
    return lines


def _filter_cases_by_names(cases: List[Path], names: List[str], suite_root: Path) -> List[Path]:
    """
    Filter discovered cases by a list of requested names or relative paths.

    Matching rules:
      1) Exact match on case directory name (case-insensitive)
      2) Exact match on relative path from suite_root, backslash-normalized
      3) Fallback: any relative path that endswith the requested token

    """
    if not names:
        return cases

    selected: List[Path] = []

    by_name: Dict[str, Path] = {}
    by_rel: Dict[str, Path] = {}
    for idm in cases:
        case_dir = idm.parent
        by_name[case_dir.name.lower()] = idm
        try:
            rel = case_dir.relative_to(suite_root)
            by_rel[str(rel).replace("/", "\\").lower()] = idm
        except Exception:
            pass

    for req in names:
        k = req.lower().replace("/", "\\")
        if k in by_name:
            selected.append(by_name[k])
            continue
        if k in by_rel:
            selected.append(by_rel[k])
            continue
        cand = [idm for rel, idm in by_rel.items() if rel.endswith(k)]
        if cand:
            selected.append(cand[0])

    seen = set()
    out: List[Path] = []
    for p in selected:
        if p not in seen:
            out.append(p)
            seen.add(p)

    print(f"[cases] Filtered: {len(out)}/{len(cases)} selected")
    return out
