"""Portable half of the QualiSpectra guard tests (spec garde-uniforme, critère 2):
the Claude Code chain refuses added comments, protects its own files and the
git hooks, and blocks on drift from HEAD, from the pyplet root as well."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _main_checkout() -> Path:
    if env := os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(env).resolve()
    common = subprocess.run(
        (
            "git",
            "-C",
            str(ROOT),
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ),
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    return Path(common).parent if common else ROOT


MAIN = _main_checkout()
GUARD = MAIN / ".claude" / "hooks" / "guards.py"
SETTINGS = MAIN / ".claude" / "settings.json"
SCANNER = MAIN / ".claude" / "skills" / "comment-audit" / "scripts" / "scan_comments.py"
TARGET = str(MAIN / "pyplet" / "some_module.py")

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        not GUARD.is_file(),
        reason=f"no Claude Code guard at {GUARD}: nothing to assert in this clone",
    ),
]


def run(tool_name, tool_input, event="PreToolUse", extra=None):
    payload = {
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    payload.update(extra or {})
    proc = subprocess.run(
        (sys.executable, str(GUARD)),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": "", "CLAUDE_PROJECT_DIR": str(MAIN)},
    )
    return proc.returncode, proc.stdout


def decision(stdout):
    return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]


def edit(new, old=""):
    return {"file_path": TARGET, "old_string": old, "new_string": new}


@pytest.mark.parametrize(
    "new",
    [
        "x = 1  # count the widgets\n",
        "# TODO: revisit\nx = 1\n",
        "def f():\n    # explain why\n    return 1\n",
        "    # indented fragment without context\n    y = 2\n",
    ],
)
def test_added_comment_is_denied(new):
    code, out = run("Edit", edit(new))
    assert code == 0
    assert decision(out) == "deny"
    assert (
        "test that FAILS"
        in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    )


@pytest.mark.parametrize(
    "new",
    [
        "import os  # noqa: F401\n",
        "x = []  # type: list[int]\n",
        "if TYPE_CHECKING:  # pragma: no cover\n    pass\n",
        "# fmt: off\nM = [1,\n 2]\n# fmt: on\n",
        "x = 1\n",
        'def f():\n    """Return one."""\n    return 1\n',
    ],
)
def test_directives_and_plain_code_pass(new):
    code, out = run("Edit", edit(new))
    assert code == 0 and out == ""


def test_moving_an_existing_comment_passes():
    old = "a = 1\n# kept from before\nb = 2\n"
    new = "# kept from before\na = 1\nb = 2\n"
    code, out = run("Edit", edit(new, old))
    assert code == 0 and out == ""


def test_write_compares_against_file_on_disk(tmp_path):
    target = tmp_path / "mod.py"
    target.write_text("# legacy comment\nx = 1\n", encoding="utf-8")
    payload = {"file_path": str(target), "content": "# legacy comment\nx = 2\n"}
    code, out = run("Write", payload)
    assert code == 0 and out == ""
    payload["content"] = "# legacy comment\n# fresh one\nx = 2\n"
    code, out = run("Write", payload)
    assert decision(out) == "deny"


def test_multiedit_scans_every_edit():
    payload = {
        "file_path": TARGET,
        "edits": [
            {"old_string": "a", "new_string": "b"},
            {"old_string": "c", "new_string": "d  # sneaky\n"},
        ],
    }
    _, out = run("MultiEdit", payload)
    assert decision(out) == "deny"


def test_long_docstring_is_denied():
    new = (
        'def f():\n    """Summary.\n\n    Line 3.\n    Line 4.\n    """\n    return 1\n'
    )
    _, out = run("Edit", edit(new))
    assert decision(out) == "deny"
    assert (
        "3 lines" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_three_line_docstring_passes():
    new = 'def f():\n    """Summary.\n    Detail.\n    """\n    return 1\n'
    code, out = run("Edit", edit(new))
    assert code == 0 and out == ""


@pytest.mark.parametrize(
    "new",
    [
        'CSS = """\n.a {}\n.b {}\n.c {}\n.d {}\n"""\n',
        'f(textwrap.dedent("""\n    a\n    b\n    c\n    d\n"""))\n',
        'x = call(arg, """\nl1\nl2\nl3\nl4\n""")\n',
    ],
)
def test_non_docstring_triple_quoted_strings_pass(new):
    code, out = run("Edit", edit(new))
    assert code == 0 and out == ""


def test_existing_long_docstring_untouched_passes():
    doc = '    """One.\n    Two.\n    Three.\n    Four.\n    """\n'
    old = "def f():\n" + doc + "    return 1\n"
    new = "def f():\n" + doc + "    return 2\n"
    code, out = run("Edit", edit(new, old))
    assert code == 0 and out == ""


@pytest.mark.parametrize(
    "path",
    [
        str(MAIN / "README.md"),
        str(MAIN / ".bmad-loop" / "x.py"),
        str(MAIN / "tests" / "fixtures" / "bad.py"),
    ],
)
def test_non_app_paths_are_not_guarded(path):
    code, out = run(
        "Edit", {"file_path": path, "old_string": "", "new_string": "# free\n"}
    )
    assert code == 0 and out == ""


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/hooks/guards.py",
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/skills/comment-audit/scripts/scan_comments.py",
        ".githooks/pre-commit",
        ".gitlab-ci.yml",
    ],
)
def test_guard_chain_paths_are_write_protected(rel):
    for tool in ("Edit", "Write"):
        code, out = run(tool, {"file_path": str(MAIN / rel), "content": "x"})
        assert code == 0 and decision(out) == "deny", (tool, rel)


@pytest.mark.parametrize(
    "command",
    [
        "git commit --no-verify -m x",
        "git commit -n -m x",
        "git config core.hooksPath /dev/null",
        "rm .githooks/pre-commit",
        "cat .claude/settings.json",
    ],
)
def test_guard_chain_bash_bypasses_are_denied(command):
    code, out = run("Bash", {"command": command})
    assert code == 0 and decision(out) == "deny", command


def _env_without_hook_git_vars():
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo, *args):
    return subprocess.run(
        ("git", "-C", str(repo), *args),
        capture_output=True,
        text=True,
        check=True,
        env=_env_without_hook_git_vars(),
    )


def test_git_helper_never_reinitialises_the_hook_repository_as_bare(
    tmp_path, monkeypatch
):
    real = tmp_path / "real"
    _git(real.parent, "init", "-q", str(real))
    monkeypatch.setenv("GIT_DIR", str(real / ".git"))
    _git(tmp_path, "init", "-q", str(tmp_path / "throwaway"))
    assert _git(real, "config", "core.bare").stdout.strip() == "false"


def _chain_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".claude" / "hooks").mkdir(parents=True)
    (repo / ".claude" / "hooks" / "guards.py").write_text("x = 1\n")
    (repo / "ruff.toml").write_text("")
    (repo / "CLAUDE.md").write_text("")
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    return repo


def _run_in(repo, event, tool_name=None, maintenance=False):
    payload = {"hook_event_name": event, "cwd": str(repo), "tool_input": {}}
    if tool_name:
        payload["tool_name"] = tool_name
    env = {"PATH": os.environ["PATH"], "CLAUDE_PROJECT_DIR": str(repo)}
    if maintenance:
        env["QS_GUARD_MAINTENANCE"] = "1"
    proc = subprocess.run(
        (sys.executable, str(GUARD)),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    return proc.stdout


@pytest.mark.parametrize("event,tool", [("PostToolUse", "Bash"), ("Stop", None)])
def test_guard_chain_drift_from_head_blocks_however_it_was_made(tmp_path, event, tool):
    repo = _chain_repo(tmp_path)
    assert _run_in(repo, event, tool) == ""
    (repo / ".claude" / "hooks" / "guards.py").write_text("x = 2\n")
    out = json.loads(_run_in(repo, event, tool))
    assert out["decision"] == "block"
    assert ".claude/hooks/guards.py" in out["reason"]
    assert _run_in(repo, event, tool, maintenance=True) == ""


def test_guard_chain_drift_ignores_index_flags(tmp_path):
    repo = _chain_repo(tmp_path)
    _git(repo, "update-index", "--skip-worktree", ".claude/hooks/guards.py")
    (repo / ".claude" / "hooks" / "guards.py").write_text("x = 2\n")
    out = json.loads(_run_in(repo, "Stop"))
    assert out["decision"] == "block" and ".claude/hooks/guards.py" in out["reason"]
    (repo / ".claude" / "hooks" / "guards.py").unlink()
    out = json.loads(_run_in(repo, "Stop"))
    assert out["decision"] == "block" and ".claude/hooks/guards.py" in out["reason"]


def test_guard_chain_drift_sees_untracked_hook_files(tmp_path):
    repo = _chain_repo(tmp_path)
    (repo / ".githooks").mkdir()
    (repo / ".githooks" / "pre-commit").write_text("exit 0\n")
    out = json.loads(_run_in(repo, "Stop"))
    assert out["decision"] == "block" and ".githooks/pre-commit" in out["reason"]


def test_guard_chain_drift_follows_symlinks_to_the_owning_repo(tmp_path):
    chain = _chain_repo(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    (root / "CLAUDE.md").write_text("")
    (root / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    (root / ".gitlab-ci.yml").write_text("stages: [test]\n")
    (root / ".gitignore").write_text(".claude/\n.githooks\n")
    _git(root, "init", "-q")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    (root / ".claude").mkdir()
    (root / ".claude" / "hooks").symlink_to(chain / ".claude" / "hooks")
    assert _run_in(root, "Stop") == ""
    (chain / ".claude" / "hooks" / "guards.py").write_text("x = 2\n")
    out = json.loads(_run_in(root, "Stop"))
    assert out["decision"] == "block"
    assert ".claude/hooks/guards.py  (in repo)" in out["reason"]
    (chain / ".claude" / "hooks" / "guards.py").write_text("x = 1\n")
    (root / ".gitlab-ci.yml").write_text("stages: [lint]\n")
    out = json.loads(_run_in(root, "Stop"))
    assert out["decision"] == "block" and ".gitlab-ci.yml" in out["reason"]
    (root / ".gitlab-ci.yml").write_text("stages: [test]\n")
    (root / ".githooks").symlink_to(root / "nowhere")
    out = json.loads(_run_in(root, "Stop"))
    assert out["decision"] == "block" and ".githooks" in out["reason"]


def _staged_repo(tmp_path):
    repo = _chain_repo(tmp_path)
    (repo / "client").mkdir()
    (repo / "ruff.toml").write_text('line-length = 88\n[lint]\nselect = ["E", "F"]\n')
    (repo / "client" / "m.py").write_text(
        'def f():\n    """One.\n    Two.\n    """\n    return 1\n'
    )
    ruff = MAIN / ".venv" / "bin" / "ruff"
    assert ruff.is_file(), f"no ruff at {ruff}: run `make env`"
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "ruff").symlink_to(ruff)
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "m")
    return repo


def _staged(repo):
    return subprocess.run(
        (sys.executable, str(GUARD), "--staged", "--repo", str(repo)),
        capture_output=True,
        text=True,
        timeout=120,
        env={"PATH": os.environ["PATH"]},
    )


def test_staged_gate_refuses_added_comment_and_grown_docstring(tmp_path):
    repo = _staged_repo(tmp_path)
    (repo / "client" / "m.py").write_text(
        'def f():\n    """One.\n    Two.\n    Three.\n    Four.\n    """\n'
        "    return 1  # why\n"
    )
    _git(repo, "add", "-A")
    proc = _staged(repo)
    assert proc.returncode == 1
    assert "added comment: # why" in proc.stderr
    assert "grown docstring of 5 lines" in proc.stderr


def test_staged_gate_passes_a_clean_change(tmp_path):
    repo = _staged_repo(tmp_path)
    (repo / "client" / "m.py").write_text(
        'def f():\n    """One.\n    Two.\n    """\n    return 2\n'
    )
    _git(repo, "add", "-A")
    proc = _staged(repo)
    assert proc.returncode == 0, proc.stderr


def test_staged_scan_needs_no_writable_tmpdir(tmp_path):
    repo = _staged_repo(tmp_path)
    (repo / "client" / "m.py").write_text("def f():\n    return 1  # why\n")
    _git(repo, "add", "-A")
    unwritable = tmp_path / "ro-tmp"
    unwritable.mkdir(mode=0o500)
    env = {"PATH": os.environ["PATH"], "TMPDIR": str(unwritable)}
    proc = subprocess.run(
        (sys.executable, str(GUARD), "--staged", "--repo", str(repo)),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 1
    assert "did not run" not in proc.stderr
    assert "added comment: # why" in proc.stderr
    assert not any(unwritable.iterdir())
    assert "tempfile" not in SCANNER.read_text(encoding="utf-8")


def test_staged_gate_fails_closed_when_the_scan_cannot_run(
    tmp_path, monkeypatch, capsys
):
    repo = _staged_repo(tmp_path)
    (repo / "client" / "m.py").write_text(
        'def f():\n    """One.\n    Two.\n    """\n    return 2\n'
    )
    _git(repo, "add", "-A")
    spec = importlib.util.spec_from_file_location("guards_fc", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "SCAN_SCRIPT", tmp_path / "missing_scanner.py")
    assert mod.check_staged(repo) == 1
    err = capsys.readouterr().err
    assert "comment scan did not run" in err
    assert "refused this commit" in err


def test_scan_subprocess_env_is_an_allowlist():
    spec = importlib.util.spec_from_file_location("guards_env", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert set(mod.SCAN_ENV_KEYS) == {"PATH", "CLAUDE_PROJECT_DIR"}
    assert set(mod._scan_env()) <= set(mod.SCAN_ENV_KEYS)
    src = GUARD.read_text(encoding="utf-8")
    assert src.count("env=_scan_env()") == src.count("str(SCAN_SCRIPT)") == 2


def test_protected_write_resolves_aliases(tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(MAIN / ".claude")
    for path in (
        str(alias / "hooks" / "guards.py"),
        str(MAIN / ".claude//hooks/guards.py"),
    ):
        code, out = run("Write", {"file_path": path, "content": "x"})
        assert code == 0 and decision(out) == "deny", path


def test_git_precommit_hook_calls_the_staged_gate():
    hook = (MAIN / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert "guards.py --staged" in hook
    assert os.access(MAIN / ".githooks" / "pre-commit", os.X_OK)


def test_ordinary_bash_passes():
    code, out = run("Bash", {"command": "git status && make test"})
    assert code == 0 and out == ""


def test_maintenance_env_lifts_guard_chain_protection():
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit --no-verify -m x"},
    }
    proc = subprocess.run(
        (sys.executable, str(GUARD)),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=60,
        env={
            "PATH": "",
            "CLAUDE_PROJECT_DIR": str(MAIN),
            "QS_GUARD_MAINTENANCE": "1",
        },
    )
    assert proc.returncode == 0 and proc.stdout == ""


def test_stop_hook_does_not_loop():
    code, out = run("Stop", {}, event="Stop", extra={"stop_hook_active": True})
    assert code == 0 and out == ""


def test_scanner_strict_flags_whitelisted_tags(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("# TODO: later\nx = 1  # noqa\n# fmt: off\n", encoding="utf-8")
    lax = json.loads(
        subprocess.run(
            (sys.executable, str(SCANNER), "--file", str(f)),
            capture_output=True,
            text=True,
        ).stdout
    )
    strict = json.loads(
        subprocess.run(
            (sys.executable, str(SCANNER), "--file", str(f), "--strict"),
            capture_output=True,
            text=True,
        ).stdout
    )
    assert lax["flagged"] == []
    assert [x["line"] for x in strict["flagged"]] == [1]


def test_settings_wire_the_guard_on_edit_tools_and_stop():
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
    pre = {h["matcher"]: h for h in hooks["PreToolUse"]}
    writers = "Edit|Write|MultiEdit|NotebookEdit"
    assert writers in pre
    assert any("guards.py" in h["command"] for h in pre[writers]["hooks"])
    assert "Bash" in pre
    assert any("guards.py" in h["command"] for h in pre["Bash"]["hooks"])
    assert any(
        "guards.py" in h["command"] for entry in hooks["Stop"] for h in entry["hooks"]
    )


def test_guard_module_loads_scanner_from_repo():
    spec = importlib.util.spec_from_file_location("guards", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert Path(mod.SCAN_SCRIPT).resolve() == SCANNER.resolve() and SCANNER.exists()
