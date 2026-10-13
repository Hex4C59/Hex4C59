import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_site import check_site
from package_course import check_archive, write_archive


class SiteLinksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put("index.html", '<link rel="canonical" href="https://example.org/blog/">'
                 '<a href="/blog/article/#answer">read</a><script src="/blog/app.js"></script>')
        self.put("article/index.html", '<h2 id="answer">Answer</h2><a href="#answer">same page</a>'
                 '<a href="https://external.org/missing/">external</a>')
        self.put("app.js", "")
        self.put("index.json", json.dumps([{"permalink": "/blog/article/"}]))

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_subpath_and_relative_fragments(self):
        self.assertEqual(check_site(self.root)["search_entries"], 1)

    def test_missing_fragment(self):
        self.put("article/index.html", '<h2 id="wrong">Wrong</h2>')
        with self.assertRaisesRegex(ValueError, "missing fragment"):
            check_site(self.root)

    def test_missing_asset(self):
        (self.root / "app.js").unlink()
        with self.assertRaisesRegex(ValueError, "missing local target"):
            check_site(self.root)

    def test_url_outside_base_path(self):
        self.put("article/index.html", '<a href="/article/">missing blog prefix</a>')
        with self.assertRaisesRegex(ValueError, "leaves site base path"):
            check_site(self.root)

    def test_missing_css_font(self):
        self.put("style.css", '@font-face{src:url("./font.woff2")}')
        with self.assertRaisesRegex(ValueError, "font.woff2"):
            check_site(self.root)

    def test_duplicate_search_entries(self):
        self.put("index.json", json.dumps([{"permalink": "/blog/article/"}] * 2))
        with self.assertRaisesRegex(ValueError, "Duplicate search entry"):
            check_site(self.root)


class CourseArchiveTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "course"
        (self.source / "src").mkdir(parents=True)
        (self.source / "src/main.rs").write_text('fn main() { println!("你好"); }\n')
        (self.source / ".gitignore").write_text("/target/\n")
        (self.source / "target").mkdir()
        (self.source / "target/generated").write_text("generated")
        self.archive = self.root / "course.zip"
        write_archive(self.source, self.archive)

    def test_repeated_pack_is_byte_identical(self):
        first = self.archive.read_bytes()
        (self.source / "src/main.rs").touch()
        write_archive(self.source, self.archive)
        self.assertEqual(first, self.archive.read_bytes())
        self.assertEqual(check_archive(self.source, self.archive), 2)

    def test_changed_source_is_rejected(self):
        (self.source / "src/main.rs").write_text("fn main() {}")
        with self.assertRaisesRegex(ValueError, "contents differ"):
            check_archive(self.source, self.archive)

    def test_extra_archive_entry_is_rejected(self):
        with zipfile.ZipFile(self.archive, "a") as packed:
            packed.writestr("rust-course/secret", "not source")
        with self.assertRaisesRegex(ValueError, "extra"):
            check_archive(self.source, self.archive)

    def test_missing_archive_entry_is_rejected(self):
        (self.source / "README.md").write_text("new lesson")
        with self.assertRaisesRegex(ValueError, "missing"):
            check_archive(self.source, self.archive)

    def test_symlinks_are_rejected(self):
        (self.source / "outside").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            write_archive(self.source, self.archive)


if __name__ == "__main__":
    unittest.main()
