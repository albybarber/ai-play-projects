import os
import subprocess
from pathlib import Path

INSTALL = Path(__file__).resolve().parent.parent / "install.sh"
SKILL = INSTALL.parent / "skills" / "pr-tone"


def run(home, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(["bash", str(INSTALL), *args], env=env, capture_output=True, text=True)


def test_install_links_for_claude_and_copilot_and_uninstalls(tmp_path):
    dests = [tmp_path / ".claude" / "skills" / "pr-tone", tmp_path / ".copilot" / "skills" / "pr-tone"]
    for _ in range(2):  # re-running is safe
        r = run(tmp_path)
        assert r.returncode == 0, r.stderr
        for d in dests:
            assert d.is_symlink() and d.resolve() == SKILL.resolve()
    assert "\033[" not in r.stdout  # no colour codes when not a terminal
    r = run(tmp_path, "--uninstall")
    assert r.returncode == 0 and not any(d.exists() for d in dests)


def test_copy_to_custom_target(tmp_path):
    r = run(tmp_path, "--copy", "--target", str(tmp_path / "copilot"))
    dest = tmp_path / "copilot" / "pr-tone"
    assert r.returncode == 0, r.stderr
    assert not dest.is_symlink() and (dest / "SKILL.md").exists()
    assert os.access(dest / "scripts" / "prtone.py", os.X_OK)


def test_never_overwrites_someone_elses_folder(tmp_path):
    other = tmp_path / "skills" / "pr-tone"
    other.mkdir(parents=True)
    (other / "notes.txt").write_text("mine")
    for args in ([], ["--uninstall"]):
        r = run(tmp_path, "--target", str(tmp_path / "skills"), *args)
        assert (other / "notes.txt").read_text() == "mine"
    assert "isn't a pr-tone skill" in r.stdout + r.stderr
