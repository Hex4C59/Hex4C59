from pathlib import Path
import subprocess
import json
import sys
import unittest


class EntryPointTests(unittest.TestCase):
    def test_all_mechanisms_run_from_the_extracted_project(self):
        result = subprocess.run([sys.executable, "app.py"], cwd=Path(__file__).parent,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("fixture", result.stdout)
        for name in ("planning", "context_budget", "coordination", "guardrails"):
            self.assertIn(name + ": ", result.stdout)
        outcomes = {}
        for line in result.stdout.splitlines():
            if ": " in line and line.split(": ", 1)[0] in {"planning", "context_budget", "coordination", "guardrails"}:
                name, payload = line.split(": ", 1)
                outcomes[name] = json.loads(payload)
        self.assertEqual(set(outcomes), {"planning", "context_budget", "coordination", "guardrails"})
        self.assertTrue(all(value["ok"] is True for value in outcomes.values()))

    def test_single_part_and_invalid_part_selection(self):
        command = [sys.executable, "app.py", "--part"]
        good = subprocess.run(command + ["planning"], cwd=Path(__file__).parent,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("planning: ", good.stdout)
        self.assertNotIn("coordination: ", good.stdout)
        bad = subprocess.run(command + ["unknown"], cwd=Path(__file__).parent,
                             capture_output=True, text=True, timeout=20)
        self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
