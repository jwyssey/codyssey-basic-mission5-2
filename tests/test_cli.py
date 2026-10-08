"""REPL에서 사용자 입력·오류 복구·출력 계약을 검증한다."""

import ast
import io
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from minigit import Repository
from minigit.cli import MiniGitCLI, run_repl


class CLITests(unittest.TestCase):
    def setUp(self):
        clock = lambda: datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
        self.cli = MiniGitCLI(Repository(clock=clock))

    def test_case_insensitive_commands_and_quoted_arguments(self):
        self.assertIn("Current user: Alice Smith", self.cli.execute('iNiT "Alice Smith"'))
        self.assertIn("c00000001", self.cli.execute('CoMmIt "Add login feature"'))
        self.assertIn("Found 1 commit:", self.cli.execute('SeArCh "LOGIN FEATURE"'))
        self.assertIn("Found 1 commit:", self.cli.execute('SEARCH --author="Alice Smith"'))

    def test_invalid_args_and_unknown_commands(self):
        self.cli.execute("INIT Alice")
        for line in (
            "INIT", 'INIT ""', "COMMIT unquoted message", 'COMMIT "   "',
            'COMMIT "unclosed', "LOG extra", "LOG --sort-by=unknown", "LOG --sort-by=",
            "PATH a", "PATH a b c", 'PATH "" b', "ANCESTORS",
            "SEARCH --author=", "SEARCH --unknown=Alice", "SEARCH one two",
            "BRANCH one two", "SWITCH", "USER", "MERGE", "HELP extra", "EXIT extra",
        ):
            with self.subTest(line=line):
                self.assertEqual(self.cli.execute(line), "Invalid args")
        self.assertEqual(self.cli.execute("nonsense"), "Unknown command: nonsense")
        self.assertTrue(self.cli.running)
        self.assertEqual(self.cli.repository.commits, {})

    def test_standard_unknown_branch_and_commit_errors(self):
        self.cli.execute("INIT Alice")
        self.assertEqual(self.cli.execute("SWITCH nowhere"), "Unknown branch: nowhere")
        self.assertEqual(self.cli.execute("ANCESTORS nowhere"), "Unknown commit: nowhere")

    def test_log_includes_identifiable_fields_and_head(self):
        self.cli.execute("INIT Alice")
        self.cli.execute('COMMIT "Initial commit"')
        output = self.cli.execute("LOG")
        for value in ("c00000001", "Alice", "2026-10-08T12:00:00", "Initial commit", "HEAD -> main"):
            self.assertIn(value, output)

    def test_no_path_and_same_commit_output(self):
        self.cli.execute("INIT Alice")
        self.cli.execute("BRANCH orphan")
        self.cli.execute('COMMIT "First root"')
        self.cli.execute("SWITCH orphan")
        self.cli.execute('COMMIT "Second root"')
        self.assertEqual(self.cli.execute("PATH c00000001 c00000002"), "No path")
        self.assertEqual(self.cli.execute("PATH c00000001 c00000001"), "Path: c00000001")

    def test_empty_results_and_blank_input(self):
        self.assertEqual(self.cli.execute("   "), "")
        self.assertEqual(self.cli.execute("LOG"), "Repository not initialized")
        self.cli.execute("INIT Alice")
        self.assertEqual(self.cli.execute("LOG"), "No commits")
        self.assertEqual(self.cli.execute("SEARCH absent"), "No matches")
        self.cli.execute("COMMIT root")
        self.assertEqual(self.cli.execute("ANCESTORS c00000001"), "No ancestors")

    def test_help_and_both_exit_commands(self):
        self.assertIn("PATH", self.cli.execute("HELP"))
        for command in ("exit", "QUIT"):
            cli = MiniGitCLI()
            self.assertEqual(cli.execute(command), "Bye.")
            self.assertFalse(cli.running)

    def test_repl_recovers_from_errors_and_exits(self):
        source = io.StringIO('INIT Alice\nCOMMIT "bad\nCOMMIT good\nLOG\nquit\nCOMMIT ignored\n')
        target = io.StringIO()
        run_repl(source, target)
        output = target.getvalue()
        self.assertEqual(output.count("mini-git> "), 5)
        self.assertIn("Invalid args", output)
        self.assertIn("commit c00000001", output)
        self.assertNotIn("ignored", output)
        self.assertTrue(output.endswith("Bye.\n"))

    def test_eof_and_ctrl_c_exit_cleanly(self):
        target = io.StringIO()
        run_repl(io.StringIO(), target)
        self.assertIn("Bye.", target.getvalue())
        source = io.StringIO()
        target = io.StringIO()
        with patch.object(source, "readline", side_effect=KeyboardInterrupt):
            run_repl(source, target)
        self.assertIn("Bye.", target.getvalue())

    def test_no_standard_sort_api_used_in_implementation(self):
        root = Path(__file__).resolve().parents[1]
        for path in (root / "minigit").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    forbidden = (
                        isinstance(node.func, ast.Name) and node.func.id == "sorted"
                    ) or (
                        isinstance(node.func, ast.Attribute) and node.func.attr == "sort"
                    )
                    self.assertFalse(forbidden, f"Forbidden sorting API: {path}:{node.lineno}")
