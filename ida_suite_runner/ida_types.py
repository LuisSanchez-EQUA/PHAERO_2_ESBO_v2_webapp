# -*- coding: utf-8 -*-
"""
Core datatypes for the IDA suite runner.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class CliOptions:
    """
    Command-line switch bundle for launching IDA processes.

    Defaults preserve legacy behavior:
      - faststart_level: 1 (emit -G 1) unless explicitly set to None
      - window_state: ':icon'
      - do_and_exit: True (emit -Q)
    """

    faststart_level: Optional[int] = 1
    window_title: Optional[str] = None   # -L "title"
    window_state: Optional[str] = ":icon"  # -W :icon (start minimized)
    instance_id: Optional[str] = None    # value for -C; if None, use -C+
    temp_suffix: Optional[str] = None    # -T <name>; keep None to avoid extra temp subfolder
    do_and_exit: bool = True             # -Q
    extra_flags: List[str] = field(default_factory=list)  # any extra switches


@dataclass
class Job:
    """
    Description of a single case execution.

    - idm_source: ORIGINAL .idm path (in the suite tree) PATH-IN
    - work_dir:   target case folder under WORK where the case will run
    - title:      optional window title
    - suite_root: suite folder that contains this case
    """
    idm_source: Path
    work_dir: Path
    title: Optional[str] = None
    suite_root: Optional[Path] = None


@dataclass
class LaunchConfig:
    """
    Process + environment configuration for launching IDA and staging cases.


    """
    exe_path: Path
    img_path: Optional[Path] = None   # leave None to default to exe_dir/ida.img
    cli: CliOptions = field(default_factory=CliOptions)
    monitor_grace_after_done: float = 30.0
    idle_terminate_after: float = 300.0

    # Copy-ignore policy
    copy_ignore_patterns: Tuple[str, ...] = (
        ".svn", "__pycache__",
        "*.tmp", "*.log",
        "idamod*"
    )
