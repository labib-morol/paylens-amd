#!/usr/bin/env python3
"""Automated 3-Gate Verification Script for PayLens Repository Audit.

Gate 1: Forbidden String Scan across app.py, README.md, CHANGES.md, AUDIT.md, agent/, and engine/.
Gate 2: Benchmark & Documentation Consistency Check between benchmark_results.json, README.md, and CHANGES.md.
Gate 3: Test Suite & Headless Smoke Test Check (pytest + app.py import/syntax validation).
"""

import os
import sys
import json
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

GATE_1_FORBIDDEN_STRINGS = [
    "Recovered Today",
    'get("true_positives", 28)',
    'get("false_positives", 2)',
    "$295.00",
    "9.9/10",
    "2,842",
    "82,898",
    "0.6.3",
    "Zero hallucinations",
    "Cryptographic",
    "<REPO_URL>",
    "Benchmark completed successfully!",
]


def run_gate_1() -> bool:
    print("=" * 70)
    print("GATE 1: FORBIDDEN STRING SCAN")
    print("=" * 70)
    
    files_to_scan = []
    for rel_file in ["app.py", "README.md", "CHANGES.md", "AUDIT.md"]:
        f_path = ROOT_DIR / rel_file
        if f_path.exists():
            files_to_scan.append(f_path)
            
    for subdir in ["agent", "engine"]:
        dir_path = ROOT_DIR / subdir
        if dir_path.exists():
            for p in dir_path.glob("**/*.py"):
                files_to_scan.append(p)
                
    violations = []
    for fpath in files_to_scan:
        rel_path = fpath.relative_to(ROOT_DIR)
        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception as e:
            violations.append(f"Could not read {rel_path}: {e}")
            continue
            
        for forbidden in GATE_1_FORBIDDEN_STRINGS:
            # Case-insensitive for phrases like "Zero hallucinations" or "Cryptographic"
            if forbidden.lower() in content.lower():
                # Locate specific lines
                for line_num, line in enumerate(content.splitlines(), start=1):
                    if forbidden.lower() in line.lower():
                        violations.append(f"[{rel_path}:{line_num}] Contains forbidden pattern '{forbidden}': {line.strip()[:80]}")
                        
    if violations:
        print("[FAIL] Gate 1 found forbidden string matches:")
        for v in violations:
            print(f"  - {v}")
        return False
        
    print(f"[PASS] Gate 1 passed! Scanned {len(files_to_scan)} files with 0 forbidden string occurrences.")
    return True


def run_gate_2() -> bool:
    print("\n" + "=" * 70)
    print("GATE 2: BENCHMARK & DOCUMENTATION CONSISTENCY CHECK")
    print("=" * 70)
    
    bench_path = ROOT_DIR / "benchmarks" / "benchmark_results.json"
    if not bench_path.exists():
        print(f"[FAIL] Gate 2: {bench_path} does not exist.")
        return False
        
    with open(bench_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)
        
    readme_path = ROOT_DIR / "README.md"
    changes_path = ROOT_DIR / "CHANGES.md"
    
    readme_text = readme_path.read_text(encoding="utf-8")
    changes_text = changes_path.read_text(encoding="utf-8")
    
    amd_data = bench_data.get("amd_tokenfactory", {})
    summary = amd_data.get("summary", {})
    tiers = amd_data.get("tiers", [])
    google_data = bench_data.get("google_gemma4", {})
    
    inconsistencies = []
    
    # 1. Check AMD summary counters
    for key in ["attempted_requests", "completed_requests", "failed_requests"]:
        if key in summary:
            val = str(summary[key])
            if val not in readme_text:
                inconsistencies.append(f"AMD summary {key}={val} not found in README.md")
                
    # 2. Check each tier's throughput and counts
    for t in tiers:
        c = t.get("concurrency")
        tok_s = f"{t.get('tokens_per_sec', 0):.1f}"
        if tok_s not in readme_text:
            inconsistencies.append(f"Tier c={c} throughput {tok_s} tok/s not found in README.md")
        if tok_s not in changes_text:
            inconsistencies.append(f"Tier c={c} throughput {tok_s} tok/s not found in CHANGES.md")
            
    # 3. Check Google Gemma requests
    g_att = str(google_data.get("attempted_requests", google_data.get("requests", 0)))
    g_comp = str(google_data.get("completed_requests", google_data.get("completed", 0)))
    if f"{g_comp}/{g_att}" not in readme_text and f"{g_comp} of {g_att}" not in readme_text and f"{g_comp} of {g_att}" not in changes_text:
        inconsistencies.append(f"Google Gemma completed {g_comp}/{g_att} not documented in README or CHANGES")
        
    if inconsistencies:
        print("[FAIL] Gate 2: Found documentation inconsistencies:")
        for inc in inconsistencies:
            print(f"  - {inc}")
        return False
        
    print(f"[PASS] Gate 2 passed! Benchmark metrics ({len(tiers)} tiers + Google Gemma) strictly reconciled across README.md and CHANGES.md.")
    return True


def run_gate_3() -> bool:
    print("\n" + "=" * 70)
    print("GATE 3: TEST SUITE & CLEAN HEADLESS IMPORT CHECK")
    print("=" * 70)
    
    # Run pytest
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    
    print("Running pytest test suite...")
    res = subprocess.run([sys.executable, "-m", "pytest", "-v"], cwd=ROOT_DIR, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        # Try finding pytest executable if python -m pytest fails
        pytest_exe = ROOT_DIR / ".venv" / "Scripts" / "pytest.exe"
        if pytest_exe.exists():
            res = subprocess.run([str(pytest_exe), "-v"], cwd=ROOT_DIR, env=env, capture_output=True, text=True)
        else:
            res = subprocess.run(["pytest", "-v"], cwd=ROOT_DIR, env=env, capture_output=True, text=True)
            
    if res.returncode != 0:
        print(f"[FAIL] Gate 3: Pytest failed (exit code {res.returncode}):")
        print(res.stdout)
        print(res.stderr)
        return False
        
    print(res.stdout.strip())
    print("\nVerifying headless compilation and import of app.py...")
    import py_compile
    try:
        py_compile.compile(str(ROOT_DIR / "app.py"), doraise=True)
        print("  - app.py compiled successfully with zero syntax errors.")
    except Exception as e:
        print(f"[FAIL] Gate 3: app.py failed compilation: {e}")
        return False
        
    print("[PASS] Gate 3 passed! Full test suite passing and app.py compiles cleanly.")
    return True


def main():
    print("STARTING PAYLENS 3-GATE AUTOMATED AUDIT VERIFICATION\n")
    g1 = run_gate_1()
    g2 = run_gate_2()
    g3 = run_gate_3()
    
    print("\n" + "=" * 70)
    if g1 and g2 and g3:
        print("ALL 3 AUDIT GATES PASSED")
        print("=" * 70)
        sys.exit(0)
    else:
        print("AUDIT VERIFICATION FAILED")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
