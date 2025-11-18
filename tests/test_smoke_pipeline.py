"""
End-to-end smoke tests for the CVE analysis pipeline.

These tests run the full pipeline and verify that it produces valid output,
even if external APIs are unavailable (fallback behavior).
"""
import json
import subprocess
import sys
from typing import Any, Dict

import pytest

from tests.conftest import validate_pipeline_output


@pytest.mark.smoke
def test_cli_pipeline_runs_successfully() -> None:
    """
    Test that the CLI pipeline entrypoint runs without crashing.

    This is a smoke test: runs python main.py --package lodash and verifies:
    1. Exit code is 0
    2. stdout contains valid JSON
    3. JSON has expected structure (package, version_range, results, etc.)
    """
    result = subprocess.run(
        [sys.executable, "main.py", "--package", "lodash"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Check exit code
    assert result.returncode == 0, f"CLI failed with exit code {result.returncode}.\nStderr: {result.stderr}"

    # Check stdout is valid JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"CLI output is not valid JSON.\nOutput: {result.stdout}\nError: {e}"
        )

    # Validate structure
    assert isinstance(output, dict), "Pipeline output must be a dict"
    validate_pipeline_output(output)


@pytest.mark.smoke
def test_cli_pipeline_with_force_flag() -> None:
    """Test that --force flag works (bypasses cache)."""
    result = subprocess.run(
        [sys.executable, "main.py", "--package", "express", "--force"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"CLI with --force flag failed.\nStderr: {result.stderr}"

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"CLI output is not valid JSON with --force flag. Error: {e}")

    validate_pipeline_output(output)


@pytest.mark.smoke
def test_cli_pipeline_with_skip_threat_agent() -> None:
    """Test that --skip-threat-agent flag works."""
    result = subprocess.run(
        [sys.executable, "main.py", "--package", "react", "--skip-threat-agent"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert (
        result.returncode == 0
    ), f"CLI with --skip-threat-agent flag failed.\nStderr: {result.stderr}"

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"CLI output is not valid JSON with --skip-threat-agent. Error: {e}"
        )

    validate_pipeline_output(output)
    # When threat agent is skipped, cases should still exist (placeholder fallback)
    assert len(output["results"]) > 0, "Results should not be empty"


@pytest.mark.smoke
def test_cli_pipeline_with_version_range() -> None:
    """Test that --version-range argument works."""
    result = subprocess.run(
        [sys.executable, "main.py", "--package", "npm", "--version-range", "latest"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert (
        result.returncode == 0
    ), f"CLI with --version-range failed.\nStderr: {result.stderr}"

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"CLI output is not valid JSON with version-range. Error: {e}")

    validate_pipeline_output(output)
    assert output["version_range"] == "latest", "Output version_range should match input"


@pytest.mark.smoke
def test_pipeline_output_contains_valid_timestamps() -> None:
    """Verify that all timestamps in output are valid ISO format strings."""
    result = subprocess.run(
        [sys.executable, "main.py", "--package", "lodash"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)
    validate_pipeline_output(output)

    # Check top-level timestamp
    try:
        from datetime import datetime

        datetime.fromisoformat(output["generated_at"].replace("Z", "+00:00"))
    except ValueError as e:
        pytest.fail(f"Invalid generated_at timestamp: {output['generated_at']}. Error: {e}")

    # Check all nested timestamps
    for item in output["results"]:
        for timestamp_field in ["epss", "cvss"]:
            if timestamp_field in item:
                ts = item[timestamp_field].get("collected_at")
                try:
                    from datetime import datetime

                    datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except (ValueError, AttributeError) as e:
                    pytest.fail(
                        f"Invalid {timestamp_field}.collected_at timestamp: {ts}. Error: {e}"
                    )


@pytest.mark.smoke
def test_pipeline_output_risk_levels_are_valid() -> None:
    """Verify that all risk_level values are one of: Low, Medium, High."""
    result = subprocess.run(
        [sys.executable, "main.py", "--package", "lodash"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)
    validate_pipeline_output(output)

    valid_risk_levels = {"Low", "Medium", "High"}
    for item in output["results"]:
        risk_level = item["analysis"].get("risk_level")
        assert (
            risk_level in valid_risk_levels
        ), f"Invalid risk_level: {risk_level}. Must be one of {valid_risk_levels}"


@pytest.mark.smoke
def test_pipeline_missing_required_arg_fails() -> None:
    """Verify that missing --package argument causes CLI to fail."""
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should fail (exit code != 0)
    assert result.returncode != 0, "CLI should fail when --package is missing"


@pytest.mark.smoke
def test_pipeline_help_message_works() -> None:
    """Verify that --help flag works."""
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, "CLI --help should succeed"
    assert "package" in result.stdout.lower(), "--help should mention 'package'"
