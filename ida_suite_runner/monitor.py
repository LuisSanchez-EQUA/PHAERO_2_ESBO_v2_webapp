# -*- coding: utf-8 -*-
"""
Process and completion monitoring helpers.

"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple


def _find_footprint_in_case(case_dir: Path) -> Optional[Path]:
    """
    Look for any idamod*/footprint.txt under the case folder.

    """
    try:
        for sub in case_dir.iterdir():
            if sub.is_dir() and sub.name.lower().startswith("idamod"):
                fp = sub / "footprint.txt"
                if fp.exists():
                    return fp
    except FileNotFoundError:
        pass
    return None


def detect_done_markers(case_dir: Path) -> Optional[str]:
    """
    Check standard completion signals

    Order and messages match the original:
      1) idamod*/footprint.txt -> "Detected <path> -> done."
      2) log.txt contains "End of simulation" -> "Found 'End of simulation' in log.txt."
    """
    fp = _find_footprint_in_case(case_dir)
    if fp is not None:
        return f"Detected {fp} -> done."

    log_txt = case_dir / "log.txt"
    if log_txt.exists():
        try:
            txt = log_txt.read_text(errors="ignore")
            if "End of simulation" in txt:
                return "Found 'End of simulation' in log.txt."
        except Exception:
            pass

    return None


def get_psutil_process(pid: int):
    """
    Try to obtain a psutil.Process for the given pid.

    Returns the process object, or None if psutil is missing or the process
    cannot be created
    """
    try:
        import psutil  # type: ignore
        return psutil.Process(pid)
    except Exception:
        return None


def sample_psutil(proc) -> Tuple[float, float]:
    """
    Sample CPU percent (blocking interval ~0.5s) and RSS memory in MB.

    If proc is None or sampling fails, returns (0.0, 0.0).
    Mirrors the original usage:
      cpu = psproc.cpu_percent(interval=0.5)
      mem = psproc.memory_info().rss / (1024*1024)
    """
    if proc is None:
        return 0.0, 0.0
    try:
        cpu = proc.cpu_percent(interval=0.5)
        mem = proc.memory_info().rss / (1024 * 1024)
        return float(cpu), float(mem)
    except Exception:
        return 0.0, 0.0
