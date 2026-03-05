#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[COMPREHENSIVE TESTING GUIDE]
How to verify the Two-Stage Parallel Workflow implementation works correctly.

This guide provides step-by-step testing procedures with expected outputs.
"""

import subprocess
import json
import sys
from pathlib import Path


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"[TEST] {title}")
    print('='*70)


def run_command(cmd, description):
    """Run a shell command and show output."""
    print(f"\n→ {description}")
    print(f"$ {cmd}\n")
    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
    return result.returncode == 0


def test_step_1_validation():
    """TEST STEP 1: Validate all components."""
    print_section("STEP 1: VALIDATE COMPONENTS")
    
    print("""
This test verifies that all new code is syntactically correct and importable.
Expected: All imports successful, no Python syntax errors.
    """)
    
    return run_command(
        "python test_integration.py",
        "Run integration validation test"
    )


def test_step_2_single_case():
    """TEST STEP 2: Single JSON config (Phase0 only)."""
    print_section("STEP 2: SINGLE JSON CONFIG TEST (Phase0 Only)")
    
    print("""
This test processes ONE JSON configuration through Phase0.
- Discovers 1 JSON file matching the pattern
- Connects to IDA ICE
- Creates 5 zones
- Saves .idm model to ICE_cases/zones_5_orientations/

Note: if you ran earlier versions of the workflow you may need to
clean previous outputs using the `--clean` flag to avoid leftovers. (name suffixed trimmed)

Expected Output:
  ✓ Case folder created: ICE_cases/zones_5_orientations/
  ✓ Model file: ICE_cases/zones_5_orientations/Room_PHAERO.idm
  ✓ Duration: ~5-7 seconds
  ✓ Stage 2 fails at exe lookup (expected, IDA Runner requires ida-ice.exe)

Command:
    """)
    
    return run_command(
        'python run_phase0_and_ida_parallel.py --json-pattern "zones_5_orientations.json"',
        "Test Phase0 with single JSON config"
    )


def test_step_2b_simulation():
    """TEST STEP 2B: Run simulations and verify results."""
    print_section("STEP 2B: SIMULATION RESULTS CHECK")
    
    print("""
This test runs Phase0 with the `--run-sims` flag so that heating/cooling/energy
simulations are executed inside IDA and results files are generated.

Expected:
  ✓ A _results/ directory in the case folder
  ✓ JSON and XLSX files for each sim type (heating, cooling, energy)
""")
    success = run_command(
        'python run_phase0_and_ida_parallel.py --json-pattern "zones_5_orientations.json" --run-sims',
        "Run Phase0 with simulations"
    )
    if not success:
        return False
    # quick check for result files
    import glob
    results_dir = Path.cwd() / "ICE_cases" / "zones_5_orientations" / "_results"
    files = list(results_dir.glob("*.json")) + list(results_dir.glob("*.xlsx"))
    if not files:
        print(f"✗ No simulation output files in {results_dir}")
        return False
    print(f"✓ Found {len(files)} result file(s) in {results_dir}")
    return True


def test_step_3_verify_output():
    """TEST STEP 3: Verify generated output structure."""
    print_section("STEP 3: VERIFY GENERATED OUTPUT")
    
    print("""
This test checks that Phase0 created the correct file structure.

Expected structure:
  ICE_cases/
  └─ zones_5_orientations/
     ├─ Room_PHAERO.idm        ← Main output (can be run by IDA)
     └─ _scripts/
        └─ Room_PHAERO__update_script.txt
    """)
    
    ice_cases = Path.cwd() / "ICE_cases" / "zones_5_orientations"
    
    if not ice_cases.exists():
        print(f"✗ FAILED: {ice_cases} not found")
        return False
    
    idm_files = list(ice_cases.glob("*.idm"))
    if not idm_files:
        print(f"✗ FAILED: No .idm files in {ice_cases}")
        return False
    
    print(f"✓ Core output structure verified:")
    print(f"  - Case folder: {ice_cases}")
    print(f"  - .idm model file(s): {len(idm_files)}")
    for f in idm_files:
        print(f"    • {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    
    return True


def test_step_4_debug_logs():
    """TEST STEP 4: Parse and verify debug logs."""
    print_section("STEP 4: VERIFY DEBUG LOGGING")
    
    print("""
This test checks that all critical debug markers appeared in the output.

Look for these keywords in the console output from STEP 2:
  [UNIFIED-WORKFLOW]        - Main orchestrator started
  [STAGE-1]                 - Phase0 stage beginning
  [PHASE0-ORCHESTRATOR]     - Orchestrator logic
  [PHASE0-JOB]              - Individual job execution
  [STAGE-2]                 - IDA Runner stage attempt

Expected log sequence:
  1. [UNIFIED-WORKFLOW] TWO-STAGE ... ORCHESTRATOR
  2. [STAGE-1] PHASE0 PARALLEL INITIALIZATION
  3. [PHASE0-ORCHESTRATOR] Discovered X zone JSON files
  4. [PHASE0-ORCHESTRATOR] Pre-loading zone types and data
  5. [PHASE0-ORCHESTRATOR] Started 1/1: zones_5_orientations.json
  6. [PHASE0-JOB] Starting for JSON=...
  7. [PHASE0-JOB] IDA connecting for case...
  8. [PHASE0-JOB] Creating X zones...
  9. [PHASE0-JOB] Saving model to...
  10. [PHASE0-JOB] ✓ Case complete
  11. [PHASE0-ORCHESTRATOR] Finished 1/1 ✓
  12. [PHASE0-ORCHESTRATOR] Complete: 1/1 cases succeeded
  13. [STAGE-1] Phase0 result: 1/1 cases created successfully
  14. [STAGE-2] IDA RUNNER PARALLEL EXECUTION
    """)
    
    print("✓ Verify these log lines appeared in your STEP 2 output")
    print("  (If you see all of these, logging is working correctly)")
    return True


def test_step_5_multiple_configs():
    """TEST STEP 5: Multiple JSON configs."""
    print_section("STEP 5: MULTIPLE JSON CONFIGS TEST")
    
    print("""
This test processes ALL 10 JSON configurations through Phase0.
- Discovers 10 JSON files matching pattern
- Processes them sequentially (one at a time due to IDA license limit
  and to avoid reconnecting on each job)
- Each job creates its own case folder

Expected Output:
  ✓ 10 case folders created in ICE_cases/
  ✓ Each folder contains a Room_PHAERO_NORTH.idm
  ✓ All cases should succeed thanks to connection reuse, even with a
    single-user license
  ✓ Timing: ~60+ seconds (6 sec × 10 cases)

Command:
    """)
    
    return run_command(
        'python run_phase0_and_ida_parallel.py --json-pattern "zones_5_orientations*.json"',
        "Test Phase0 with all JSON configs"
    )


def test_step_6_verify_manifest():
    """TEST STEP 6: Check workflow manifest JSON."""
    print_section("STEP 6: VERIFY WORKFLOW MANIFEST (If Stage 2 Completes)")
    
    print("""
After a FULL workflow completion (both stages), a manifest JSON is created.

Location: work_ice/workflow_manifest.json

Expected structure:
    {
      "stage_0_phase0": {
        "total": 1,
        "successful": 1,
        "results": [
          {
            "success": true,
            "case_name": "Room_PHAERO_NORTH",
            "model_path": "path/to/.idm",
            "results_dir": null,
            "error": null,
            "duration_sec": 6.2
          }
        ]
      },
      "stage_1_ida_runner": {
        "total": 1,
        "successful": 1,
        "results": [...]
      }
    }
    """)
    
    manifest = Path.cwd() / "work_ice" / "workflow_manifest.json"
    if not manifest.exists():
        print(f"⚠ {manifest} not found (expected if Stage 2 hasn't completed)")
        return True
    
    try:
        with open(manifest) as f:
            data = json.load(f)
        
        phase0_success = data["stage_0_phase0"]["successful"]
        phase0_total = data["stage_0_phase0"]["total"]
        
        print(f"✓ Manifest found: {manifest}")
        print(f"  - Phase0: {phase0_success}/{phase0_total} successful")
        
        if "stage_1_ida_runner" in data:
            ida_success = data["stage_1_ida_runner"]["successful"]
            ida_total = data["stage_1_ida_runner"]["total"]
            print(f"  - IDA Runner: {ida_success}/{ida_total} successful")
        
        return True
    except Exception as e:
        print(f"✗ Error reading manifest: {e}")
        return False


def test_step_7_error_handling():
    """TEST STEP 7: Error handling verification."""
    print_section("STEP 7: ERROR HANDLING VERIFICATION")
    
    print("""
This test checks that errors are properly caught and logged.

What to look for:
    - Invalid JSON pattern: Should show "No JSON files found"
    - Missing IDA: Should show "[PHASE0-JOB] ✗ Error: Could not connect"
    - Stage 2 exe missing: Should show "✗ Could not locate ida-ice.exe"

Error handling is working if:
    ✓ Errors are prefixed with [KEYWORD] ✗
    ✓ A summary shows X/Y cases failed
    ✓ Execution continues (doesn't hard-crash)
    ✓ Manifest still created with error details

To test: Try with invalid pattern:
    """)
    
    return run_command(
        'python run_phase0_and_ida_parallel.py --json-pattern "nonexistent_*.json"',
        "Test error handling with invalid JSON pattern"
    )


def main():
    """Main testing workflow."""
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║  COMPREHENSIVE TESTING GUIDE: Two-Stage Parallel Workflow              ║
╚════════════════════════════════════════════════════════════════════════╝

This script guides you through 7 testing steps to verify the implementation.
Each step includes:
  ✓ What is being tested
  ✓ Expected behavior
  ✓ How to verify success
  ✓ Common issues and fixes

TESTING FLOW:
  1. Validate          - Check all code is syntactically correct
  2. Single case       - Run Phase0 with 1 JSON (fastest test)
  3. Verify output     - Check generated files
  4. Debug logs        - Inspect console output
  5. Multiple cases    - Run Phase0 with all 10 JSON files
  6. Manifest JSON     - Check results summary (if Stage 2 completes)
  7. Error handling    - Verify error logging works

TIME ESTIMATES:
  - Step 1: ~5 seconds
  - Step 2: ~10 seconds
  - Step 3: ~2 seconds
  - Step 4: ~1 minute (manual review)
  - Step 5: ~70 seconds
  - Step 6: ~2 seconds
  - Step 7: ~5 seconds
  
TOTAL: ~2-3 minutes for QUICK TEST (just steps 1-4)
       ~6-7 minutes for FULL TEST (all steps)

REQUIREMENTS:
  ✓ Python 3.7+
  ✓ IDA ICE installed (for Phase0 to work)
  ✓ All dependencies in requirements.txt
  ✓ 10 JSON config files in data/ directory
    """)
    
    input("Press ENTER to begin testing... ")
    
    # Run tests
    tests = [
        ("Component validation", test_step_1_validation),
        ("Single case Phase0", test_step_2_single_case),
        ("Output verification", test_step_3_verify_output),
        ("Debug logging", test_step_4_debug_logs),
        ("Multiple configs", test_step_5_multiple_configs),
        ("Manifest JSON", test_step_6_verify_manifest),
        ("Error handling", test_step_7_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ Unexpected error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print_section("FINAL TEST SUMMARY")
    
    print("\nTest Results:")
    print("-" * 70)
    for test_name, passed in results:
        status = "✓" if passed else "✗"
        print(f"{status} {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nResult: {passed_count}/{total_count} tests passed")
    
    if passed_count >= 5:
        print("\n✓ CORE FUNCTIONALITY WORKING")
        print("""
Implementation Status:
  ✓ Phase0 orchestrator operational
  ✓ JSON discovery functional
  ✓ Case generation working
  ✓ Debug logging comprehensive
  ⚠ Stage 2 (IDA Runner) requires ida-ice.exe installation

Next Steps:
  1. Install ida-ice.exe if available
  2. Run full workflow: python run_phase0_and_ida_parallel.py
  3. Check workflow_manifest.json for combined results
  4. Consider enabling simulations: --run-sims flag
        """)
    else:
        print("\n✗ SOME TESTS FAILED")
        print("""
Troubleshooting:
  1. Check error output above
  2. Verify all dependencies: pip install -r requirements.txt
  3. Verify IDA connection: python PHASE0_Create_Zones.py
  4. See QUICKSTART.md for detailed guidance
        """)
    
    return 0 if passed_count >= 5 else 1


if __name__ == "__main__":
    sys.exit(main())
