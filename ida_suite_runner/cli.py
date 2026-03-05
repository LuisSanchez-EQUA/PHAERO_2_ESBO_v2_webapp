# -*- coding: utf-8 -*-
"""
CLI entrypoint

Defaults:
- Paths are built relative to the current working directory (CWD).

Flexibility:
- You can override paths using CLI flags
  Priority order to resolve EXE:
    1) --exe <path>
    2) ENV (ICE: IDA_ICE_EXE, Tunnel/Road: IDA_TUNNEL_EXE)
    3) CWD-relative default (e.g., install/.../bin/ida-xxx.exe)
    4) Auto-scan under CWD/install/** for ida-ice.exe or ida-tunnel.exe

Usage:
  python -m ida_suite_runner.cli [--exe path] [--path-in path] [--work path] [--img path]
  # or (from code root)
  python test_4_IDA_2.py [--exe path] [--path-in path] [--work path] [--img path]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .ida_types import CliOptions, LaunchConfig
from .launcher import _preflight_or_die
from .orchestrator import run_suite_parallel


USAGE = (
    "Usage:\n"
    "  python -m ida_suite_runner.cli [--exe EXE] [--path-in DIR] [--work DIR] [--img IMG]\n"
    "  # or (from code root)\n"
    "  python test_4_IDA_2.py [--exe EXE] [--path-in DIR] [--work DIR] [--img IMG]"
)


def _get_arg_path(flag: str) -> Optional[Path]:
    if flag in sys.argv:
        try:
            i = sys.argv.index(flag)
            return Path(sys.argv[i + 1])
        except Exception:
            print(f"Error: {flag} requires a path argument")
            sys.exit(1)
    return None


def _first_existing(candidates: List[Path]) -> Optional[Path]:
    for p in candidates:
        if p and p.exists():
            return p
    return None


def _scan_for_exe(base: Path, exe_name: str) -> Optional[Path]:
    """As a last resort, scan under base (e.g., CWD / 'install') for the exe."""
    try:
        # Prefer matches where parent is 'bin'
        for p in base.rglob(exe_name):
            if p.parent.name.lower() == "bin":
                return p
        # Otherwise return the first match
        for p in base.rglob(exe_name):
            return p
    except Exception:
        pass
    return None


def main() -> None:
    # simplified ICE-only CLI; other modes removed
    # optional args
    EXE_ARG: Optional[Path] = _get_arg_path("--exe")
    PATH_IN_ARG: Optional[Path] = _get_arg_path("--path-in")
    WORK_ARG: Optional[Path] = _get_arg_path("--work")
    IMG_ARG: Optional[Path] = _get_arg_path("--img")

    # CWD-relative anchors
    CWD = Path.cwd().resolve()

    INCLUDE: Tuple[str, ...] = ()
    EXCLUDE: Tuple[str, ...] = ()
    PARALLEL_WORKERS = 4
    INITIAL_DELAY_SEC = 2
    REFILL_DELAY_SEC = 2

    # Defaults for ICE
    default_exe = CWD / "install/ice/bin/ida-ice.exe"
    default_path_in = CWD / "ICE_cases"
    default_work = CWD / "work_ice"
    FASTSTART = 1
    PRESERVE_SUBPATH = True
    env_exe = os.getenv("IDA_ICE_EXE")
    exe_name = "ida-ice.exe"

    # Resolve PATH_IN / WORK with overrides (keep defaults otherwise)
    PATH_IN = PATH_IN_ARG or default_path_in
    WORK = WORK_ARG or default_work

    # Resolve EXE with priority: --exe > ENV > default > scan(CWD/install)
    exe_candidates: List[Path] = []
    if EXE_ARG:
        exe_candidates.append(EXE_ARG)
    if env_exe:
        exe_candidates.append(Path(env_exe))
    exe_candidates.append(default_exe)

    exe_found = _first_existing(exe_candidates)
    if not exe_found:
        # last resort: scan under CWD/install
        scanned = _scan_for_exe(CWD / "install", exe_name)
        exe_found = scanned if scanned else default_exe

    EXE = exe_found

    # Optional explicit image path (CLI or ENV), else None => <exe_dir>/ida.img
    img_env = os.getenv("IDA_IMG_PATH")
    IMG_PATH = IMG_ARG or (Path(img_env) if img_env else None)

    # Build config
    cli = CliOptions(
        faststart_level=FASTSTART,
        window_title=None,
        window_state=":icon",
        instance_id=None,
        temp_suffix=None,
        do_and_exit=True,
        extra_flags=[],
    )

    cfg = LaunchConfig(
        exe_path=EXE,
        img_path=IMG_PATH,  # None => default to exe_dir/ida.img
        cli=cli,
        monitor_grace_after_done=30.0,
        idle_terminate_after=3000000000000.0,
    )

    _preflight_or_die(cfg)

    # Run parallel IDA suite on all cases discovered under PATH_IN
    results = run_suite_parallel(
        PATH_IN, cfg, WORK,
        max_workers=PARALLEL_WORKERS,
        include=INCLUDE,
        exclude=EXCLUDE,
        initial_delay_sec=INITIAL_DELAY_SEC,
        refill_delay_sec=REFILL_DELAY_SEC,
        preserve_suite_subpath_override=PRESERVE_SUBPATH,
    )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
