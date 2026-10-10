"""Temporary Git repositories unaffected by the host's Git configuration.

Not collected by unittest discovery. Repo-local settings override global/system
autocrlf, signing, hooks and attributes, so committed bytes equal written bytes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCAL_CONFIG = (
    ("core.autocrlf", "false"), ("core.safecrlf", "false"), ("core.eol", "lf"),
    ("core.fsmonitor", "false"), ("commit.gpgsign", "false"), ("tag.gpgsign", "false"),
    ("user.name", "Synthetic Test"), ("user.email", "synthetic@example.invalid"),
)


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.decode('utf-8', 'replace')[-400:]}")
    return result.stdout


def init_repo(root: Path) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    for key, value in LOCAL_CONFIG:
        git(root, "config", "--local", key, value)
    hooks = root / ".git" / "synthetic-no-hooks"
    hooks.mkdir(exist_ok=True)
    git(root, "config", "--local", "core.hooksPath", str(hooks))
    git(root, "config", "--local", "core.attributesFile", str(root / ".git" / "synthetic-no-attributes"))
    git(root, "config", "--local", "core.excludesFile", str(root / ".git" / "synthetic-no-excludes"))
    return root


def write(root: Path, relative: Path | str, data: bytes) -> Path:
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def copy_registered(root: Path, relative: Path | str, source_repo: Path = REPO) -> Path:
    """Copy a tracked source with CRLF normalised to LF (a CRLF host checkout stays usable)."""
    return write(root, relative, (Path(source_repo) / relative).read_bytes().replace(b"\r\n", b"\n"))


def commit_all(root: Path, message: str = "Synthetic registration") -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-verify", "-m", message)
    return git(root, "rev-parse", "HEAD").decode().strip()
