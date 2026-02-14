from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import run_cli


class TemplateCliTests(unittest.TestCase):
    def test_init_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(run_cli(cwd, "init").returncode, 0)
            default_profile = json.loads(run_cli(cwd, "profile", "show", "default").stdout)
            self.assertEqual(default_profile["command"], "codex")
            self.assertIn("exec", default_profile["args"])
            proc_list = run_cli(cwd, "list")
            self.assertEqual(proc_list.returncode, 0, proc_list.stderr)
            self.assertIn("planning.json", proc_list.stdout)
            self.assertIn("testing.json", proc_list.stdout)
            self.assertIn("review.json", proc_list.stdout)
            self.assertIn("general", proc_list.stdout)

    def test_yaml_scope_and_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(run_cli(cwd, "init").returncode, 0)
            create = run_cli(
                cwd,
                "create",
                "triage",
                "--description",
                "Bug triage role",
                "--role",
                "You triage {{specific_to}} issues for {{owner}}.",
                "--instructions",
                "Classify severity for {{task}} and report to {{owner}}.",
                "--scope",
                "specific",
                "--specific-to",
                "checkout-service",
                "--format",
                "yaml",
            )
            self.assertEqual(create.returncode, 0, create.stderr)

            listed = run_cli(cwd, "list")
            self.assertIn("triage.yaml", listed.stdout)
            self.assertIn("specific:checkout-service", listed.stdout)

            dry = run_cli(
                cwd,
                "run",
                "triage",
                "Investigate flaky checkout test",
                "--var",
                "owner=qa-team",
                "--dry-run",
            )
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn("qa-team", dry.stdout)
            self.assertIn("checkout-service", dry.stdout)

    def test_edit_and_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(run_cli(cwd, "init").returncode, 0)
            create = run_cli(
                cwd,
                "create",
                "planner",
                "--description",
                "Planner role",
                "--role",
                "You plan work.",
                "--instructions",
                "Return a concise plan.",
            )
            self.assertEqual(create.returncode, 0, create.stderr)

            edit = run_cli(
                cwd,
                "edit",
                "planner",
                "--description",
                "Updated planner",
                "--scope",
                "specific",
                "--specific-to",
                "migration-project",
            )
            self.assertEqual(edit.returncode, 0, edit.stderr)

            renamed = run_cli(cwd, "rename", "planner", "planner-v2", "--format", "yaml")
            self.assertEqual(renamed.returncode, 0, renamed.stderr)

            show = run_cli(cwd, "show", "planner-v2")
            payload = json.loads(show.stdout)
            self.assertEqual(payload["name"], "planner-v2")
            self.assertEqual(payload["format"], "yaml")
            self.assertEqual(payload["scope"], "specific")
            self.assertEqual(payload["specific_to"], "migration-project")


if __name__ == "__main__":
    unittest.main()
