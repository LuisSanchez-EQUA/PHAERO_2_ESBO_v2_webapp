# -*- coding: utf-8 -*-
"""
Command builder and preflight checks.

"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from .ida_types import LaunchConfig  


def build_command(cfg: LaunchConfig, script_path: Path, per_job_title: Optional[str] = None) -> List[str]:
    """
    Build the full command list to launch IDA with the given script.

    Mirrors original logic:
      - If cfg.cli.instance_id is set -> ["-C", value], else "-C+"
      - Include "-G <level>" only if faststart_level is not None
      - Optional title (-L) and window state (-W)
      - Optional temp suffix (-T)
      - -Q appended when do_and_exit is True
      - Append any extra flags verbatim
      - Primary run uses "-X <script>", with slashes normalized to forward
      - First two argv are [exe, img], where img defaults to <exe_dir>/ida.img
    """
    exe = str(cfg.exe_path)
    exe_dir = cfg.exe_path.parent
    img = str(cfg.img_path or (exe_dir / "ida.img"))  # always ida.img now

    flags: List[str] = []
    # 1) Instance id
 #   if cfg.cli.instance_id:
 #       flags.extend(["-C", cfg.cli.instance_id])
 #   else:
 #       flags.append("-C+")
    # 2) -G level (only if provided) 1 = faststart
    if cfg.cli.faststart_level is not None:
        flags.extend(["-G", str(int(cfg.cli.faststart_level))])
    # 3) title + window state
    title = per_job_title or cfg.cli.window_title
    if title:
        flags.extend(["-L", title])
    if cfg.cli.window_state:
        flags.extend(["-W", cfg.cli.window_state])
    # 4) optional temp suffix
    if cfg.cli.temp_suffix:
        flags.extend(["-T", cfg.cli.temp_suffix])
    # 5) do-and-exit
    if cfg.cli.do_and_exit:
        flags.append("-Q")
    # 6) extras
    flags.extend(cfg.cli.extra_flags)
    # 7) primary
    flags.extend(["-X", str(script_path).replace("\\", "/")])

    return [exe, img] + flags


def _preflight_or_die(cfg: LaunchConfig):
    """
    Validate presence of the executable and ida.img (or configured image).

    Messages and exit code are identical to the original:
      - Each problem is printed with a '[preflight] ' prefix
      - Exit code is 2 if any problem exists
    """
    problems = []
    if not cfg.exe_path.exists():
        problems.append(f"Executable not found: {cfg.exe_path}")
    img = cfg.img_path or (cfg.exe_path.parent / "ida.img")
    if not img.exists():
        problems.append(f"Image file not found: {img}")
    if problems:
        for p in problems:
            print("[preflight] " + p)
        sys.exit(2)
