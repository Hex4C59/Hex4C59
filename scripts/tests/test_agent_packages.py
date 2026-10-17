from pathlib import Path
import json
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_agent_examples import archive_files, check_archive, write_archives


class AgentPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        (self.source / "common").mkdir(parents=True)
        (self.source / "sample").mkdir()
        (self.source / "manifest.json").write_text(json.dumps({"sample": "/sample/"}))
        for name in ["agent_runtime.py", "README.md", "test_runtime.py"]:
            (self.source / "common" / name).write_text("shared runtime")
        (self.source / "common/requirements.txt").write_text("jsonschema==4.26.0\n")
        for name in ["app.py", "test_app.py", "README.md"]:
            (self.source / "sample" / name).write_text("sample file")
        self.destination = self.root / "output"

    def test_package_includes_shared_runtime_dependencies_and_is_reproducible(self):
        write_archives(self.destination, self.source)
        archive = self.destination / "sample.zip"
        first = archive.read_bytes()
        write_archives(self.destination, self.source)
        self.assertEqual(first, archive.read_bytes())
        with zipfile.ZipFile(archive) as packed:
            self.assertEqual(packed.read("requirements.txt"), b"jsonschema==4.26.0\n")
            self.assertEqual(packed.read("agent_runtime.py"), b"shared runtime")
        self.assertEqual(check_archive(self.source, "sample", archive), 6)

    def test_changed_source_or_extra_archive_entry_is_rejected(self):
        write_archives(self.destination, self.source)
        archive = self.destination / "sample.zip"
        (self.source / "sample/app.py").write_text("changed")
        with self.assertRaises(ValueError):
            check_archive(self.source, "sample", archive)
        write_archives(self.destination, self.source)
        with zipfile.ZipFile(archive, "a") as packed:
            packed.writestr("../escape.txt", "bad")
        with self.assertRaises(ValueError):
            check_archive(self.source, "sample", archive)

    def test_private_artifacts_symlinks_and_runtime_shadowing_are_rejected(self):
        path = self.source / "sample/.env"
        path.write_text("SYNTHETIC=not-a-secret")
        with self.assertRaises(ValueError):
            archive_files(self.source, "sample")
        path.unlink()
        path = self.source / "sample/link.py"
        path.symlink_to(self.source / "common/agent_runtime.py")
        with self.assertRaises(ValueError):
            archive_files(self.source, "sample")
        path.unlink()
        (self.source / "sample/agent_runtime.py").write_text("shadow")
        with self.assertRaises(ValueError):
            archive_files(self.source, "sample")

    def test_missing_entry_and_unpinned_dependency_are_rejected(self):
        (self.source / "sample/requirements-extra.txt").write_text("moving-dependency>=1\n")
        with self.assertRaises(ValueError):
            archive_files(self.source, "sample")
        (self.source / "sample/requirements-extra.txt").unlink()
        (self.source / "sample/app.py").unlink()
        with self.assertRaises(ValueError):
            archive_files(self.source, "sample")


if __name__ == "__main__":
    unittest.main()
