# Anthrosevka Mono web fonts

These WOFF2 web subsets are derived from Anthrosevka Mono v0.4.0,
revision `3034350ccf478ee033aa400a1261f4e11b5ba5a3`, released on 2026-09-14.
The upstream project is an Iosevka custom build inspired by Anthropic Mono.
It is independent of Anthropic PBC and is not the Anthropic Mono font.

- Project: https://github.com/nanxstats/anthrosevka
- Release: https://github.com/nanxstats/anthrosevka/releases/tag/v0.4.0
- Source archive: `AnthrosevkaMono.zip`; its SHA-256 is recorded in `manifest.json`.
- License: SIL Open Font License 1.1, retained in `OFL.txt`.
- Copyright and modification notice: `NOTICE.txt`.

The local family name is **Hex Mono**. Included faces are Regular 400,
Medium 500, Semibold 600, Bold 700, and Italic 400. Chinese text falls back
to the site's Hex Han Sans family (Noto Sans SC).

Conversion on 2026-10-14 used fontTools 4.60.1 and Brotli compression.
The subsets retain common Latin, Greek, Cyrillic, punctuation, mathematical,
arrow, box-drawing, geometric, and braille characters, plus characters found
in the blog's Markdown at conversion time. OpenType layout features and
original copyright and licensing metadata are preserved. Other characters
use the platform fallbacks declared in CSS. `subset-unicodes.txt` records the
retained Unicode coverage for reproducing these subsets.

The files are self-hosted; no external font service is requested by readers.
`manifest.json` records the source revision, archive checksum, output weights,
glyph counts, and output SHA-256 checksums.
