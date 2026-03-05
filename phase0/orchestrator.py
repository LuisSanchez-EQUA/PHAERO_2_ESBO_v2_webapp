# -*- coding: utf-8 -*-
"""
[PHASE0 ORCHESTRATOR]
Parallel Phase0 job executor (mirrors ida_suite_runner/orchestrator.py pattern).

Discovers JSON config files and runs Phase0 initialization in parallel.
Each job creates a case folder with .idm model ready for IDA Runner.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .workflows import derive_case_name, run_create_zones_single_case
from .data_loader import load_zone_types, load_zone_data


class _TeeStream:
    """Write to terminal and a worker log file simultaneously."""

    def __init__(self, stream, log_handle, *, filter_terminal: bool = False):
        self._stream = stream
        self._log = log_handle
        self._filter_terminal = filter_terminal
        self._buffer = ""

    @staticmethod
    def _is_critical_line(line: str) -> bool:
        text = line.strip().lower()
        if not text:
            return False
        critical_tokens = (
            "error",
            "fail",
            "warning",
            "retry",
            "crash",
            "could not",
            "case start",
            "case end",
            "[worker-",
        )
        return any(token in text for token in critical_tokens)

    def write(self, data):
        self._log.write(data)
        self._log.flush()
        if self._stream is None:
            return len(data)
        if not self._filter_terminal:
            self._stream.write(data)
            self._stream.flush()
            return len(data)

        # Buffered line-based filtering for terminal output.
        self._buffer += data
        while True:
            nl = self._buffer.find("\n")
            if nl < 0:
                break
            line = self._buffer[: nl + 1]
            self._buffer = self._buffer[nl + 1 :]
            if self._is_critical_line(line):
                self._stream.write(line)
                self._stream.flush()
        return len(data)

    def flush(self):
        if self._stream is not None:
            if self._filter_terminal and self._buffer:
                if self._is_critical_line(self._buffer):
                    self._stream.write(self._buffer)
                self._buffer = ""
            self._stream.flush()
        self._log.flush()

    def isatty(self):
        return bool(self._stream and getattr(self._stream, "isatty", lambda: False)())


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def discover_zone_json_files(
    data_dir: Path,
    include_pattern: str = "zones_*.json",
) -> List[Path]:
    """
    [DEBUG: DISCOVERY PHASE]
    Find all JSON config files matching pattern in data_dir.
    Returns sorted list of Path objects.
    """
    jsons = sorted(data_dir.glob(include_pattern))
    print(f"[PHASE0-ORCHESTRATOR] Discovered {len(jsons)} zone JSON files:")
    for j in jsons:
        print(f"  - {j.name}")
    return jsons


def _split_round_robin(
    items: List[Tuple[int, Path]],
    buckets: int,
) -> List[List[Tuple[int, Path]]]:
    if buckets <= 1:
        return [items]
    out: List[List[Tuple[int, Path]]] = [[] for _ in range(buckets)]
    for pos, entry in enumerate(items):
        out[pos % buckets].append(entry)
    return [chunk for chunk in out if chunk]


def _derive_case_name_from_json(json_config: Path) -> str:
    try:
        with open(json_config, "r", encoding="utf-8") as handle:
            zones = json.load(handle)
        if isinstance(zones, list) and zones and isinstance(zones[0], dict):
            first_zone = zones[0].get("zone_name")
            if isinstance(first_zone, str) and first_zone.strip():
                return derive_case_name(first_zone)
    except Exception:
        pass
    return json_config.stem


def _run_worker_batch(
    batch: List[Tuple[int, Path]],
    output_cases_dir: Path,
    *,
    worker_id: int,
    run_simulations: bool,
    refill_delay_sec: float,
    results_reader: str,
) -> List[Tuple[int, dict]]:
    # This block is in charge of one persistent worker session lifecycle.
    # It is used by `run_phase0_parallel(... worker_sessions=True)` via ProcessPoolExecutor.
    from .ida_session import connect_to_ida, disconnect_from_ida, exit_ida

    logs_dir = output_cases_dir / "_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"worker_{worker_id:02d}.txt"

    with open(log_path, "a", encoding="utf-8") as log_handle:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = _TeeStream(original_stdout, log_handle, filter_terminal=True)
        sys.stderr = _TeeStream(original_stderr, log_handle, filter_terminal=True)
        print("=" * 90)
        print(f"[WORKER-{worker_id:02d}] START {_now()} pid={os.getpid()} assigned_cases={len(batch)}")
        print(f"[WORKER-{worker_id:02d}] Batch: {[p.name for _, p in batch]}")

        zone_types_map = load_zone_types()
        zone_data_map = load_zone_data()
        results: List[Tuple[int, dict]] = []

        try:
            connect_to_ida()
        except Exception as exc:
            # If a worker cannot start an IDA session, mark all its assigned
            # cases as failed instead of crashing the whole orchestrator run.
            print(f"[WORKER-{worker_id:02d}] ERROR cannot connect to IDA: {exc}")
            for idx, json_config in batch:
                case_name = _derive_case_name_from_json(json_config)
                results.append(
                    (
                        idx,
                        {
                            "success": False,
                            "case_name": case_name,
                            "model_path": None,
                            "results_dir": None,
                            "error": f"Worker could not connect to IDA ICE API: {exc}",
                            "duration_sec": 0.0,
                        },
                    )
                )
            return results
        try:
            for idx, json_config in batch:
                # This block is in charge of per-case execution with one retry.
                # It is used to keep worker alive across multiple JSON cases.
                case_start = time.perf_counter()
                case_name = _derive_case_name_from_json(json_config)
                case_dir = output_cases_dir / case_name
                print("-" * 90)
                print(
                    f"[WORKER-{worker_id:02d}] CASE START {_now()} idx={idx} "
                    f"json={json_config.name} case={case_name}"
                )
                result = None
                for attempt in (1, 2):
                    try:
                        current = run_create_zones_single_case(
                            zones_json_path=json_config,
                            case_output_dir=case_dir,
                            zone_types_map=zone_types_map,
                            zone_data_map=zone_data_map,
                            run_simulations=run_simulations,
                            connect_and_disconnect=False,
                            results_reader=results_reader,
                        )
                        current["case_name"] = current.get("case_name") or case_name
                        result = current
                        if current.get("success"):
                            break
                        if attempt == 1:
                            print(f"[PHASE0-ORCHESTRATOR] Retrying once after failure: {json_config.name}")
                            try:
                                disconnect_from_ida()
                            except Exception:
                                pass
                            try:
                                exit_ida()
                            except Exception:
                                pass
                            try:
                                connect_to_ida()
                            except Exception as exc:
                                result = {
                                    "success": False,
                                    "case_name": case_name,
                                    "model_path": None,
                                    "results_dir": None,
                                    "error": f"Retry reconnect failed: {exc}",
                                    "duration_sec": 0.0,
                                }
                                break
                    except Exception as exc:
                        result = {
                            "success": False,
                            "case_name": case_name,
                            "model_path": None,
                            "results_dir": None,
                            "error": str(exc),
                            "duration_sec": 0.0,
                        }
                        if attempt == 1:
                            print(f"[PHASE0-ORCHESTRATOR] Retrying once after crash: {json_config.name}")
                            try:
                                disconnect_from_ida()
                            except Exception:
                                pass
                            try:
                                exit_ida()
                            except Exception:
                                pass
                            try:
                                connect_to_ida()
                            except Exception as reconn_exc:
                                result = {
                                    "success": False,
                                    "case_name": case_name,
                                    "model_path": None,
                                    "results_dir": None,
                                    "error": f"Retry reconnect failed after crash: {reconn_exc}",
                                    "duration_sec": 0.0,
                                }
                                break
                if result is None:
                    result = {
                        "success": False,
                        "case_name": case_name,
                        "model_path": None,
                        "results_dir": None,
                        "error": "Unknown worker failure",
                        "duration_sec": 0.0,
                    }

                print(
                    f"[WORKER-{worker_id:02d}] CASE END {_now()} case={case_name} "
                    f"success={result.get('success')} elapsed={time.perf_counter() - case_start:.1f}s"
                )
                results.append((idx, result))
                if refill_delay_sec > 0:
                    time.sleep(refill_delay_sec)
        finally:
            disconnect_from_ida()
            exit_ida()
            success_count = sum(1 for _idx, r in results if r.get("success"))
            print(
                f"[WORKER-{worker_id:02d}] END {_now()} "
                f"success={success_count}/{len(results)} log={log_path}"
            )
            print("=" * 90)
            sys.stdout = original_stdout
            sys.stderr = original_stderr
    return results


def run_phase0_parallel(
    json_configs: List[Path],
    output_cases_dir: Path,
    *,
    max_workers: int = 2,
    run_simulations: bool = False,
    initial_delay_sec: float = 1.0,
    refill_delay_sec: float = 1.0,
    reuse_connection: bool = True,
    worker_sessions: bool = False,
    results_reader: str = "auto",
) -> List[dict]:
    """
    [PHASE0 ORCHESTRATOR]
    Rolling-window parallel execution of Phase0 jobs.

    Args are the same as before, plus:
        reuse_connection: if True, the orchestrator will open one IDA
            connection before scheduling jobs and close it once all jobs
            have finished. Each job then skips its own connect/disconnect.
    """
    """
    [PHASE0 ORCHESTRATOR]
    Rolling-window parallel execution of Phase0 jobs.
    
    Each job:
    1. Reads a zones JSON config file
    2. Connects to IDA
    3. Creates zones
    4. Optionally runs simulations
    5. Saves .idm model to output_cases_dir/<case_name>/
    
    Args:
        json_configs: List of paths to zones JSON config files
        output_cases_dir: Where to save all case folders (must be discoverable by IDA Runner)
        max_workers: Max parallel IDA sessions (LIMITED BY IDA LICENSES!)
        run_simulations: Whether to run HEATING/COOLING/ENERGY in each job
        initial_delay_sec: Delay before starting first job
        refill_delay_sec: Delay between job submissions
    
    Returns:
        List of result dicts (same length as json_configs)
    """
    total = len(json_configs)
    if total == 0:
        print("[PHASE0-ORCHESTRATOR] No JSON configs found.")
        return []
    
    # DEBUG: Log orchestrator start
    print(f"\n[PHASE0-ORCHESTRATOR] Starting {total} case(s) with max_workers={max_workers}")
    print(f"[PHASE0-ORCHESTRATOR] run_simulations={run_simulations}")
    print(f"[PHASE0-ORCHESTRATOR] results_reader={results_reader}")
    print(f"[PHASE0-ORCHESTRATOR] Output cases dir: {output_cases_dir}")
    
    output_cases_dir.mkdir(parents=True, exist_ok=True)
    
    if worker_sessions and max_workers > 0:
        # This block is in charge of process-based worker orchestration.
        # It is used by the entrypoint as the default production execution mode.
        print("[PHASE0-ORCHESTRATOR] Using persistent IDA session per worker process.")
        logs_dir = output_cases_dir / "_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        print(f"[PHASE0-ORCHESTRATOR] Worker logs: {logs_dir}")
        indexed_configs = list(enumerate(json_configs))
        batches = _split_round_robin(indexed_configs, min(max_workers, total))
        results_ws: List[Optional[dict]] = [None] * total
        if initial_delay_sec > 0:
            time.sleep(initial_delay_sec)
        with cf.ProcessPoolExecutor(max_workers=min(max_workers, len(batches))) as ex:
            fut_to_batch = {
                ex.submit(
                    _run_worker_batch,
                    batch,
                    output_cases_dir,
                    worker_id=batch_idx + 1,
                    run_simulations=run_simulations,
                    refill_delay_sec=refill_delay_sec,
                    results_reader=results_reader,
                ): (batch_idx + 1, batch)
                for batch_idx, batch in enumerate(batches)
            }
            completed = 0
            for fut in cf.as_completed(fut_to_batch):
                worker_id, batch = fut_to_batch[fut]
                try:
                    worker_results = fut.result()
                except Exception as exc:
                    failed_batch = batch
                    print(
                        f"[PHASE0-ORCHESTRATOR] Worker-{worker_id:02d} process crashed; "
                        f"marking {len(failed_batch)} case(s) as failed: {exc}"
                    )
                    worker_results = []
                    for idx_failed, json_path in failed_batch:
                        worker_results.append(
                            (
                                idx_failed,
                                {
                                    "success": False,
                                    "case_name": _derive_case_name_from_json(json_path),
                                    "model_path": None,
                                    "results_dir": None,
                                    "error": f"Worker process crashed: {exc}",
                                    "duration_sec": 0.0,
                                },
                            )
                        )
                for idx_done, result in worker_results:
                    results_ws[idx_done] = result
                    completed += 1
                    status = "OK" if result.get("success") else "FAIL"
                    print(
                        f"[PHASE0-ORCHESTRATOR] Finished {completed}/{total} {status}: "
                        f"{json_configs[idx_done].name} ({result.get('duration_sec', 0):.1f}s)"
                    )
        successful_ws = sum(1 for r in results_ws if r and r.get("success"))
        print(f"\n[PHASE0-ORCHESTRATOR] Complete: {successful_ws}/{total} cases succeeded")
        return [r if r is not None else {} for r in results_ws]

    # Pre-load reference data once (efficiency optimization)
    # This block is in charge of legacy thread-mode orchestration.
    # It is used only when worker_sessions=False.
    print("[PHASE0-ORCHESTRATOR] Pre-loading zone types and data...")
    zone_types_map = load_zone_types()
    zone_data_map = load_zone_data()
    
    results: List[Optional[dict]] = [None] * total
    idx_next = 0
    in_flight: Dict[cf.Future, int] = {}
    
    # if we're reusing a single connection, make sure it's open now
    if reuse_connection and total > 0:
        print("[PHASE0-ORCHESTRATOR] Reusing single IDA connection for all jobs")
        from .ida_session import connect_to_ida
        connect_to_ida()

    def _run_and_return(idx: int, json_config: Path) -> dict:
        """Wrapper to run a Phase0 job and catch exceptions.

        After the job finishes we may have a sanitized case_name inside the
        result; if that differs from the JSON stem we rename the directory so
        that both the folder and the model share the same name.
        """
        try:
            case_name = _derive_case_name_from_json(json_config)
            case_dir = output_cases_dir / case_name

            result = run_create_zones_single_case(
                zones_json_path=json_config,
                case_output_dir=case_dir,
                zone_types_map=zone_types_map,
                zone_data_map=zone_data_map,
                run_simulations=run_simulations,
                connect_and_disconnect=not reuse_connection,
                results_reader=results_reader,
            )

            result["case_name"] = result.get("case_name") or case_name
            return result
        except Exception as e:
            # DEBUG: Log job exception
            return {
                "success": False,
                "case_name": json_config.stem,
                "model_path": None,
                "results_dir": None,
                "error": str(e),
                "duration_sec": 0.0,
            }
    
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        # Prime: submit initial batch
        while idx_next < min(max_workers, total):
            fut = ex.submit(_run_and_return, idx_next, json_configs[idx_next])
            in_flight[fut] = idx_next
            print(f"[PHASE0-ORCHESTRATOR] Started {idx_next+1}/{total}: {json_configs[idx_next].name}")
            idx_next += 1
            if initial_delay_sec > 0 and idx_next < min(max_workers, total):
                time.sleep(initial_delay_sec)
        
        # Refill as jobs complete
        while in_flight:
            done, _pending = cf.wait(in_flight.keys(), return_when=cf.FIRST_COMPLETED)
            for fut in done:
                idx_done = in_flight.pop(fut)
                result = fut.result()
                results[idx_done] = result
                
                # DEBUG: Log job completion
                status = "OK" if result.get("success") else "FAIL"
                print(f"[PHASE0-ORCHESTRATOR] Finished {idx_done+1}/{total} {status}: {json_configs[idx_done].name} ({result.get('duration_sec', 0):.1f}s)")
                
                if idx_next < total:
                    if refill_delay_sec > 0:
                        time.sleep(refill_delay_sec)
                    fut2 = ex.submit(_run_and_return, idx_next, json_configs[idx_next])
                    in_flight[fut2] = idx_next
                    print(f"[PHASE0-ORCHESTRATOR] Started {idx_next+1}/{total}: {json_configs[idx_next].name}")
                    idx_next += 1
    # after executor shuts down
    if reuse_connection:
        from .ida_session import disconnect_from_ida, exit_ida
        print("[PHASE0-ORCHESTRATOR] tearing down shared IDA connection")
        disconnect_from_ida()
        exit_ida()
    
    # DEBUG: Summary
    successful = sum(1 for r in results if r and r.get("success"))
    print(f"\n[PHASE0-ORCHESTRATOR] Complete: {successful}/{total} cases succeeded")
    return [r if r is not None else {} for r in results]
