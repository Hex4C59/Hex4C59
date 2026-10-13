# Profile artwork

These static assets are used by the personal GitHub profile README. They are kept in this repository so the profile does not depend on live badge or image-generation services.

- `hero-light.svg` and `hero-dark.svg`: greeting artwork composed with the `reading.svg` illustration by Pablo Stanley from [Open Doodles](https://www.opendoodles.com/). The illustration is dedicated to the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). The original is available at https://opendoodles.s3-us-west-1.amazonaws.com/reading.svg. The original pink book is preserved. Neutral line colors change for light and dark backgrounds; no colored background panel is added.
- `reader.svg`: the reader extracted from the existing light hero for the blog introduction. The drawing and pink book are preserved; neutral lines use `currentColor` to follow the blog theme. The same Open Doodles CC0 attribution above applies.
- Hero lettering: [Caveat](https://github.com/google/fonts/tree/main/ofl/caveat), weight 600, converted to SVG paths so it renders consistently without downloading a font. See [Caveat-OFL.txt](Caveat-OFL.txt) for the SIL Open Font License.
- Language and tool badges: locally composed labels using the individual brand colors and icon paths from [Simple Icons](https://github.com/simple-icons/simple-icons), distributed under [CC0 1.0](https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md). Product names and logos belong to their respective owners.

The hero has separate light and dark palettes selected with a README `picture` element. All artwork is static; no scripts, tracking, animation, or external fonts are embedded.
