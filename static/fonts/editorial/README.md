# Editorial fonts

These self-hosted WOFF2 fonts support the blog's sans-serif body and headings, with a serif wordmark.
They are derived from the following SIL Open Font License 1.1 families:

| Upstream family | Local family | Included faces |
| --- | --- | --- |
| Source Sans 3 | Hex Sans | Regular 400, Medium 500, Semibold 600, Italic 400 |
| Source Serif 4 | Hex Serif | Medium 500, optical size 32 |
| Noto Sans SC | Hex Han Sans | Regular 400, Medium 500, Semibold 600 |
| Noto Serif SC | Hex Han Serif | Medium 500 |

The original font sources were downloaded from Google Fonts on 2026-10-12. Original projects:

- https://github.com/adobe-fonts/source-sans
- https://github.com/adobe-fonts/source-serif
- https://github.com/notofonts/noto-cjk
- https://github.com/google/fonts/tree/main/ofl

Each upstream license and copyright notice is included alongside the fonts.
Modified fonts use the local family names above to respect reserved font names.
The English faces retain their full upstream glyph coverage. The Chinese faces
include GB 2312 characters plus characters used in the blog's Markdown content
at conversion time. Chinese faces are split into disjoint subsets of up to
1,024 characters, ordered by frequency in the content. CSS `unicode-range` lets
the browser download only the subsets used on the current page.
`subset-unicodes.txt` records the requested code points;
unsupported characters use the platform fallbacks declared in CSS.

Conversion used fontTools 4.60.1 with Brotli compression, preserving layout tables
and copyright notices while renaming the family and subfamily records.
`manifest.json` records the final font weights, upstream revisions, and SHA-256
checksums. No external font service is required at runtime.

Medium 500 faces for Source Sans 3 and Noto Sans SC were added on 2026-10-14
so the lighter heading weight uses actual font files. Source Sans 3 uses the
upstream `3.052R` release. Noto Sans SC uses the Google Fonts revision recorded
in `manifest.json`, instantiated at weight 500 and split using the same
`unicode-range` partitions as the existing regular faces. The output keeps the
local family names, copyright notices, and OFL license. Source URLs and source
SHA-256 checksums are included in the new manifest records.

The separate `../anthrosevka/` directory provides the Hex Mono web family used
for section headings, navigation metadata, outlines, and code.
