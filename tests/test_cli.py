from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CodexflowCliTests(unittest.TestCase):
    def run_cli(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, "-m", "codexflow.cli", *args]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            proc_init = self.run_cli(cwd, "init")
            self.assertEqual(proc_init.returncode, 0, proc_init.stderr)

            proc_list = self.run_cli(cwd, "list")
            self.assertEqual(proc_list.returncode, 0, proc_list.stderr)
            self.assertIn("planning.json", proc_list.stdout)
            self.assertIn("testing.json", proc_list.stdout)
            self.assertIn("review.json", proc_list.stdout)
            self.assertIn("general", proc_list.stdout)

    def test_yaml_scope_and_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(self.run_cli(cwd, "init").returncode, 0)

            create = self.run_cli(
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

            listed = self.run_cli(cwd, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("triage.yaml", listed.stdout)
            self.assertIn("specific:checkout-service", listed.stdout)

            dry = self.run_cli(
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
            self.assertIn("Investigate flaky checkout test", dry.stdout)

    def test_edit_and_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(self.run_cli(cwd, "init").returncode, 0)

            create = self.run_cli(
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

            edit = self.run_cli(
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

            renamed = self.run_cli(cwd, "rename", "planner", "planner-v2", "--format", "yaml")
            self.assertEqual(renamed.returncode, 0, renamed.stderr)

            show = self.run_cli(cwd, "show", "planner-v2")
            self.assertEqual(show.returncode, 0, show.stderr)
            payload = json.loads(show.stdout)
            self.assertEqual(payload["name"], "planner-v2")
            self.assertEqual(payload["format"], "yaml")
            self.assertEqual(payload["scope"], "specific")
            self.assertEqual(payload["specific_to"], "migration-project")

    def test_ai_create_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(self.run_cli(cwd, "init").returncode, 0)

            script = (
                "import json,sys;_ = sys.stdin.read();"
                "print(json.dumps({"
                "'description':'AI generated role',"
                "'role_prompt':'You handle {{task}} for {{specific_to}}.',"
                "'instructions':'Return a plan and tests for {{task}}.',"
                "'scope':'specific',"
                "'specific_to':'checkout-service',"
                "'profile':'default'"
                "}))"
            )

            add_profile = self.run_cli(
                cwd,
                "profile",
                "add",
                "mock-ai",
                "--command",
                sys.executable,
                "--arg=-c",
                "--arg",
                script,
                "--prompt-mode",
                "stdin",
            )
            self.assertEqual(add_profile.returncode, 0, add_profile.stderr)

            created = self.run_cli(
                cwd,
                "ai",
                "Create a QA role for checkout",
                "--name",
                "ai-role",
                "--runner-profile",
                "mock-ai",
                "--format",
                "yaml",
            )
            self.assertEqual(created.returncode, 0, created.stderr)

            show_created = self.run_cli(cwd, "show", "ai-role")
            self.assertEqual(show_created.returncode, 0, show_created.stderr)
            created_data = json.loads(show_created.stdout)
            self.assertEqual(created_data["format"], "yaml")
            self.assertEqual(created_data["scope"], "specific")
            self.assertEqual(created_data["specific_to"], "checkout-service")

            updated = self.run_cli(
                cwd,
                "ai",
                "Make this a general planning role",
                "--name",
                "ai-role",
                "--runner-profile",
                "mock-ai",
                "--scope",
                "general",
                "--format",
                "json",
            )
            self.assertEqual(updated.returncode, 0, updated.stderr)

            show_updated = self.run_cli(cwd, "show", "ai-role")
            self.assertEqual(show_updated.returncode, 0, show_updated.stderr)
            updated_data = json.loads(show_updated.stdout)
            self.assertEqual(updated_data["format"], "json")
            self.assertEqual(updated_data["scope"], "general")
            self.assertNotIn("specific_to", updated_data)

    def test_ai_auto_name_from_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(self.run_cli(cwd, "init").returncode, 0)

            script = (
                "import json,sys;_ = sys.stdin.read();"
                "print(json.dumps({"
                "'description':'Generated by AI',"
                "'role_prompt':'Do {{task}}',"
                "'instructions':'Steps for {{task}}',"
                "'scope':'general',"
                "'specific_to':None,"
                "'profile':'default'"
                "}))"
            )

            add_profile = self.run_cli(
                cwd,
                "profile",
                "add",
                "mock-ai",
                "--command",
                sys.executable,
                "--arg=-c",
                "--arg",
                script,
                "--prompt-mode",
                "stdin",
            )
            self.assertEqual(add_profile.returncode, 0, add_profile.stderr)

            created = self.run_cli(
                cwd,
                "ai",
                "I want to create a profile with roles for checkout reliability",
                "--runner-profile",
                "mock-ai",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertIn("Created template `create-profile-roles-checkout-reliability`", created.stdout)

            listed = self.run_cli(cwd, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("create-profile-roles-checkout-reliability.json", listed.stdout)


if __name__ == "__main__":
    unittest.main()
