# -*- coding: utf-8 -*-
"""
IDA .idm script builder.


"""

from __future__ import annotations

from pathlib import Path

from .ida_types import Job 


def _lisp_bool(value: bool) -> str:
    return ":TRUE" if bool(value) else ":FALSE"


def _build_select_output_form(
    *,
    temperatures: bool = True,
    heat_balance: bool = True,
    comfort_indices: bool = True,
    iaq: bool = True,
    light_cond: bool = True,
    shadingon: bool = True,
) -> str:
    return (
        "(:UPDATE [doc_]\n"
        "    ((OUTPUT-CONTROL :N OUTPUT)\n"
        f"    (:PAR :N TEMPERATURES     :V {_lisp_bool(temperatures)}     :S '(:DEFAULT NIL 2))\n"
        f"    (:PAR :N HEAT_BALANCE     :V {_lisp_bool(heat_balance)}     :S '(:DEFAULT NIL 2))\n"
        f"    (:PAR :N COMFORT_INDICES  :V {_lisp_bool(comfort_indices)}  :S '(:DEFAULT NIL 2))\n"
        f"    (:PAR :N IAQ              :V {_lisp_bool(iaq)}              :S '(:DEFAULT NIL 2))\n"
        f"    (:PAR :N LIGHT_COND       :V {_lisp_bool(light_cond)}       :S '(:DEFAULT NIL 2))\n"
        f"    (:PAR :N SHADINGON        :V {_lisp_bool(shadingon)}        :S '(:DEFAULT NIL 2))))"
    )


def _lisp_escape_path(p: Path) -> str:
    """
    Escape backslashes for a literal string in the .idm script.

    """
    return str(p).replace("\\", "\\\\")





def build_ida_script(job: Job,idm_for_run: Path,*,tunnel_or_road_mode: bool) -> Path:
    """
    Create a .idm bootstrap in job.work_dir

    - ICE: ice-run-building-ex or ESBO special energy run
    - Writes with Windows ANSI (cp1252) to avoid Unicode mangling

    Returns the path to the created .idm script.
    """
    job.work_dir.mkdir(parents=True, exist_ok=True)

    ida_script = job.work_dir / "ida_app_script.idm"
    log_file   = job.work_dir / "log.txt"
    output_txt = job.work_dir / "output.txt"
    temp_root  = job.work_dir

    e_log  = _lisp_escape_path(log_file)
    e_temp = _lisp_escape_path(temp_root)
    e_idm  = _lisp_escape_path(idm_for_run)
    e_out  = _lisp_escape_path(output_txt)
    case_name = job.idm_source.stem
    run_form = "( :call esbo-run-load-sim-ex [doc_ simulations heating])"
    select_output_form = _build_select_output_form()

    content = (
        f'( :batch >> "{e_log}"\n'
        f'  ( :set doc_ (:call get-document "{e_idm}") )\n'     #shifted rows the row below to avoid race conditions..
        f'  ( setf-temp-folder "{e_temp}" )\n'
        f'  {select_output_form}\n'
        f'  {run_form}\n'
        f'  ( save-document doc_ )\n'
        f'  ( :set f_ ( :call open "{e_out}" :direction :output ) )\n'
        f'  ( format f_ "status=done~%" )\n'
        f'  ( format f_ "case_name={case_name}~%" )\n'
        f'  ( format f_ "simulation_mode=heating~%" )\n'
        f'  ( format f_ "model_path={e_idm}~%" )\n'
        f'  ( format f_ "work_dir={e_temp}~%" )\n'
        f'  ( format f_ "period=~A~%" [doc_ project_report period] )\n'
        f'  ( :call close f_ )\n'
        f'  ( exit-ida )\n'
        f')\n'
    )
    # to deal with special characters in case names..
    ida_script.write_text(content, encoding="cp1252", errors="replace")
    print(f"  ✓ Created IDA script: {ida_script}")
    return ida_script
