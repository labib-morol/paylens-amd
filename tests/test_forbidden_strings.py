"""Test that verifies app.py and README.md contain ZERO forbidden claims or strings."""
from pathlib import Path
import pytest

FORBIDDEN_STRINGS = [
    "100%",
    "Zero-Hallucination",
    "0 Hallucinations",
    "guarantee",
    "Cryptographic",
    "Autonomous",
    "$5,000",
    "€",
    "1,286",
    "82,898",
    "70,658",
    "2,842",
    "2,843",
]

ROOT_DIR = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("filename", ["app.py", "README.md", "PROGRESS.md"])
def test_no_forbidden_strings_in_core_files(filename):
    filepath = ROOT_DIR / filename
    assert filepath.exists(), f"File {filename} does not exist"

    content = filepath.read_text(encoding="utf-8")
    violations = []

    for forbidden in FORBIDDEN_STRINGS:
        if forbidden.lower() in content.lower():
            # Find line numbers
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                if forbidden.lower() in line.lower():
                    # Allow verified telemetry indicator "Clean First Pass (100%)"
                    if forbidden == "100%" and "clean first pass" in line.lower():
                        continue
                    violations.append(f"{filename}:{idx} contains '{forbidden}': {line.strip()[:60]}")

    # Check for "3%" unless qualified with synthetic data
    if "3%" in content and "illustrative synthetic data" not in content.lower():
        violations.append(f"{filename} contains unqualified '3%' statistic")

    assert not violations, "Forbidden marketing or unverified claims found:\n" + "\n".join(violations)
