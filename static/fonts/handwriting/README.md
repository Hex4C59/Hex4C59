# Home introduction lettering

`long-cang-intro.woff` is a local WOFF subset of Long Cang Regular, used only
for the Chinese handwritten introduction on the home page. The GitHub profile
lettering uses Caveat, which does not include the Chinese characters in this quote.

- Source: [Google Fonts / Long Cang](https://github.com/google/fonts/tree/main/ofl/longcang)
- Original file: `LongCang-Regular.ttf`
- Source Git blob: `363bb08696fe4d3827bd36d3d2fbc028d1205161`
- Original SHA-256: `e5bf2c3f24ef2327c6f136d8f73e2f9dfdf44896fdbeb35a9515f44777bb91bc`
- License: SIL Open Font License 1.1; see `long-cang-OFL.txt`.
- Subset text: `文章本天成，妙手偶得之`

The subset was generated with fontTools, preserving the font's naming and
license metadata. If the introduction text changes, regenerate the subset
from the original font to include any new characters:

```sh
pyftsubset LongCang-Regular.ttf \
  --text='文章本天成，妙手偶得之' \
  --flavor=woff \
  --output-file=long-cang-intro.woff
```
