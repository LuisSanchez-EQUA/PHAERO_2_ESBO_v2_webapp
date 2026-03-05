# -*- coding: utf-8 -*-
"""
Single-job runner.

"""

from __future__ import annotations

import os
import subprocess
import time
from typing import List

from .ida_types import Job, LaunchConfig
from .launcher import build_command
from .monitor import detect_done_markers, get_psutil_process, sample_psutil
from .scripts import build_ida_script
from .staging import materialize_case_to_work


def _has_valid_completion(job: Job) -> bool:
    note = detect_done_markers(job.work_dir)
    if note:
        return True

    output_txt = job.work_dir / "output.txt"
    if not output_txt.exists():
        return False

    try:
        text = output_txt.read_text(encoding="utf-8", errors="ignore")
        return "status=done" in text or "Done " in text
    except Exception:
        return False


def run_job(job: Job, cfg: LaunchConfig, tunnel_or_road_mode: bool) -> dict:
    t0 = time.time()
    notes: List[str] = []

    idm_copied = materialize_case_to_work(job, cfg)
    script_path = build_ida_script(job, idm_copied, tunnel_or_road_mode=tunnel_or_road_mode)
    per_title = job.title or cfg.cli.window_title or "IDA Job"

    cmd = build_command(cfg, script_path, per_title)
    (job.work_dir / "command_log.txt").write_text(subprocess.list2cmdline(cmd), encoding="utf-8")

    proc = subprocess.Popen(
        cmd,
        cwd=str(cfg.exe_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )

    worker_pid = proc.pid
    notes.append(f"Spawned PID: {worker_pid}")

    done_detected = False
    last_active = time.time()
    peak_cpu = 0.0
    max_rss_mb = 0.0

    psproc = get_psutil_process(worker_pid)
    have_psutil = psproc is not None

    while True:
        if proc.poll() is not None:
            notes.append("Process exited.")
            break

        if have_psutil and psproc is not None:
            cpu, mem = sample_psutil(psproc)
            peak_cpu = max(peak_cpu, cpu)
            max_rss_mb = max(max_rss_mb, mem)
            if cpu > 1.0:
                last_active = time.time()
        else:
            time.sleep(0.5)

        note = detect_done_markers(job.work_dir)
        if note:
            notes.append(note)
            done_detected = True
            break

        if time.time() - last_active > cfg.idle_terminate_after:
            notes.append(f"Idle > {cfg.idle_terminate_after}s - terminating.")
            break

        time.sleep(0.5)

    if proc.poll() is None and done_detected:
        notes.append(f"Waiting {cfg.monitor_grace_after_done}s for natural exit...")
        t_grace = time.time() + cfg.monitor_grace_after_done
        while time.time() < t_grace and proc.poll() is None:
            time.sleep(1)

    if proc.poll() is None:
        notes.append("Process still alive - terminating.")
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    completed = _has_valid_completion(job)
    if not completed:
        notes.append("Missing completion marker/output.txt; simulation did not finish cleanly.")

    t1 = time.time()
    return {
        "pid": worker_pid if completed else -1,
        "duration_sec": round(t1 - t0, 2),
        "peak_cpu_percent": round(peak_cpu, 2),
        "max_rss_mb": round(max_rss_mb, 2),
        "notes": notes,
        "output_txt": str(job.work_dir / "output.txt"),
        "log_txt": str(job.work_dir / "log.txt"),
        "cmd": (job.work_dir / "command_log.txt").read_text(encoding="utf-8", errors="ignore"),
    }
