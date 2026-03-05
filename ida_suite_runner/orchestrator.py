# -*- coding: utf-8 -*-
"""
Suite orchestrator (rolling parallel execution).


"""

from __future__ import annotations

import concurrent.futures as cf
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .ida_types import Job, LaunchConfig  # UPDATED IMPORT
from .runner import run_job
from .discovery import discover_cases, _filter_cases_by_names


def _jobs_from_cases(
    cases: List[Path],
    suite_root: Path,
    work_root: Path,
    *,
    preserve_suite_subpath: bool
) -> List[Job]:
    """
    Construct Job objects for each discovered case.
    """
    jobs: List[Job] = []
    for idm in cases:
        case_src_dir = idm.parent
        try:
            rel_case = case_src_dir.relative_to(suite_root)   # e.g. ICE_5_Cases\<CaseName>
        except Exception:
            rel_case = Path(case_src_dir.name)
        if preserve_suite_subpath:
            sub_work = work_root / rel_case                   # WORK\<SuiteSubpath>\<CaseName>
        else:
            sub_work = work_root / rel_case.name              # WORK\<CaseName>
        jobs.append(Job(
            idm_source=idm,
            work_dir=sub_work,
            title=f"IDA Suite: {idm.stem}",
            suite_root=suite_root,
        ))
    return jobs


def run_suite_parallel(
    suite_root: Path,
    cfg: LaunchConfig,
    work_root: Path,
    *,
    max_workers: int = 5, #TODO: Suggestion, make this easy to set as a config/parameterize when calling test4Ida2
    include: Iterable[str] = (),
    exclude: Iterable[str] = (),
    initial_delay_sec: float = 0.0,
    refill_delay_sec: float = 0.0,
    tunnel_or_road_mode: bool = False,
    cases_list: Optional[List[str]] = None,
    preserve_suite_subpath_override: Optional[bool] = None,  
) -> List[dict]:
    """
    Rolling-window parallel execution: keep up to max_workers jobs running until all are done.


    """
    cases = discover_cases(suite_root, include=include, exclude=exclude)
    if cases_list:
        cases = _filter_cases_by_names(cases, cases_list, suite_root)
    total = len(cases)
    if total == 0:
        print("[parallel] No cases found.")
        return []

    # either WORK\<SuiteSubpath>\<Case>\... or WORK\<Case>\...
    preserve_suite = (
        preserve_suite_subpath_override
        if preserve_suite_subpath_override is not None
        else (not tunnel_or_road_mode)
    )

    jobs = _jobs_from_cases(cases, suite_root, work_root, preserve_suite_subpath=preserve_suite)

    print(f"[parallel] Scheduling {total} case(s) with up to {max_workers} workers...")

    results: List[Optional[dict]] = [None] * total
    idx_next = 0 # index of the next unscheduled job (next job to submit)
    in_flight: Dict[cf.Future, int] = {}

    def _run_and_return(idx: int, job: Job) -> dict:
        try:
            return run_job(job, cfg, tunnel_or_road_mode=tunnel_or_road_mode)
        except Exception as e:
            return {
                "pid": -1,
                "duration_sec": 0.0,
                "peak_cpu_percent": 0.0,
                "max_rss_mb": 0.0,
                "notes": [f"Exception: {e!r}"],
                "output_txt": str(job.work_dir / "output.txt"),
                "log_txt": str(job.work_dir / "log.txt"),
                "cmd": "",
            }

    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        # Prime
        while idx_next < min(max_workers, total):
            fut = ex.submit(_run_and_return, idx_next, jobs[idx_next])
            in_flight[fut] = idx_next
            print(f"[parallel] Started {idx_next+1}/{total}: {jobs[idx_next].work_dir}")
            idx_next += 1
            if initial_delay_sec > 0 and idx_next < min(max_workers, total):
                time.sleep(initial_delay_sec)

        # Refill as they finish
        while in_flight:
            done, _pending = cf.wait(in_flight.keys(), return_when=cf.FIRST_COMPLETED)
            for fut in done:
                idx_done = in_flight.pop(fut)
                results[idx_done] = fut.result()
                print(f"[parallel] Finished {idx_done+1}/{total}: {jobs[idx_done].work_dir}")
                if idx_next < total:
                    if refill_delay_sec > 0:
                        time.sleep(refill_delay_sec)
                    fut2 = ex.submit(_run_and_return, idx_next, jobs[idx_next])
                    in_flight[fut2] = idx_next
                    print(f"[parallel] Started  {idx_next+1}/{total}: {jobs[idx_next].work_dir}")
                    idx_next += 1

    return [r if r is not None else {} for r in results]
