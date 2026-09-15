"""Shared look for the profile SVGs: palette, embedded fonts and card chrome."""

from __future__ import annotations

import base64
import html
import re
import urllib.parse
import urllib.request

PALETTE = {
    "bg": "#0b0f14",
    "panel": "#0d1117",
    "tile": "#11161d",
    "line": "#21262d",
    "grid": "#1c232d",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "faint": "#6e7681",
    "green": "#3fb950",
    "blue": "#58a6ff",
    "amber": "#f0b429",
    "red": "#ff7b72",
}

# Martian Mono has a fixed advance of 0.7em per glyph, which lets us place
# cursors and typing clips without measuring text at render time.
MONO_ADVANCE = 0.7
MONO = "'Martian Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', monospace"
DISPLAY = "'Unbounded', 'Segoe UI', Ubuntu, sans-serif"

FONT_FAMILIES = {
    "mono": "Martian+Mono:wght@400;700",
    "display": "Unbounded:wght@700",
}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def mono_width(text: str, size: float) -> float:
    return len(text) * size * MONO_ADVANCE


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def font_css(kind: str, text: str) -> str:
    """Return @font-face rules with a base64 subset holding only the glyphs in `text`.

    SVGs shown through <img> cannot load external fonts, so the subset goes
    inline. Without network access this returns an empty string and the SVG
    falls back to the system fonts in MONO / DISPLAY.
    """
    chars = "".join(sorted(set(text + " ")))
    query = urllib.parse.quote(chars, safe="")
    url = f"https://fonts.googleapis.com/css2?family={FONT_FAMILIES[kind]}&text={query}"
    try:
        css = _fetch(url).decode("utf-8")
        faces: dict[tuple[str, str], list[str]] = {}
        for block in re.findall(r"@font-face\s*{([^}]*)}", css):
            family = re.search(r"font-family:\s*([^;]+);", block).group(1).strip()
            weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
            src = re.search(r"url\((https://[^)]+)\)", block).group(1)
            faces.setdefault((family, src), []).append(weight)

        rules = []
        for (family, src), weights in faces.items():
            data = base64.b64encode(_fetch(src)).decode("ascii")
            weight_range = f"{min(weights, key=int)} {max(weights, key=int)}"
            rules.append(
                f"@font-face{{font-family:{family};font-weight:{weight_range};"
                f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
            )
        return "".join(rules)
    except (OSError, ValueError, AttributeError):
        return ""


def fonts_for(texts: dict[str, list[str]]) -> str:
    return "".join(font_css(kind, "".join(values)) for kind, values in texts.items() if values)


def card_defs(uid: str) -> str:
    return f"""
    <pattern id="{uid}-dots" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1.1" fill="{PALETTE['grid']}" />
    </pattern>
    <pattern id="{uid}-scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1" fill="#ffffff" opacity="0.018" />
    </pattern>"""


def card_background(uid: str, width: int, height: int, radius: int = 18) -> str:
    return f"""
  <rect width="{width}" height="{height}" rx="{radius}" fill="{PALETTE['bg']}" />
  <rect width="{width}" height="{height}" rx="{radius}" fill="url(#{uid}-dots)" />
  <rect width="{width}" height="{height}" rx="{radius}" fill="url(#{uid}-scan)" />
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="{radius}" stroke="{PALETTE['line']}" />"""


def svg_document(width: int, height: int, title: str, defs: str, style: str, body: str) -> str:
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(title)}">
  <title>{esc(title)}</title>
  <defs>{defs}
    <style>{style}</style>
  </defs>{body}
</svg>
"""


def discrete_keytimes(points: list[tuple[float, float]], total: float) -> tuple[str, str]:
    """Build `values` and `keyTimes` for a discrete SMIL animation from (time, value) pairs."""
    cleaned: list[tuple[float, float]] = []
    for time, value in sorted(points):
        time = min(max(time, 0.0), total)
        if cleaned and abs(cleaned[-1][0] - time) < 1e-6:
            cleaned[-1] = (time, value)
        else:
            cleaned.append((time, value))
    if cleaned[0][0] > 0:
        cleaned.insert(0, (0.0, cleaned[0][1]))
    values = ";".join(f"{value:g}" for _, value in cleaned)
    key_times = ";".join(f"{time / total:.4f}" for time, _ in cleaned)
    return values, key_times
