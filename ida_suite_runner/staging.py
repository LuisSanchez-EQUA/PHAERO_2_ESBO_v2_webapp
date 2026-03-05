# -*- coding: utf-8 -*-
"""
Staging (copying) utilities.

"""

from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path

from .ida_types import Job, LaunchConfig  


def _ignore_func(patterns):
    """
    Return a callable suitable for shutil.copytree(ignore=...) that filters
    directory entries using fnmatch against the provided patterns tuple.
    """
    pats = tuple(patterns)

    def _inner(dirpath: str, names):
        ignored = []
        for pat in pats:
            ignored.extend(fnmatch.filter(names, pat))
        return ignored

    return _inner


def _copy_case_contents(src_case_dir: Path, dst_case_dir: Path, ignore_patterns):
    """
    Copy only the contents of src_case_dir into dst_case_dir.

    """
    dst_case_dir.mkdir(parents=True, exist_ok=True)
    for item in src_case_dir.iterdir():
        dst = dst_case_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True, ignore=_ignore_func(ignore_patterns))
        else:
            shutil.copy2(item, dst)


def materialize_case_to_work(job: Job, cfg: LaunchConfig) -> Path:
    """
    Ensure the case is materialized under job.work_dir.
    Returns the path to the .idm file inside job.work_dir.


    """
    job.work_dir.mkdir(parents=True, exist_ok=True)
    case_src = job.idm_source.parent

    # If src == dst, skip copying (keeps legacy try/except tolerance)
    try:
        if case_src.resolve() == job.work_dir.resolve():
            return job.idm_source
    except Exception:
        pass

    _copy_case_contents(case_src, job.work_dir, cfg.copy_ignore_patterns)

    return job.work_dir / job.idm_source.name
