"""Build isolated content fixtures to test metadata gates and asset selection."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HugoContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for name in ("layouts", "assets", "data", "themes/typo"):
            shutil.copytree(ROOT / name, cls.root / name)
        config = (ROOT / "hugo.toml").read_text().replace("enableGitInfo = true", "enableGitInfo = false")
        (cls.root / "hugo.toml").write_text(config)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.content = self.root / "content"
        self.content.mkdir()
        self.addCleanup(shutil.rmtree, self.content)
        self.output = self.root / "public"
        if self.output.exists():
            shutil.rmtree(self.output)

    def article(self, section="tutorials", slug="lesson", fields="", body="## Example\n\n```rust\nfn main() {}\n```\n"):
        path = self.content / section / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('+++\ntitle = "Lesson"\ndate = 2026-10-13T09:00:00+08:00\n'
                        'draft = false\nauthor = "Test"\ndescription = "An example"\n'
                        'tags = []\ncategories = []\n' + fields + '\n+++\n' + body)
        return path

    def build(self, error=None):
        result = subprocess.run(["hugo", "--gc", "--minify", "--source", str(self.root)],
                                capture_output=True, text=True)
        output = result.stdout + result.stderr
        if error is None:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn(error, output)
        return result

    def series(self, extra=""):
        self.article(slug="one", fields='series = ["course"]\nseries_order = 1\nseries_number = 1')
        self.article(slug="two", fields='series = ["course"]\nseries_order = 2\nseries_number = 2\n' + extra)
        path = self.content / "series/course/_index.md"
        path.parent.mkdir(parents=True)
        path.write_text('+++\ntitle = "Course"\nseries_start = "/tutorials/one/"\n+++\n')
        return path

    def test_old_url_keeps_tutorial_navigation_and_one_stylesheet(self):
        self.article(fields='url = "/posts/old-lesson/"')
        self.build()
        html = (self.output / "posts/old-lesson/index.html").read_text()
        self.assertRegex(html, r'href=/tutorials/ aria-current=page')
        self.assertEqual(len(re.findall(r'<link rel=stylesheet', html)), 1)
        self.assertIn('class=chroma', html)
        self.assertIn('js/copy-code.js', html)
        self.assertNotIn('search-bundle', html)
        self.assertNotIn('katex.min.js', html)

    def test_five_article_types_have_labels_and_shortcuts(self):
        for kind in ("concept", "tutorial", "practice", "review", "eval"):
            self.article(section="agent", slug=kind,
                         fields='article_type = "%s"\ndifficulty = "beginner"' % kind)
        self.build()
        html = (self.output / "agent/index.html").read_text()
        for kind, label in (("practice", "工程实战"), ("review", "方案与项目复盘"), ("eval", "评测与实验")):
            self.assertIn('data-value=' + kind, html)
            self.assertIn(label, html)

    def test_math_is_opt_in_and_search_has_its_bundle(self):
        self.article(fields="math = true", body="$$x^2$$")
        (self.content / "search.md").write_text('+++\ntitle = "Search"\nlayout = "search"\n+++\n')
        self.build()
        article = (self.output / "tutorials/lesson/index.html").read_text()
        search = (self.output / "search/index.html").read_text()
        self.assertIn('katex.min.js', article)
        self.assertNotIn('copy-code.js', article)
        self.assertIn('search-bundle', search)
        self.assertNotIn('katex.min.js', search)

    def test_math_on_first_chapter_is_loaded_on_hub(self):
        self.series()
        path = self.content / "tutorials/one/index.md"
        path.write_text(path.read_text().replace('series_order = 1', 'math = true\nseries_order = 1'))
        self.article(slug="hub", fields='series = ["course"]\nseries_index = true\nlayout = "series"')
        self.build()
        self.assertIn('katex.min.js', (self.output / "tutorials/hub/index.html").read_text())

    def test_invalid_article_type(self):
        self.article(section="agent", fields='article_type = "typo"\ndifficulty = "beginner"')
        self.build("unknown article_type")

    def test_unknown_section(self):
        self.article(section="unclassified")
        self.build("unknown article section")

    def test_missing_description(self):
        path = self.article()
        path.write_text(path.read_text().replace('description = "An example"\n', ''))
        self.build("description is required")

    def test_invalid_math_flag(self):
        self.article(fields='math = "true"')
        self.build("math must be true or false")

    def test_missing_date(self):
        path = self.article()
        path.write_text(path.read_text().replace('date = 2026-10-13T09:00:00+08:00\n', ''))
        self.build("publication date is required")

    def test_zero_chapter_number(self):
        self.series()
        path = self.content / "tutorials/two/index.md"
        path.write_text(path.read_text().replace('series_number = 2', 'series_number = 0'))
        self.build("series_number must be a positive integer")

    def test_duplicate_series_order(self):
        self.series()
        path = self.content / "tutorials/two/index.md"
        path.write_text(path.read_text().replace('series_order = 2', 'series_order = 1'))
        self.build("duplicate series_order")

    def test_duplicate_chapter_number(self):
        self.series()
        path = self.content / "tutorials/two/index.md"
        path.write_text(path.read_text().replace('series_number = 2', 'series_number = 1'))
        self.build("duplicate series_number")

    def test_series_start_must_be_a_member_content_path(self):
        term = self.series()
        self.article(slug="unrelated")
        term.write_text(term.read_text().replace('/tutorials/one/', '/tutorials/unrelated/'))
        self.build("must resolve to a published member's content path")

    def test_duplicate_series_hub(self):
        self.series()
        for slug in ("hub-one", "hub-two"):
            self.article(slug=slug, fields='series = ["course"]\nseries_index = true')
        self.build("only one series_index hub")

    def test_draft_with_unfinished_metadata_can_be_saved(self):
        path = self.article()
        path.write_text(path.read_text().replace('draft = false', 'draft = true').replace('description = "An example"', 'description = ""'))
        self.build()
        self.assertFalse((self.output / "tutorials/lesson/index.html").exists())


if __name__ == "__main__":
    unittest.main()
