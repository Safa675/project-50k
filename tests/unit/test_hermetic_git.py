"""The hermetic temp-repo helper must ignore hostile host Git configuration."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.unit._hermetic_git import commit_all, git, init_repo, write


def _git_version() -> tuple[int, ...] | None:
    try:
        output = subprocess.run(["git", "--version"], capture_output=True, check=True).stdout.decode()
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"(\d+)\.(\d+)", output)
    return tuple(int(part) for part in match.groups()) if match else None


class HermeticGitTests(unittest.TestCase):
    def test_helper_ignores_hostile_host_config(self):
        version = _git_version()
        if version is None:
            self.skipTest("git is not available")
        if version < (2, 32):
            self.skipTest("git predates GIT_CONFIG_GLOBAL/GIT_CONFIG_SYSTEM support")
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp) / "host"
            host.mkdir()
            attributes = write(host, "attributes", b"* text eol=crlf\n")
            hooks = host / "hooks"
            write(hooks, "pre-commit", b"#!/bin/sh\nexit 1\n")
            hostile = (b"[core]\n\tautocrlf = true\n\tsafecrlf = true\n\teol = crlf\n"
                       b"\tattributesFile = " + attributes.as_posix().encode() + b"\n"
                       b"\thooksPath = " + hooks.as_posix().encode() + b"\n"
                       b"[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = synthetic-missing-gpg\n")
            global_config = write(host, "global.gitconfig", hostile)
            system_config = write(host, "system.gitconfig", hostile)
            environment = {"GIT_CONFIG_GLOBAL": str(global_config), "GIT_CONFIG_SYSTEM": str(system_config)}
            with patch.dict(os.environ, environment):
                os.environ.pop("GIT_CONFIG_NOSYSTEM", None)
                self.assertEqual(git(host, "config", "--global", "core.autocrlf").strip(), b"true")
                root = init_repo(Path(tmp) / "repo")
                fixtures = {"lf.txt": b"one\ntwo\n", "crlf.txt": b"one\r\ntwo\r\n", "dir/mixed.md": b"a\r\nb\n"}
                for relative, data in fixtures.items():
                    write(root, relative, data)
                head = commit_all(root)
                self.assertRegex(head, r"^[0-9a-f]{40,64}$")
                for relative, data in fixtures.items():
                    self.assertEqual(git(root, "show", f"HEAD:{relative}"), data, relative)
                    self.assertEqual((root / relative).read_bytes(), data, relative)
                self.assertEqual(git(root, "log", "-1", "--format=%G?").strip(), b"N")
                # Negative control: an ordinary repo under the same host config cannot commit.
                plain = Path(tmp) / "plain"
                plain.mkdir()
                subprocess.run(["git", "-C", str(plain), "init", "-q"], capture_output=True, check=True)
                write(plain, "crlf.txt", b"one\r\n")
                subprocess.run(["git", "-C", str(plain), "add", "-A"], capture_output=True, check=False)
                result = subprocess.run(["git", "-C", str(plain), "-c", "user.name=Synthetic", "-c",
                                         "user.email=synthetic@example.invalid", "commit", "-qm", "plain"],
                                        capture_output=True, check=False)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
