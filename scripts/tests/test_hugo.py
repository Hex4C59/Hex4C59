"""Build isolated content fixtures to test metadata gates and asset selection."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

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
        (self.content / "articles").mkdir()
        (self.content / "articles/_index.md").write_text('+++\ntitle = "文章"\n+++\n')
        self.addCleanup(shutil.rmtree, self.content)
        self.output = self.root / "public"
        if self.output.exists():
            shutil.rmtree(self.output)

    def article(self, section="tutorials", slug="lesson", fields="", body="## Example\n\n```rust\nfn main() {}\n```\n"):
        path = self.content / section / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('+++\ntitle = "Lesson"\ndate = 2026-10-13T09:00:00+08:00\n'
                        'draft = false\nauthor = "Test"\ndescription = "An example"\n'
                        'tags = []\ncategories = ["ai"]\n' + fields + '\n+++\n' + body)
        return path

    def build(self, error=None, include_drafts=False, base_url=None):
        command = ["hugo", "--gc", "--minify", "--source", str(self.root)]
        if include_drafts:
            command.append("--buildDrafts")
        if base_url:
            command.extend(["--baseURL", base_url])
        result = subprocess.run(command,
                                capture_output=True, text=True)
        output = result.stdout + result.stderr
        if error is None:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn(error, output)
        return result

    def test_agent_code_renders_the_download_source_and_tracks_changes(self):
        examples = self.root / "examples"
        source = examples / "agents/cli-coding/app.py"
        source.parent.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, examples)
        source.write_text('print("artifact version one")\n')
        self.article(body='{{< agent-code example="cli-coding" file="app.py" >}}\n')
        self.build()
        html = (self.output / "tutorials/lesson/index.html").read_text()
        self.assertIn("artifact version one", html)
        self.assertIn('copy-code-button', html)
        url = re.search(r'data-markdown-url=([^ >]+)', html).group(1).strip('"')
        markdown = (self.output / url.lstrip('/')).read_text()
        self.assertIn('```py\nprint("artifact version one")\n', markdown)
        self.assertNotIn("agent-code-source", markdown)
        self.assertNotIn('<span class=', markdown)
        source.write_text('print("artifact version two")\n')
        self.build()
        html = (self.output / "tutorials/lesson/index.html").read_text()
        self.assertIn("artifact version two", html)
        self.assertNotIn("artifact version one", html)

    def test_agent_code_rejects_missing_or_escaping_sources(self):
        self.article(body='{{< agent-code example="cli-coding" file="app.py" >}}\n')
        self.build(error="Missing tutorial source")
        (self.content / "tutorials/lesson/index.md").unlink()
        self.article(body='{{< agent-code example="cli-coding" file="../private.py" >}}\n')
        self.build(error="Invalid agent-code")

    def series(self, extra=""):
        self.article(slug="one", fields='series = ["course"]\nseries_order = 1\nseries_number = 1')
        self.article(slug="two", fields='series = ["course"]\nseries_order = 2\nseries_number = 2\n' + extra)
        path = self.content / "series/course/_index.md"
        path.parent.mkdir(parents=True)
        path.write_text('+++\ntitle = "Course"\nseries_start = "/tutorials/one/"\n+++\n')
        return path

    def test_annotations_keep_giscus_when_api_is_not_configured(self):
        self.article(section="articles")
        with patch.dict("os.environ", {"HUGO_COMMENTS_API_URL": ""}):
            self.build()
        html = (self.output / "articles/lesson/index.html").read_text()
        self.assertIn("giscus.app/client.js", html)
        self.assertNotIn("data-annotations", html)

    def test_annotations_enable_native_ui_and_login_callback_cleanup(self):
        self.article(section="articles")
        with patch.dict("os.environ", {"HUGO_COMMENTS_API_URL": "https://comments.example/"}):
            self.build()
        html = (self.output / "articles/lesson/index.html").read_text()
        self.assertIn("data-annotations", html)
        self.assertIn("data-owner=Hex4C59", html)
        self.assertIn("annotation-login-pending", html)
        self.assertIn("comments.example", html)
        self.assertNotIn("giscus.app/client.js", html)
        self.assertRegex(html, r'src=/js/annotations\.[^ >]+\.js')

    def test_annotations_respect_article_comment_opt_out(self):
        self.article(section="articles", fields="comments = false")
        with patch.dict("os.environ", {"HUGO_COMMENTS_API_URL": "https://comments.example/"}):
            self.build()
        html = (self.output / "articles/lesson/index.html").read_text()
        self.assertNotIn("data-annotations", html)
        self.assertNotRegex(html, r'src=/js/annotations\.')

    def test_interactive_diagram_publishes_bundle_html_and_assets(self):
        article = self.article(section="articles", body='{{< interactive-diagram src="diagram.html" assets="flow.css,flow.js" title="Flow" >}}')
        (article.parent / "diagram.html").write_text('<!doctype html><html><body><p>Diagram</p><script src="flow.js"></script></body></html>')
        (article.parent / "flow.js").write_text('document.body.dataset.ready = "yes";')
        (article.parent / "flow.css").write_text('body { margin: 0; }')
        self.build()
        bundle = self.output / "articles/lesson"
        html = (bundle / "index.html").read_text()
        self.assertIn('src=/articles/lesson/diagram.html', html)
        self.assertIn('sandbox=allow-scripts', html)
        self.assertIn('Diagram', (bundle / "diagram.html").read_text())
        self.assertTrue((bundle / "flow.js").is_file())
        self.assertTrue((bundle / "flow.css").is_file())

    def test_interactive_diagram_rejects_missing_dependency(self):
        article = self.article(section="articles", body='{{< interactive-diagram src="diagram.html" assets="missing.js" >}}')
        (article.parent / "diagram.html").write_text('<p>Diagram</p>')
        self.build(error='interactive-diagram: missing asset')

    def test_old_url_keeps_article_navigation_and_one_stylesheet(self):
        self.article(fields='url = "/posts/old-lesson/"')
        self.build()
        html = (self.output / "posts/old-lesson/index.html").read_text()
        self.assertRegex(html, r'href=/articles/ aria-current=page')
        self.assertEqual(len(re.findall(r'<link rel=stylesheet', html)), 1)
        self.assertIn('class=chroma', html)
        self.assertIn('js/copy-code.js', html)
        self.assertNotIn('search-bundle', html)
        self.assertNotIn('katex.min.js', html)

    def test_article_reader_keeps_chrome_out_of_search_text(self):
        self.article(body="## 第一节\n\n### A child\n\n```rust\nfn main() {}\n```\n")
        self.build()
        html = (self.output / "tutorials/lesson/index.html").read_text()
        self.assertIn('href=#article-content', html)
        self.assertEqual(html.count('id=TableOfContents'), 1)
        self.assertIn('href=#%e7%ac%ac%e4%b8%80%e8%8a%82', html.lower())
        self.assertIn('data-reading-progress', html)
        self.assertIn('data-code-language=rust', html)
        self.assertIn('type=button aria-label=复制代码 hidden', html)
        import json
        entry = json.loads((self.output / 'index.json').read_text())[0]
        self.assertIn('fn main()', entry['content'])
        self.assertNotIn('CODE', entry['content'])
        self.assertNotIn('复制', entry['content'])

    def test_reader_preserves_toc_opt_out_and_series_navigation(self):
        self.series()
        self.article(slug="hub", fields='series = ["course"]\nseries_index = true')
        self.article(slug="no-toc", fields='showtoc = false')
        self.build()
        chapter = (self.output / "tutorials/one/index.html").read_text()
        self.assertIn('aria-label=系列章节目录', chapter)
        self.assertEqual(chapter.count('id=TableOfContents'), 1)
        hidden = (self.output / "tutorials/no-toc/index.html").read_text()
        self.assertNotIn('id=TableOfContents', hidden)
        self.assertIn('data-reading-progress', hidden)

    def test_markdown_export_preserves_code_and_resolves_bundle_links(self):
        article = self.article(section="articles", body=(
            '## 正文\n\n![plot](plot.svg)\n\n[data](data.csv)\n\n'
            '[note][asset]\n\n[asset]: plot.svg "Diagram"\n\n'
            '`[sample](plot.svg)`\n\n```markdown\n[sample](plot.svg)\n'
            '<script>sample()</script>\n```\n\n    [indented](plot.svg)\n\n$$x^2$$\n\n'
            '<figure>\n    <source srcset="plot.svg 1x, plot.svg 2x">\n    <img src="plot.svg">\n</figure>\n'))
        (article.parent / "plot.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (article.parent / "data.csv").write_text('a,b\n1,2\n')
        self.build()
        html = (self.output / "articles/lesson/index.html").read_text()
        url = re.search(r'data-markdown-url=([^ >]+)', html).group(1).strip('"')
        markdown = (self.output / url.lstrip('/')).read_text()
        self.assertTrue(markdown.startswith('# Lesson\n'))
        self.assertIn('原文：https://hex4c59.cc/articles/lesson/', markdown)
        self.assertIn('![plot](https://hex4c59.cc/articles/lesson/plot.svg)', markdown)
        self.assertIn('[asset]: https://hex4c59.cc/articles/lesson/plot.svg "Diagram"', markdown)
        self.assertIn('`[sample](plot.svg)`', markdown)
        self.assertIn('```markdown\n[sample](plot.svg)\n<script>sample()</script>\n```', markdown)
        self.assertIn('$$x^2$$', markdown)
        self.assertIn('    [indented](plot.svg)', markdown)
        self.assertIn('srcset="https://hex4c59.cc/articles/lesson/plot.svg 1x, https://hex4c59.cc/articles/lesson/plot.svg 2x"', markdown)
        self.assertNotIn('draft =', markdown)
        self.assertIn('type=text/markdown', html)

    def test_markdown_export_expands_interactive_shortcodes_without_scripts(self):
        article = self.article(section="articles", body='{{< interactive-diagram src="diagram.html" title="Flow" mobile-height="600" >}}')
        (article.parent / 'diagram.html').write_text('<!doctype html><html><body>Flow</body></html>')
        self.build()
        html = (self.output / 'articles/lesson/index.html').read_text()
        url = re.search(r'data-markdown-url=([^ >]+)', html).group(1).strip('"')
        markdown = (self.output / url.lstrip('/')).read_text()
        self.assertIn('https://hex4c59.cc/articles/lesson/diagram.html', markdown)
        self.assertIn('Flow', markdown)
        self.assertNotIn('<script', markdown)
        self.assertNotIn('<style', markdown)
        self.assertNotIn('{{<', markdown)

    def test_markdown_export_respects_a_site_path_prefix(self):
        config = self.root / 'hugo.toml'
        original = config.read_text()
        self.addCleanup(config.write_text, original)
        config.write_text(original.replace('baseURL = "https://hex4c59.cc/"', 'baseURL = "https://example.org/blog/"'))
        self.article(slug='next')
        article = self.article(section='articles', body='![plot](plot.svg)\n\n[next](/tutorials/next/)\n\n[home](/blog)\n')
        (article.parent / 'plot.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.build()
        html = (self.output / 'articles/lesson/index.html').read_text()
        url = re.search(r'data-markdown-url=([^ >]+)', html).group(1).strip('"')
        self.assertTrue(url.startswith('/blog/markdown/'))
        markdown = (self.output / url[len('/blog/'):]).read_text()
        self.assertIn('![plot](https://example.org/blog/articles/lesson/plot.svg)', markdown)
        self.assertIn('[next](https://example.org/blog/tutorials/next/)', markdown)
        self.assertIn('[home](https://example.org/blog)', markdown)

    def test_reader_script_and_export_are_limited_to_articles(self):
        self.article()
        self.article(slug='draft', fields='', body='Never export this draft.')
        path = self.content / 'tutorials/draft/index.md'
        path.write_text(path.read_text().replace('draft = false', 'draft = true'))
        self.build()
        article = (self.output / 'tutorials/lesson/index.html').read_text()
        home = (self.output / 'index.html').read_text()
        self.assertIn('/js/reader.min.', article)
        self.assertNotIn('/js/reader.min.', home)
        self.assertNotIn('type=text/markdown', home)
        self.assertFalse(any('Never export this draft.' in p.read_text() for p in (self.output / 'markdown').glob('*.md')))

    def test_related_reading_prioritizes_curated_links_and_deduplicates_courses(self):
        current = self.article(slug='current')
        current.write_text(current.read_text().replace('tags = []', 'tags = ["Rust"]'))
        self.series()
        self.article(slug='hub', fields='series = ["course"]\nseries_index = true')
        for slug in ('one', 'two'):
            path = self.content / ('tutorials/' + slug + '/index.md')
            path.write_text(path.read_text().replace('tags = []', 'tags = ["Rust"]'))
        self.article(slug='chosen')
        self.article(slug='draft')
        path = self.content / 'tutorials/draft/index.md'
        path.write_text(path.read_text().replace('draft = false', 'draft = true'))
        current.write_text(current.read_text().replace('tags = ["Rust"]', 'tags = ["Rust"]\nrelated_reading = [{ref = "/tutorials/chosen/", reason = "补充前置知识"}]'))
        self.build()
        html = (self.output / 'tutorials/current/index.html').read_text()
        related = re.search(r'<section class=related-reading.*?</section>', html, re.S).group()
        self.assertIn('补充前置知识', related)
        self.assertIn('同话题 · Rust', related)
        self.assertEqual(related.count('href=/tutorials/hub/'), 1)
        self.assertNotIn('href=/tutorials/one/', related)
        self.assertNotIn('href=/tutorials/two/', related)
        self.assertNotIn('href=/tutorials/current/', related)
        self.assertNotIn('href=/tutorials/draft/', related)
        self.assertLess(related.index('href=/tutorials/chosen/'), related.index('href=/tutorials/hub/'))
        chapter = (self.output / 'tutorials/one/index.html').read_text()
        self.assertNotIn('class=related-reading', chapter)

    def test_related_reading_rejects_missing_curated_page(self):
        self.article(fields='related_reading = [{ref = "/articles/missing/", reason = "Read next"}]')
        self.build('related_reading: missing page')

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

    def test_three_tags_are_allowed(self):
        path = self.article()
        path.write_text(path.read_text().replace('tags = []', 'tags = ["Rust", "所有权", "借用"]'))
        self.build()

    def test_more_than_three_tags_are_rejected(self):
        path = self.article()
        path.write_text(path.read_text().replace('tags = []', 'tags = ["Rust", "所有权", "借用", "移动"]'))
        result = self.build("tags must contain at most 3 entries")
        self.assertIn("tutorials/lesson/index.md", result.stdout + result.stderr)

    def test_draft_tags_are_checked_when_included(self):
        path = self.article()
        path.write_text(path.read_text().replace('tags = []', 'tags = ["a", "b", "c", "d"]')
                        .replace('draft = false', 'draft = true'))
        self.build()
        self.build("tags must contain at most 3 entries", include_drafts=True)

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

    def test_new_subject_needs_only_configuration_and_content(self):
        config = self.root / "data/categories.toml"
        original = config.read_text()
        self.addCleanup(config.write_text, original)
        config.write_text(original + '\n[travel]\nlabel = "旅行"\ndescription = "旅途中的观察"\norder = 4\n')
        path = self.article(section="articles", slug="journey", body="一次旅行的记录。")
        path.write_text(path.read_text().replace('categories = ["ai"]', 'categories = ["travel"]'))
        self.build()
        html = (self.output / "articles/journey/index.html").read_text()
        self.assertIn('href=/categories/travel/', html)
        self.assertIn('旅行', html)
        self.assertIn('<title>旅行 |', (self.output / 'categories/travel/index.html').read_text())
        import json
        self.assertEqual(json.loads((self.output / 'index.json').read_text())[0]['category_labels'], ['旅行'])
        self.assertNotIn('js/copy-code.js', html)
        self.assertNotIn('katex.min.js', html)
        for url in ('/', '/articles/', '/series/', '/about/'):
            self.assertIn('href=' + url, html)
        collection = (self.output / "articles/index.html").read_text()
        self.assertIn('value=travel', collection)
        self.assertIn('href=/articles/journey/', collection)

    def test_supplements_share_hub_without_chapter_navigation(self):
        self.series()
        self.article(slug="hub", fields='series = ["course"]\nseries_index = true\nlayout = "series"\nseries_kind = "course"', body="课程目录的内容。")
        self.article(slug="practice", fields='series = ["course"]\nseries_role = "exercise"')
        self.article(slug="reference", fields='series = ["course"]\nseries_role = "appendix"')
        self.build()
        hub = (self.output / "tutorials/hub/index.html").read_text()
        self.assertIn('课程目录的内容', hub)
        self.assertIn('2 章 · 2 篇配套资料', hub)
        self.assertIn('href=/tutorials/practice/', hub)
        self.assertIn('href=/tutorials/reference/', hub)
        last = (self.output / "tutorials/two/index.html").read_text()
        nav = re.search(r'<nav class=series-pagination.*?</nav>', last, re.S).group()
        self.assertNotIn('/tutorials/reference/', nav)
        self.assertIn('已读到本系列末篇', nav)
        reference = (self.output / "tutorials/reference/index.html").read_text()
        nav = re.search(r'<nav class=series-pagination.*?</nav>', reference, re.S).group()
        self.assertIn('系列资料导航', nav)
        self.assertNotIn('下一篇', nav)
        listing = (self.output / "tutorials/index.html").read_text()
        self.assertEqual(len(re.findall('class="?post-line ', listing)), 1)

    def test_global_library_can_expand_members_and_filter_support_tags(self):
        self.series()
        self.article(slug="hub", fields='series = ["course"]\nseries_index = true')
        p = self.article(slug="reference", fields='series = ["course"]\nseries_role = "appendix"')
        p.write_text(p.read_text().replace('tags = []', 'tags = ["排错"]'))
        self.build()
        html = (self.output / "articles/index.html").read_text()
        self.assertIn('data-expand-series', html)
        self.assertRegex(html, r'data-mode=member hidden')
        self.assertIn('value=排错', html)
        self.assertIn('href=/tutorials/reference/', html)
        tag = (self.output / "tags/排错/index.html").read_text()
        self.assertIn('data-expand-series checked', tag)
        self.assertRegex(tag, r'data-mode=hub hidden')

    def test_ordered_members_may_use_different_source_folders(self):
        self.series()
        self.article(section="articles", slug="hub", fields='series = ["course"]\nseries_index = true')
        self.build()
        html = (self.output / "articles/hub/index.html").read_text()
        self.assertIn('href=/tutorials/one/', html)

    def test_open_collection_does_not_require_orders(self):
        for slug in ("first", "second"):
            self.article(section="articles", slug=slug, fields='series = ["notes"]')
        self.build()
        html = (self.output / "series/notes/index.html").read_text()
        self.assertIn('文章合集', html)
        self.assertIn('/articles/first/', html)
        self.assertIn('/articles/second/', html)

    def topic(self, fields='include_categories = ["ai"]', start='/articles/first/'):
        path = self.content / 'topics/ai/_index.md'
        path.parent.mkdir(parents=True)
        (self.content / 'topics/_index.md').write_text('+++\ntitle = "专题"\ndescription = "阅读路线"\n+++\n')
        path.write_text('+++\ntitle = "Agent 专题"\ndescription = "从概念到实践"\n'
                        'topic_key = "ai"\nweight = 10\ntopic_start = "' + start + '"\n' + fields + '\n'
                        '[[reading_routes]]\ntitle = "从这里读起"\npages = ["' + start + '"]\n+++\n')
        return path

    def test_topic_preserves_old_urls_and_excludes_drafts_and_search_chrome(self):
        import json
        self.article(section='articles', slug='first', fields='url = "/old-first/"')
        draft = self.article(section='articles', slug='unfinished')
        draft.write_text(draft.read_text().replace('draft = false', 'draft = true'))
        self.topic()
        self.build(base_url='https://example.org/blog/')
        topic = (self.output / 'topics/ai/index.html').read_text()
        article = (self.output / 'old-first/index.html').read_text()
        self.assertIn('1 篇正文', topic)
        self.assertIn('href=/blog/old-first/', topic)
        self.assertNotIn('unfinished', topic)
        self.assertIn('aria-label=所属专题', article)
        self.assertIn('href=/blog/topics/ai/', article)
        self.assertIn('aria-label=返回专题阅读路线', article)
        entries = json.loads((self.output / 'index.json').read_text())
        self.assertEqual(len(entries), 1)
        self.assertNotIn('推荐阅读路线', entries[0]['content'])
        home = (self.output / 'index.html').read_text()
        self.assertLess(home.index('id=home-topics-title'), home.index('id=recent-title'))

    def test_home_groups_open_series_without_hiding_standalone_articles(self):
        self.article(section='articles', slug='first', fields='series = ["notes"]\nlastmod = 2026-10-14')
        self.article(section='articles', slug='second', fields='series = ["notes"]\nlastmod = 2026-10-15')
        self.article(section='articles', slug='standalone')
        self.topic('include_series = ["notes"]\ninclude_categories = ["ai"]')
        self.build()
        home = (self.output / 'index.html').read_text()
        self.assertEqual(home.count('data-update-series=notes'), 1)
        updates = re.search(r'<section class="?list-container home-recent.*?</section>', home, re.S).group()
        self.assertIn('href=/articles/second/', updates)
        self.assertNotIn('href=/articles/first/', updates)
        self.assertIn('href=/articles/standalone/', updates)
        topic = (self.output / 'topics/ai/index.html').read_text()
        self.assertIn('3 篇正文', topic)
        series = (self.output / 'series/notes/index.html').read_text()
        self.assertIn('href=/topics/ai/', series)

    def test_topic_rejects_unpublished_or_missing_reading_start(self):
        self.article(section='articles', slug='first')
        draft = self.article(section='articles', slug='unfinished')
        draft.write_text(draft.read_text().replace('draft = false', 'draft = true'))
        path = self.topic(start='/articles/missing/')
        for start in ('/articles/missing/', '/articles/unfinished/'):
            with self.subTest(start=start):
                path.write_text(path.read_text().replace('/articles/missing/', start))
                self.build('must resolve to a published article content path')

    def test_topic_rejects_unknown_series(self):
        self.article(section='articles', slug='first')
        self.topic('include_series = ["missing"]')
        self.build('unknown series')

    def test_reader_membership_can_follow_an_open_collection(self):
        self.series()
        p = self.content / "tutorials/one/index.md"
        p.write_text(p.read_text().replace('series = ["course"]', 'series = ["notes", "course"]'))
        self.article(slug="hub", fields='series = ["course"]\nseries_index = true')
        self.build()
        html = (self.output / "tutorials/one/index.html").read_text()
        self.assertIn('data-series-sidebar=/tutorials/hub/', html)

    def test_tag_aliases_remain_searchable(self):
        import json
        p = self.article(section="articles")
        p.write_text(p.read_text().replace('tags = []', 'tags = ["记忆"]'))
        term = self.content / 'tags/记忆/_index.md'
        term.parent.mkdir(parents=True)
        term.write_text('+++\ntitle = "记忆"\naliases = ["/tags/memory/"]\n+++\n')
        self.build()
        entry = json.loads((self.output / 'index.json').read_text())[0]
        self.assertEqual(entry['tags'], ['记忆'])
        self.assertIn('memory', entry['tag_aliases'])
        self.assertEqual(entry['source_label'], '原创')
        self.assertTrue((self.output / 'tags/memory/index.html').exists())

    def test_mixed_optional_formats_have_flat_filter_values(self):
        self.article(section="articles", slug="plain")
        self.article(section="articles", slug="concept", fields='article_type = "concept"')
        self.article(section="articles", slug="tutorial", fields='article_type = "tutorial"')
        self.build()
        html = (self.output / "articles/index.html").read_text()
        self.assertIn('<option value=concept>概念与设计</option>', html)
        self.assertIn('<option value=tutorial>实战教程</option>', html)
        self.assertNotIn('value="[', html)
        self.assertNotIn('value=[', html)

    def test_translation_attribution_is_independent_of_folder(self):
        self.article(section="articles", fields='source_kind = "translation"')
        self.build('translations require original_title')

    def test_valid_translation_in_shared_folder(self):
        self.article(section="articles", fields='source_kind = "translation"\noriginal_title = "Original"\noriginal_url = "https://example.com/original"\noriginal_author = "Author"\noriginal_site = "Example"')
        self.build()
        self.assertIn('译文', (self.output / "articles/lesson/index.html").read_text())

    def test_feed_groups_series_and_excludes_utility_pages(self):
        import xml.etree.ElementTree as ET
        self.series()
        self.article(slug="hub", fields='series = ["course"]\nseries_index = true')
        self.article(slug="reference", fields='series = ["course"]\nseries_role = "appendix"')
        (self.content / "about.md").write_text('+++\ntitle = "About"\nlayout = "about"\n+++\n')
        self.build()
        feed = ET.parse(self.output / "index.xml")
        items = feed.findall('channel/item')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].findtext('link'), 'https://hex4c59.cc/tutorials/hub/')

    def test_unknown_category_is_rejected(self):
        p = self.article()
        p.write_text(p.read_text().replace('categories = ["ai"]', 'categories = ["typo"]'))
        self.build('unknown category')

    def test_unknown_source_is_rejected(self):
        self.article(fields='source_kind = "typo"')
        self.build('unknown source_kind')

    def test_unknown_series_role_is_rejected(self):
        self.article(fields='series = ["course"]\nseries_role = "typo"')
        self.build('unknown series_role')

    def test_supplement_cannot_have_chapter_order(self):
        self.article(fields='series = ["course"]\nseries_role = "appendix"\nseries_order = 9')
        self.build('supplementary material must not have')

    def test_supplement_cannot_be_reading_start(self):
        term = self.series()
        self.article(slug="hub", fields='series = ["course"]\nseries_index = true')
        self.article(slug="reference", fields='series = ["course"]\nseries_role = "appendix"')
        term.write_text(term.read_text().replace('/tutorials/one/', '/tutorials/reference/'))
        self.build('in the reading sequence')

    def test_empty_ordered_series_is_rejected(self):
        self.article(fields='series = ["empty"]\nseries_index = true')
        self.build('requires at least one reading page')

    def test_unknown_series_kind_is_rejected(self):
        self.article(fields='series_kind = "typo"')
        self.build('unknown series_kind')

    def test_article_can_belong_to_only_one_ordered_reader(self):
        self.article(slug="one", fields='series = ["first", "second"]\nseries_order = 1')
        for key in ('first', 'second'):
            self.article(slug=key, fields='series = ["' + key + '"]\nseries_index = true')
        self.build('only one ordered series')


if __name__ == "__main__":
    unittest.main()
