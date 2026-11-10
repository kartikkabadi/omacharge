# Media provenance

## Banner

`assets/omacharge-banner.png` was generated with the built-in ImageGen tool.
It is a separate image made to match the user's Vantablack desktop and the
visual family of [Omafan's banner](https://github.com/kartikkabadi/omafan/blob/main/assets/omafan-banner.png).
References were that banner and an image of the real charge-control component.
The generated asset is a promotional illustration, not an application screenshot.

Final generation prompt:

> Use case: ads-marketing. Asset: final GitHub README banner for the open-source Omarchy battery plugin 'omacharge', very wide 3:1 landscape, approximately 2172 by 724 pixels. Reference image 1 is the user's existing Omafan banner: match its visual family, left-aligned oversized lowercase white sans-serif wordmark, sparse typography, luxurious black-on-black hardware render on the right, delicate silver rim lighting and sweeping restrained metallic lines, true black background. Reference image 2 is the actual battery controls: use only as palette/product context, do not reproduce or fabricate an application screenshot. Main subject on right: a beautiful realistic black anodized battery module / sculptural battery icon, recognizable battery silhouette with a subtle terminal, an understated segmented indicator filled to four of five segments in silver-white to suggest an 80% charge hold. Black materials, graphite, fine machined surfaces, soft silver edge highlights, deep shadows. Product photography / precise industrial 3D render, premium and restrained, matching the Vantablack desktop. Exact text on left, clearly readable: large lowercase 'omacharge'; directly below in smaller medium grey 'Battery care for Omarchy.'; beneath that a small widely spaced line 'LINUX / CHARGE LIMITS'. Keep the entire wordmark visible with generous margins. No colours whatsoever beyond black, white and neutral greys. No green, blue, gradients of colour, glow effects, cartoon style, extra logos, additional captions, watermarks, laptop mockups, invented UI or fan blades. A complete finished banner with typography, not a placeholder.

## Screenshots and preview

The three images in `assets/screenshots/` render the actual released QML with
sample Apple, Dell and Lenovo control states. The label **SIMULATED HARDWARE ·
REAL QML** is part of the capture frame. They contain no private user data and
are not presented as physical-device test evidence.

`assets/omacharge-demo.mp4` and `assets/omacharge-demo.gif` are a silent sequence
of those same rendered states, with short fades. They demonstrate the interface
in Vantablack, not a recording of changes to a real battery. The title and sample
hardware labels appear in each frame. Generation is reproducible using
`tools/render-previews.py` and `tools/make-preview.py`.

Physical test evidence is recorded separately in [VALIDATION.md](VALIDATION.md).
