# Simplified Workflow (3 Stages)

This project follows a **3-stage approach** for each case.

## Stage 1: Build Case

- Read one `zones_*.json`.
- Derive the target case name (for example `Room_PHAERO_1`).
- Open the seed model from `Starting_Case/`.
- Create/update all zones in the model.
- Save `<case>.idm`.

Output after Stage 1:
- `work_ice/<case>/<case>.idm`
- `work_ice/<case>/_scripts/...`

## Stage 2: Run Simulations

- Use the same IDA session (per worker) to run:
  - `HEATING`
  - `COOLING`
  - `ENERGY`
- IDA writes simulation artifacts (PRN/PNG and sim subfolders) into:
  - `work_ice/<case>/<case>/...`

Output after Stage 2:
- `work_ice/<case>/<case>/heating/*.prn`
- `work_ice/<case>/<case>/cooling/*.prn`
- `work_ice/<case>/<case>/energy/*.prn`
- `work_ice/<case>/<case>/*.ROOM-VIEW.png`

## Stage 3: Extract Reports

- Read report nodes from IDA and export structured tables:
  - JSON
  - Excel
- Files are saved in:
  - `work_ice/<case>/_results/`

Important rule:
- For `ENERGY`, export uses only `ZONE-SUMMARY` (no `PEAK-SUMMARY`).
- Reader modes:
  - `auto`: try `printReport`, fallback to node traversal.
  - `print`: force `printReport`.
  - `node`: skip `printReport`, direct node traversal only.

---

## Parallel Behavior

- The runner uses worker processes.
- Each worker has its own IDA session/process.
- One case can be retried once automatically after a crash.
- Simulation can retry once if expected outputs are missing (for example missing PRN on first attempt).
- Worker logs are written to `work_ice/_logs/worker_XX.txt`.

## Recommended Run

```powershell
python run_phase0_and_ida_parallel.py --json-pattern "zones_*.json" --workers 2 --results-reader auto
```

For clean tests, avoid stale folders:
- run without `--keep-prev-results`.
- or pass `--discard-prev-results` explicitly.
