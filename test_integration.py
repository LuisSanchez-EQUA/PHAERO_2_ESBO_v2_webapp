#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[INTEGRATION TEST SCRIPT]
Validates the Two-Stage Parallel Workflow Implementation

This script:
1. Checks all required modules are present
2. Verifies import paths
3. Tests Phase0 discovery
4. Validates orchestrator signature
5. Confirms JSON pattern matching
"""

import sys
from pathlib import Path

def test_imports():
    """Test all required modules can be imported."""
    print("[TEST] Checking imports...")
    modules_to_test = [
        ("phase0.workflows", ["run_create_zones_single_case", "run_create_zones"]),
        ("phase0.orchestrator", ["discover_zone_json_files", "run_phase0_parallel"]),
        ("ida_suite_runner.cli", ["main"]),
        ("ida_suite_runner.orchestrator", ["run_suite_parallel"]),
    ]
    
    for module_name, expected_funcs in modules_to_test:
        try:
            mod = __import__(module_name, fromlist=expected_funcs)
            for func in expected_funcs:
                if not hasattr(mod, func):
                    print(f"  ✗ {module_name}.{func} not found")
                    return False
            print(f"  ✓ {module_name}")
        except Exception as e:
            print(f"  ✗ {module_name}: {e}")
            return False
    
    return True


def test_json_discovery():
    """Test JSON config discovery."""
    print("\n[TEST] Checking JSON config discovery...")
    from phase0.orchestrator import discover_zone_json_files
    
    data_dir = Path.cwd() / "data"
    jsons = discover_zone_json_files(data_dir, include_pattern="zones_5_orientations*.json")
    
    if len(jsons) < 10:
        print(f"  ✗ Expected ≥10 JSON files, found {len(jsons)}")
        return False
    
    print(f"  ✓ Discovered {len(jsons)} JSON config files")
    return True


def test_output_dirs():
    """Test output directory creation."""
    print("\n[TEST] Checking output directory requirements...")
    required_dirs = [
        "data",
        "Starting_Case",
        "phase0",
        "ida_suite_runner",
    ]
    
    for dirname in required_dirs:
        p = Path.cwd() / dirname
        if not p.exists():
            print(f"  ✗ {dirname} not found")
            return False
        print(f"  ✓ {dirname}")
    
    return True


def test_entrypoint():
    """Test unified entrypoint exists and is executable."""
    print("\n[TEST] Checking unified entrypoint...")
    
    entrypoint = Path.cwd() / "run_phase0_and_ida_parallel.py"
    if not entrypoint.exists():
        print(f"  ✗ {entrypoint} not found")
        return False
    
    print(f"  ✓ {entrypoint} exists")
    
    # Try to import it
    try:
        import run_phase0_and_ida_parallel  # noqa
        print(f"  ✓ Entrypoint is importable")
    except Exception as e:
        print(f"  ✗ Cannot import entrypoint: {e}")
        return False
    
    return True


def test_ice_cases_dir():
    """Test that ICE_cases directory structure is present."""
    print("\n[TEST] Checking generated ICE_cases structure...")
    
    ice_cases = Path.cwd() / "ICE_cases"
    if not ice_cases.exists():
        print(f"  ⚠ {ice_cases} not created yet (will be created on first run)")
        return True
    
    case_dirs = list(ice_cases.glob("zones_5_orientations*"))
    if len(case_dirs) > 0:
        print(f"  ✓ Found {len(case_dirs)} case folder(s)")
        for case_dir in case_dirs:
            idm_files = list(case_dir.glob("*.idm"))
            if idm_files:
                print(f"    ✓ {case_dir.name}: {len(idm_files)} .idm file(s)")
            else:
                print(f"    ⚠ {case_dir.name}: no .idm files yet")
    else:
        print(f"  ⚠ No case folders found (expected after Phase0 runs)")
    
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("[INTEGRATION TEST] Two-Stage Parallel Workflow")
    print("=" * 70)
    
    tests = [
        ("Output directories", test_output_dirs),
        ("Module imports", test_imports),
        ("JSON discovery", test_json_discovery),
        ("Unified entrypoint", test_entrypoint),
        ("Generated structure", test_ice_cases_dir),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 70)
    print("[TEST SUMMARY]")
    print("=" * 70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for test_name, passed_test in results:
        status = "✓" if passed_test else "✗"
        print(f"{status} {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Ready for workflow execution.")
        print(f"\nNext steps:")
        print(f"  1. Single case test:")
        print(f"     python run_phase0_and_ida_parallel.py --json-pattern 'zones_5_orientations.json'")
        print(f"\n  2. Multiple case test:")
        print(f"     python run_phase0_and_ida_parallel.py --json-pattern 'zones_5_orientations - v*.json'")
        return 0
    else:
        print("\n✗ Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
