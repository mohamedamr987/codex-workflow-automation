from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from support import run_cli


class RepeatCliTests(unittest.TestCase):
    def test_template_default_repeat_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(run_cli(cwd, "init").returncode, 0)

            counter_script = (
                "import sys;_ = sys.stdin.read();"
                "f=open('runs.log','a',encoding='utf-8');"
                "f.write('run\\n');f.close()"
            )
            add_profile = run_cli(
                cwd,
                "profile",
                "add",
                "counter",
                "--command",
                sys.executable,
                "--arg=-c",
                "--arg",
                counter_script,
                "--prompt-mode",
                "stdin",
            )
            self.assertEqual(add_profile.returncode, 0, add_profile.stderr)

            create = run_cli(
                cwd,
                "create",
                "repeat-role",
                "--description",
                "Repeat role",
                "--role",
                "Run task",
                "--instructions",
                "Execute task",
                "--profile",
                "counter",
                "--repeat-for",
                "3s",
                "--repeat-every",
                "1s",
            )
            self.assertEqual(create.returncode, 0, create.stderr)

            run = run_cli(cwd, "run", "repeat-role", "Execute workflow")
            self.assertEqual(run.returncode, 0, run.stderr)
            runs_file = cwd / "runs.log"
            self.assertTrue(runs_file.exists())
            lines = [line for line in runs_file.read_text(encoding="utf-8").splitlines() if line]
            self.assertGreaterEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
