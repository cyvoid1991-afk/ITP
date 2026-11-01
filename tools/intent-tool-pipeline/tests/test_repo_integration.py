"""Exercise repository entry points from unrelated working directories."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from test_build_tool_pipeline_skill import INITIALIZER, _request

TOOL = Path(__file__).resolve().parents[1]
REPO = TOOL.parents[1]
CONTRACT = "docs/contracts/examples/filename_normalizer/product_contract.yaml"


@pytest.mark.parametrize("location", ["repo", "tool", "unrelated"])
def test_cli_default_root_is_independent_of_cwd(tmp_path, location):
    cwd = {"repo": REPO, "tool": TOOL, "unrelated": tmp_path}[location]
    result = subprocess.run(
        [sys.executable, str(TOOL / "pipeline_ops.py"), "--format", "json",
         "validate-contract", "--contract", CONTRACT],
        cwd=cwd, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert Path(payload["data"]["contract_path"]) == TOOL / CONTRACT


def test_cli_explicit_root_overrides_installed_tool(tmp_path):
    shutil.copyfile(TOOL / CONTRACT, tmp_path / "contract.yaml")
    result = subprocess.run(
        [sys.executable, str(TOOL / "pipeline_ops.py"), "--project-root", str(tmp_path),
         "--format", "json", "validate-contract", "--contract", "contract.yaml"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert Path(json.loads(result.stdout)["data"]["contract_path"]) == tmp_path / "contract.yaml"


def test_relocated_initializer_creates_run_only_inside_tool(tmp_path):
    repo = tmp_path / "repo"
    tool = repo / "tools/intent-tool-pipeline"
    script = repo / ".agents/skills/build-tool-pipeline/scripts/initialize_run.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(INITIALIZER, script)
    shutil.copytree(TOOL / "pipeline_control", tool / "pipeline_control",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (tool / "request.yaml").write_text(yaml.safe_dump(_request()), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), "--request", "request.yaml", "--run-id", "smoke",
         "--timestamp", "2026-10-01T00:00:00+09:00", "--format", "json"],
        cwd=repo, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    run_dir = json.loads(result.stdout)["data"]["run_dir"]
    assert (tool / run_dir / "30_execution/run_state.json").is_file()
    assert not (repo / "workspace").exists()
