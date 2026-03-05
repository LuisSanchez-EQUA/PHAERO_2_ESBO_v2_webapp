# -*- coding: utf-8 -*-
"""
Post-run result extraction helpers.

Stage 3 works only from files produced by Stage 2. It does not require a live
IDA connection. The extractor reuses the Phase0 PRN readers to normalize and
export timeseries plus a compact summary per case.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from phase0.simulation import format_change, ida_read


def _parse_output_metadata(output_txt: Path) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    if not output_txt.exists():
        return metadata

    for raw in output_txt.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def _collect_log_summary(log_txt: Path) -> Dict[str, object]:
    summary = {
        "log_exists": log_txt.exists(),
        "start_count": 0,
        "end_count": 0,
        "missing_output_warnings": 0,
        "last_lines": [],
    }
    if not log_txt.exists():
        return summary

    lines = log_txt.read_text(encoding="utf-8", errors="ignore").splitlines()
    summary["start_count"] = sum("Start of simulation" in line for line in lines)
    summary["end_count"] = sum("End of simulation" in line for line in lines)
    summary["missing_output_warnings"] = sum(
        ("Missing " in line) or ("missing:" in line.lower())
        for line in lines
    )
    summary["last_lines"] = [line for line in lines[-8:] if line.strip()]
    return summary


def _safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _detect_mode_from_path(prn_path: Path) -> str:
    for part in prn_path.parts:
        lowered = part.lower()
        if lowered in {"heating", "cooling", "energy"}:
            return lowered
    return "unknown"


def _find_output_root(work_dir: Path) -> Optional[Path]:
    direct = work_dir / work_dir.name
    if direct.exists():
        return direct

    candidates: List[Path] = []
    for prn in work_dir.rglob("*.prn"):
        parent = prn.parent
        mode = parent.name.lower()
        if mode in {"heating", "cooling", "energy"}:
            candidates.append(parent.parent)
    if not candidates:
        return None
    candidates.sort(key=lambda path: len(path.parts))
    return candidates[0]


def _classify_prn(prn_path: Path) -> Tuple[str, str]:
    parts = prn_path.name.split(".")
    if len(parts) < 2:
        return prn_path.stem, "unknown"
    zone_name = parts[0]
    data_name = ".".join(parts[1:-1]) if len(parts) > 2 else "unknown"
    return zone_name, data_name


def _is_case_zone(case_name: str, zone_name: str) -> bool:
    return zone_name == case_name or zone_name.startswith(f"{case_name}_")


def _get_export_bucket(case_name: str, zone_name: str) -> str:
    return "ZONES" if _is_case_zone(case_name, zone_name) else "OTHERS"


def _zone_export_dir(export_root: Path, case_name: str, zone_name: str) -> Path:
    bucket = _get_export_bucket(case_name, zone_name)
    return export_root / bucket / zone_name


def _export_timeseries(prn_path: Path, export_root: Path, case_name: str) -> Dict[str, object]:
    df = ida_read(str(prn_path))
    df_ts, columns = format_change(df)

    mode = _detect_mode_from_path(prn_path)
    zone_name, data_name = _classify_prn(prn_path)
    safe_name = prn_path.stem.replace(".", "__")
    bucket = _get_export_bucket(case_name, zone_name)
    target_dir = _zone_export_dir(export_root, case_name, zone_name) / mode
    target_dir.mkdir(parents=True, exist_ok=True)
    prn_copy_path = target_dir / prn_path.name
    csv_path = target_dir / f"{safe_name}.csv"
    json_path = target_dir / f"{safe_name}.json"

    shutil.copy2(prn_path, prn_copy_path)
    df_ts.to_csv(csv_path)
    df_ts.reset_index().to_json(json_path, orient="records", date_format="iso")

    summary = {
        "source_prn": str(prn_path),
        "mode": mode,
        "group": bucket,
        "zone_name": zone_name,
        "data_name": data_name,
        "rows": int(len(df_ts)),
        "columns": [str(col) for col in columns],
        "prn_path": str(prn_copy_path),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "stats": {},
    }

    numeric_columns = [col for col in df_ts.columns]
    stats: Dict[str, Dict[str, Optional[float]]] = {}
    for col in numeric_columns:
        series = df_ts[col]
        stats[str(col)] = {
            "min": _safe_float(series.min()),
            "max": _safe_float(series.max()),
            "mean": _safe_float(series.mean()),
        }
    summary["stats"] = stats
    return summary


def _classify_png(png_path: Path) -> str:
    return png_path.name.split(".", 1)[0]


def _export_pngs(output_root: Optional[Path], export_root: Path, case_name: str) -> List[str]:
    if output_root is None or not output_root.exists():
        return []

    exported_paths: List[str] = []
    for png_path in sorted(output_root.glob("*.png")):
        zone_name = _classify_png(png_path)
        target_dir = _zone_export_dir(export_root, case_name, zone_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / png_path.name
        shutil.copy2(png_path, target_path)
        exported_paths.append(str(target_path))
    return exported_paths


def _collect_pngs(output_root: Optional[Path]) -> List[str]:
    if output_root is None or not output_root.exists():
        return []
    return [str(path) for path in sorted(output_root.glob("*.png"))]


def _load_existing_summary(work_dir: Path) -> Optional[Dict[str, object]]:
    summary_path = work_dir / "results_summary.json"
    if not summary_path.exists():
        return None
    try:
        with open(summary_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def _export_summary_reports(work_dir: Path, output_metadata: Dict[str, str], export_root: Path) -> Dict[str, object]:
    model_path = Path(output_metadata.get("model_path", "")).expanduser()
    if not model_path.exists():
        fallback_model = work_dir / f"{work_dir.name}.idm"
        model_path = fallback_model if fallback_model.exists() else model_path

    if not model_path.exists():
        return {
            "success": False,
            "error": f"Model file not found for report export: {model_path}",
        }

    reports_dir = export_root / "_reports"
    json_path = reports_dir / f"{work_dir.name}_summary_reports.json"
    excel_path = reports_dir / f"{work_dir.name}_summary_reports.xlsx"

    script = "\n".join(
        [
            "import json",
            "from pathlib import Path",
            "from phase0.ida_session import connect_to_ida, disconnect_from_ida, exit_ida, open_model",
            "from phase0.simulation import get_results",
            f"model = Path(r'''{str(model_path)}''')",
            f"outdir = Path(r'''{str(reports_dir)}''')",
            f"json_name = r'''{json_path.name}'''",
            f"excel_name = r'''{excel_path.name}'''",
            "result = {'ok': False, 'error': None}",
            "try:",
            "    connect_to_ida()",
            "    try:",
            "        outdir.mkdir(parents=True, exist_ok=True)",
            "        building = open_model(model)",
            "        get_results(building, output_dir=outdir, json_filename=json_name, excel_filename=excel_name)",
            "        result['ok'] = True",
            "    finally:",
            "        disconnect_from_ida()",
            "        exit_ida()",
            "except Exception as exc:",
            "    result['error'] = str(exc)",
            "print('REPORT_EXPORT_RESULT=' + json.dumps(result, ensure_ascii=False))",
        ]
    )

    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=240,
        )
        marker_line = None
        for line in reversed((proc.stdout or "").splitlines()):
            if line.startswith("REPORT_EXPORT_RESULT="):
                marker_line = line
                break
        if marker_line:
            payload = json.loads(marker_line.split("=", 1)[1])
            if payload.get("ok") and json_path.exists() and excel_path.exists():
                return {
                    "success": True,
                    "model_path": str(model_path),
                    "json_path": str(json_path),
                    "excel_path": str(excel_path),
                    "report_names": ["ZONE-SUMMARY", "PEAK-SUMMARY"],
                }
            error_message = payload.get("error") or "Unknown report export error."
        else:
            error_message = (proc.stderr or proc.stdout or "").strip() or "No report export marker returned."
    except Exception as exc:
        error_message = str(exc)

    if not json_path.exists() and reports_dir.exists():
        try:
            reports_dir.rmdir()
        except Exception:
            pass

    return {
        "success": False,
        "model_path": str(model_path),
        "json_path": str(json_path),
        "excel_path": str(excel_path),
        "error": error_message,
    }


def extract_case_results(work_dir: Path) -> Dict[str, object]:
    output_txt = work_dir / "output.txt"
    log_txt = work_dir / "log.txt"
    output_root = _find_output_root(work_dir)
    extracted_root = work_dir / "_extracted"
    extracted_root.mkdir(parents=True, exist_ok=True)
    output_metadata = _parse_output_metadata(output_txt)

    prn_summaries: List[Dict[str, object]] = []
    prn_files: List[Path] = []
    if output_root and output_root.exists():
        prn_files = sorted(output_root.rglob("*.prn"))
    elif not output_root:
        existing = _load_existing_summary(work_dir)
        if existing and isinstance(existing.get("modes"), dict) and existing.get("total_prn_files", 0):
            return existing

    by_mode: Dict[str, Dict[str, object]] = {}
    for prn_path in prn_files:
        try:
            summary = _export_timeseries(prn_path, extracted_root, work_dir.name)
        except Exception as exc:
            zone_name, data_name = _classify_prn(prn_path)
            summary = {
                "source_prn": str(prn_path),
                "mode": _detect_mode_from_path(prn_path),
                "group": _get_export_bucket(work_dir.name, zone_name),
                "zone_name": zone_name,
                "data_name": data_name,
                "error": str(exc),
            }
        prn_summaries.append(summary)

        mode = str(summary.get("mode", "unknown"))
        mode_bucket = by_mode.setdefault(
            mode,
            {
                "file_count": 0,
                "zone_names": set(),
                "other_names": set(),
                "data_names": set(),
                "files": [],
            },
        )
        mode_bucket["file_count"] = int(mode_bucket["file_count"]) + 1
        zone_name = summary.get("zone_name")
        data_name = summary.get("data_name")
        group = summary.get("group")
        if isinstance(zone_name, str):
            if group == "ZONES":
                mode_bucket["zone_names"].add(zone_name)
            else:
                mode_bucket["other_names"].add(zone_name)
        if isinstance(data_name, str):
            mode_bucket["data_names"].add(data_name)
        mode_bucket["files"].append(summary)

    modes: Dict[str, object] = {}
    for mode, payload in by_mode.items():
        modes[mode] = {
            "file_count": payload["file_count"],
            "zone_count": len(payload["zone_names"]),
            "zones": sorted(payload["zone_names"]),
            "other_count": len(payload["other_names"]),
            "others": sorted(payload["other_names"]),
            "data_series": sorted(payload["data_names"]),
            "files": payload["files"],
        }

    summary = {
        "case_name": work_dir.name,
        "work_dir": str(work_dir),
        "output_root": str(output_root) if output_root else None,
        "output_root_exists": bool(output_root and output_root.exists()),
        "output_metadata": output_metadata,
        "log_summary": _collect_log_summary(log_txt),
        "png_files": _export_pngs(output_root, extracted_root, work_dir.name),
        "source_png_files": _collect_pngs(output_root),
        "total_prn_files": len(prn_files),
        "report_exports": _export_summary_reports(work_dir, output_metadata, extracted_root),
        "modes": modes,
    }

    summary_path = work_dir / "results_summary.json"
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    summary["summary_path"] = str(summary_path)

    if output_root and output_root.exists() and output_root.parent == work_dir:
        shutil.rmtree(output_root)

    return summary


def extract_suite_results(work_root: Path, ida_results: List[dict]) -> List[dict]:
    summaries: List[dict] = []
    for result in ida_results:
        log_txt = result.get("log_txt")
        output_txt = result.get("output_txt")
        work_dir: Optional[Path] = None
        if log_txt:
            work_dir = Path(log_txt).parent
        elif output_txt:
            work_dir = Path(output_txt).parent
        if not work_dir or not work_dir.exists():
            continue
        case_summary = extract_case_results(work_dir)
        case_summary["run_status"] = "success" if result.get("pid", -1) >= 0 else "failed"
        summaries.append(case_summary)

    suite_summary_path = work_root / "results_summary.json"
    with open(suite_summary_path, "w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2, ensure_ascii=False)
    return summaries
