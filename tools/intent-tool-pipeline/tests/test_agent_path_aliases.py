"""Real Windows junction coverage without symbolic-link creation privilege."""
import os
from pathlib import Path
import subprocess

import pytest

from pipeline_control.io_utils import InputError, atomic_write_json, read_structured
from pipeline_control.submissions import assert_plain_path
from test_agent_finalize import _selected, _submission, _call
from test_procedure_binding import bind


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows junction coverage")


def junction(link, target):
    # Paths come only from the isolated pytest directory, never operator input.
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path "
        + quote(link) + " -Target " + quote(target) + " | Out-Null",
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("revision", ["1.1", "1.2"])
def test_junction_submission_rejected_without_canonical_mutation(tmp_path_factory, revision):
    project = tmp_path_factory.mktemp("alias")
    run = _selected(project)
    state_path = run / "30_execution/run_state.json"
    if revision == "1.2":
        state = read_structured(state_path)
        state["control"]["semantic_role_boundary"] = revision
        atomic_write_json(state_path, state)
    request = _submission(project, run)
    if revision == "1.2":
        request = bind(project, run, request)
    source = request["source_path"]
    target = project / "protected"
    target.mkdir()
    protected = target / source.name
    protected.write_bytes(source.read_bytes())
    saved = protected.read_bytes()
    before_state = state_path.read_bytes()
    assert source.parent.is_relative_to(project)
    source.unlink()
    source.parent.rmdir()  # Empty, fixture-owned exact directory only.
    junction(source.parent, target)
    try:
        with pytest.raises(InputError, match="symlink|reparse"):
            assert_plain_path(project, source, require_file=True)
        rejected = _call(project, run, request)
        assert not rejected.ok, rejected.as_dict()
        assert state_path.read_bytes() == before_state
        assert not (run / "10_framing/problem_frame.md").exists()
        assert protected.read_bytes() == saved
    finally:
        os.rmdir(source.parent)  # Unlink the junction, never recurse into target.
    assert protected.read_bytes() == saved


def test_junction_input_escape_rejected(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    evidence = outside / "input.md"
    evidence.write_text("protected original", encoding="utf-8")
    alias = project / "alias"
    junction(alias, outside)
    try:
        with pytest.raises(InputError, match="symlink|reparse"):
            assert_plain_path(project, alias / "input.md", require_file=True)
    finally:
        os.rmdir(alias)
    assert evidence.read_text(encoding="utf-8") == "protected original"
