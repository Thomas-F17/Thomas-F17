"""Embeds the Computer Modern (CMU) fonts in generated SVGs, subset to the characters used.

GitHub shows README images without access to web fonts, so the font has to travel inside
each SVG. Fonts live in ./fonts (SIL Open Font License, see fonts/OFL.txt).
Needs:  pip install fonttools brotli   (without them the SVGs fall back to system fonts)
"""
import base64, html, io, logging, os, re
logging.getLogger("fontTools").setLevel(logging.ERROR)

FONT_DIR = os.environ.get("FONT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts"))
SERIF = "'CMU Serif','Latin Modern Roman','Computer Modern',Georgia,serif"
MONO = "'CMU Typewriter','Latin Modern Mono','Courier New',monospace"
FACES = [("CMU Serif", "normal", "cmunrm.woff"), ("CMU Serif", "bold", "cmunbx.woff"),
         ("CMU Typewriter", "normal", "cmuntt.woff"), ("CMU Typewriter", "bold", "cmuntb.woff")]
FILES = {("serif", False): "cmunrm.woff", ("serif", True): "cmunbx.woff",
         ("mono", False): "cmuntt.woff", ("mono", True): "cmuntb.woff"}

def _visible_text(svg):
    svg = re.sub(r"<style.*?</style>", "", svg, flags=re.S)
    return html.unescape("".join(re.findall(r">([^<]+)<", svg)))

def _font_rule(family, weight, path, text):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    try:
        import brotli  # noqa: F401  (needed for woff2)
        flavor, mime = "woff2", "font/woff2"
    except ImportError:
        flavor, mime = "woff", "font/woff"
    opts = subset.Options(); opts.flavor = flavor; opts.layout_features = ["*"]
    font = TTFont(path); s = subset.Subsetter(opts); s.populate(text=text + " "); s.subset(font)
    buf = io.BytesIO(); font.flavor = flavor; font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:{mime};base64,{data}) format('{flavor}');}}"

def embed(svg):
    """Returns the SVG with the CMU faces it uses embedded. Unchanged if fontTools isn't installed."""
    try:
        import fontTools  # noqa: F401
    except ImportError:
        return svg
    text = _visible_text(svg)
    bold = re.search(r"font-weight:\s*(bold|[6-9]00)", svg) is not None
    rules = []
    for family, weight, fname in FACES:
        path = os.path.join(FONT_DIR, fname)
        if family not in svg or (weight == "bold" and not bold) or not os.path.exists(path):
            continue
        rules.append(_font_rule(family, weight, path, text))
    if not rules:
        return svg
    i = svg.index(">", svg.index("<svg")) + 1
    return svg[:i] + f"<defs><style>{''.join(rules)}</style></defs>" + svg[i:]

def advance(kind, bold, text, size):
    """Width of `text` in pixels at `size`, using the real font metrics (for layout)."""
    from fontTools.ttLib import TTFont
    f = TTFont(os.path.join(FONT_DIR, FILES[(kind, bold)]))
    cmap, hm, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hm[cmap.get(ord(c), cmap[32])][0] for c in text) * size / upm
