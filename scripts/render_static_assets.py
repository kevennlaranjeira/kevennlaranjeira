#!/usr/bin/env python3
"""Render the hand-made profile SVGs (header, terminal, stack, footer, game pieces).

These assets only change when the text below changes, so they are built
locally and committed. Run: python scripts/render_static_assets.py
"""

from __future__ import annotations

import math
import re
import urllib.request
from pathlib import Path

from svg_kit import (
    DISPLAY,
    MONO,
    MONO_ADVANCE,
    PALETTE,
    USER_AGENT,
    card_background,
    card_defs,
    discrete_keytimes,
    esc,
    fonts_for,
    mono_width,
    svg_document,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICON_CACHE = Path(__file__).resolve().parent / "icons"

CONTENT = {
    "pt": {
        "location": "USP · São Carlos, SP",
        "roles": [
            "mestrando em ciência da computação · USP",
            "pesquisador",
            "desenvolvedor de software",
            "bacharel em sistemas de informação · UFV",
        ],
        "session": [
            ("whoami", [("Kevenn Laranjeira de Oliveira", "text")]),
            (
                "cat sobre.txt",
                [
                    ("mestrando e pesquisador em ciência da computação · USP São Carlos", "text"),
                    ("bacharel em sistemas de informação · UFV", "text"),
                ],
            ),
            (
                "ls interesses/",
                [("algoritmos/  backend/  bancos-de-dados/  processamento-de-imagens/  automação/", "dir")],
            ),
            ("echo $EMAIL", [("kevennlaranjeira@gmail.com", "accent")]),
        ],
        "stack": [
            ("linguagens", [("py", "Python"), ("java", "Java"), ("c", "C"), ("cpp", "C++"), ("ts", "TypeScript"), ("js", "JavaScript"), ("dart", "Dart")]),
            ("web, dados e infra", [("html", "HTML"), ("css", "CSS"), ("nodejs", "Node.js"), ("postgres", "PostgreSQL"), ("docker", "Docker")]),
            ("ferramentas", [("git", "Git"), ("github", "GitHub"), ("githubactions", "Actions"), ("latex", "LaTeX"), ("make", "Makefile")]),
        ],
    },
    "en": {
        "location": "USP · São Carlos, Brazil",
        "roles": [
            "master's student in computer science · USP",
            "researcher",
            "software developer",
            "b.sc. in information systems · UFV",
        ],
        "session": [
            ("whoami", [("Kevenn Laranjeira de Oliveira", "text")]),
            (
                "cat about.txt",
                [
                    ("master's student and researcher in computer science · USP São Carlos", "text"),
                    ("b.sc. in information systems · UFV", "text"),
                ],
            ),
            (
                "ls interests/",
                [("algorithms/  backend/  databases/  image-processing/  automation/", "dir")],
            ),
            ("echo $EMAIL", [("kevennlaranjeira@gmail.com", "accent")]),
        ],
        "stack": [
            ("languages", [("py", "Python"), ("java", "Java"), ("c", "C"), ("cpp", "C++"), ("ts", "TypeScript"), ("js", "JavaScript"), ("dart", "Dart")]),
            ("web, data & infra", [("html", "HTML"), ("css", "CSS"), ("nodejs", "Node.js"), ("postgres", "PostgreSQL"), ("docker", "Docker")]),
            ("tools", [("git", "Git"), ("github", "GitHub"), ("githubactions", "Actions"), ("latex", "LaTeX"), ("make", "Makefile")]),
        ],
    },
}

NAME_FIRST = "Kevenn Laranjeira"
NAME_LAST = "de Oliveira"
HANDLE = "github.com/kevennlaranjeira"


def suffix(locale: str) -> str:
    return "" if locale == "pt" else "-en"


def wave_path(width: int, period: int, amplitude: float, center: float, phase: float = 0.0) -> str:
    points = []
    for x in range(0, width + period + 8, 8):
        angle = 2 * math.pi * x / period
        y = center + amplitude * (math.sin(angle + phase) + 0.35 * math.sin(2 * angle + 1.3 + phase))
        points.append(f"{x},{y:.1f}")
    return "M" + " L".join(points)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def render_header(locale: str) -> str:
    data = CONTENT[locale]
    width, height = 1000, 280
    role_size = 17
    char = role_size * MONO_ADVANCE
    role_x = 48 + 2 * char
    slot = 4.2
    total = slot * len(data["roles"])

    # Each role gets a slot: typed letter by letter, held, then erased at once
    role_elements = []
    cursor_points: list[tuple[float, float]] = [(0.0, role_x), (total, role_x)]
    for index, role in enumerate(data["roles"]):
        start = index * slot
        end = start + slot - 0.35
        width_points = [(0.0, 0.0), (start, 0.0), (end, 0.0), (total, 0.0)]
        cursor_points += [(start, role_x), (end, role_x)]
        for k in range(1, len(role) + 1):
            moment = start + 0.25 + k * 0.045
            width_points.append((moment, k * char + 2))
            cursor_points.append((moment, role_x + k * char + 3))

        values, key_times = discrete_keytimes(width_points, total)
        role_elements.append(
            f"""
    <clipPath id="h-role-{index}"><rect x="{role_x}" y="210" width="{mono_width(role, role_size) + 2:.1f}" height="36">
      <animate attributeName="width" dur="{total}s" repeatCount="indefinite" calcMode="discrete" values="{values}" keyTimes="{key_times}" />
    </rect></clipPath>"""
        )
    cursor_values, cursor_times = discrete_keytimes(cursor_points, total)

    role_texts = "".join(
        f'\n  <text x="{role_x}" y="236" class="role" clip-path="url(#h-role-{i})">{esc(role)}</text>'
        for i, role in enumerate(data["roles"])
    )

    waves = f"""
  <g mask="url(#h-fade)">
    <path d="{wave_path(width, 260, 30, 146)}" stroke="url(#h-wave)" stroke-width="10" opacity="0.28" filter="url(#h-glow)">
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-260 0" dur="7s" repeatCount="indefinite" />
    </path>
    <path d="{wave_path(width, 260, 30, 146)}" stroke="url(#h-wave)" stroke-width="2.2" opacity="0.55">
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-260 0" dur="7s" repeatCount="indefinite" />
    </path>
    <path d="{wave_path(width, 180, 14, 150, 2.1)}" stroke="{PALETTE['blue']}" stroke-width="1.4" opacity="0.35">
      <animateTransform attributeName="transform" type="translate" from="-180 0" to="0 0" dur="4.6s" repeatCount="indefinite" />
    </path>
    <path d="{wave_path(width, 120, 4, 266, 0.7)}" stroke="{PALETTE['amber']}" stroke-width="1.2" opacity="0.35">
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-120 0" dur="3.2s" repeatCount="indefinite" />
    </path>
  </g>"""

    defs = card_defs("h") + f"""
    <linearGradient id="h-name" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{PALETTE['green']}" />
      <stop offset="0.55" stop-color="#7ee2a8" />
      <stop offset="1" stop-color="{PALETTE['blue']}" />
    </linearGradient>
    <linearGradient id="h-wave" x1="0" y1="0" x2="{width}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{PALETTE['green']}" />
      <stop offset="1" stop-color="{PALETTE['blue']}" />
    </linearGradient>
    <linearGradient id="h-fade-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#000" />
      <stop offset="0.18" stop-color="#fff" />
      <stop offset="0.82" stop-color="#fff" />
      <stop offset="1" stop-color="#000" />
    </linearGradient>
    <mask id="h-fade" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}">
      <rect width="{width}" height="{height}" fill="url(#h-fade-grad)" />
    </mask>
    <radialGradient id="h-blob-green">
      <stop offset="0" stop-color="{PALETTE['green']}" stop-opacity="0.2" />
      <stop offset="1" stop-color="{PALETTE['green']}" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="h-blob-blue">
      <stop offset="0" stop-color="{PALETTE['blue']}" stop-opacity="0.18" />
      <stop offset="1" stop-color="{PALETTE['blue']}" stop-opacity="0" />
    </radialGradient>
    <filter id="h-glow" x="-5%" y="-60%" width="110%" height="220%">
      <feGaussianBlur stdDeviation="7" />
    </filter>
    <clipPath id="h-card"><rect width="{width}" height="{height}" rx="18" /></clipPath>
    <clipPath id="h-reveal-1"><rect x="0" y="40" width="{width}" height="90">
      <animate attributeName="width" values="0;0;{width}" keyTimes="0;0.2;1" dur="1.3s" calcMode="spline" keySplines="0 0 1 1;0.2 0.8 0.2 1" />
    </rect></clipPath>
    <clipPath id="h-reveal-2"><rect x="0" y="130" width="{width}" height="70">
      <animate attributeName="width" values="0;0;{width}" keyTimes="0;0.45;1" dur="1.7s" calcMode="spline" keySplines="0 0 1 1;0.2 0.8 0.2 1" />
    </rect></clipPath>{''.join(role_elements)}"""

    all_mono = [data["location"], HANDLE, ">", *data["roles"]]
    style = fonts_for({"mono": all_mono, "display": [NAME_FIRST, NAME_LAST]}) + f"""
      .label {{ font: 400 13px {MONO}; fill: {PALETTE['muted']}; }}
      .name {{ font: 700 56px {DISPLAY}; letter-spacing: -0.5px; }}
      .role {{ font: 400 {role_size}px {MONO}; fill: {PALETTE['text']}; }}
      .prompt {{ font: 700 {role_size}px {MONO}; fill: {PALETTE['amber']}; }}"""

    body = card_background("h", width, height) + f"""
  <g clip-path="url(#h-card)">
    <circle cx="860" cy="30" r="320" fill="url(#h-blob-green)">
      <animateTransform attributeName="transform" type="translate" values="0 0;-60 30;0 0" dur="16s" repeatCount="indefinite" />
    </circle>
    <circle cx="120" cy="290" r="300" fill="url(#h-blob-blue)">
      <animateTransform attributeName="transform" type="translate" values="0 0;70 -20;0 0" dur="19s" repeatCount="indefinite" />
    </circle>{waves}
  </g>
  <circle cx="53" cy="40" r="4" fill="{PALETTE['amber']}">
    <animate attributeName="opacity" values="1;0.25;1" dur="2.4s" repeatCount="indefinite" />
  </circle>
  <text x="66" y="45" class="label">{esc(data['location'])}</text>
  <text x="952" y="45" class="label" text-anchor="end">{esc(HANDLE)}</text>
  <text x="46" y="118" class="name" fill="url(#h-name)" clip-path="url(#h-reveal-1)">{esc(NAME_FIRST)}</text>
  <text x="46" y="182" class="name" fill="none" stroke="{PALETTE['text']}" stroke-width="1.3" stroke-opacity="0.85" clip-path="url(#h-reveal-2)">{esc(NAME_LAST)}</text>
  <text x="48" y="236" class="prompt">&gt;</text>{role_texts}
  <rect x="{role_x}" y="221" width="{char * 0.62:.1f}" height="19" fill="{PALETTE['amber']}">
    <animate attributeName="x" dur="{total}s" repeatCount="indefinite" calcMode="discrete" values="{cursor_values}" keyTimes="{cursor_times}" />
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite" />
  </rect>"""

    title = f"{NAME_FIRST} {NAME_LAST}: " + ", ".join(data["roles"])
    return svg_document(width, height, title, defs, style, body)


# ---------------------------------------------------------------------------
# Terminal
# ---------------------------------------------------------------------------


def render_terminal(locale: str) -> str:
    data = CONTENT[locale]
    size = 15
    char = size * MONO_ADVANCE
    line_height = 29
    x0, y0 = 36, 88
    user, host_sep, path, dollar = "kevenn@usp", ":", "~", "$ "
    prompt_len = len(user + host_sep + path + dollar)

    rows = sum(1 + len(outputs) for _, outputs in data["session"]) + 1
    width, height = 1000, y0 + rows * line_height + 8
    total = 24.0
    hide_at = total - 0.5

    elements: list[str] = []
    clips: list[str] = []

    def appear(moment: float) -> str:
        values, key_times = discrete_keytimes([(0.0, 0), (moment, 1), (hide_at, 0), (total, 0)], total)
        return f'<animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" calcMode="discrete" values="{values}" keyTimes="{key_times}" />'

    def prompt(y: float, moment: float) -> str:
        return (
            f'\n  <text x="{x0}" y="{y}" class="line" xml:space="preserve">'
            f'<tspan class="user">{user}</tspan><tspan>{host_sep}</tspan><tspan class="path">{path}</tspan><tspan>{esc(dollar)}</tspan>'
            f"{appear(moment)}</text>"
        )

    moment = 0.6
    row = 0
    for index, (command, outputs) in enumerate(data["session"]):
        y = y0 + row * line_height
        elements.append(prompt(y, moment))
        moment += 0.45

        command_x = x0 + prompt_len * char
        points = [(0.0, 0.0), (moment, 0.0)]
        for k in range(1, len(command) + 1):
            points.append((moment + k * 0.075, k * char + 2))
        points += [(hide_at, 0.0), (total, 0.0)]
        values, key_times = discrete_keytimes(points, total)
        clips.append(
            f"""
    <clipPath id="t-cmd-{index}"><rect x="{command_x:.1f}" y="{y - 20}" width="{mono_width(command, size) + 2:.1f}" height="28">
      <animate attributeName="width" dur="{total}s" repeatCount="indefinite" calcMode="discrete" values="{values}" keyTimes="{key_times}" />
    </rect></clipPath>"""
        )
        elements.append(f'\n  <text x="{command_x:.1f}" y="{y}" class="line cmd" xml:space="preserve" clip-path="url(#t-cmd-{index})">{esc(command)}</text>')
        moment += len(command) * 0.075 + 0.35
        row += 1

        for text, kind in outputs:
            y = y0 + row * line_height
            elements.append(f'\n  <text x="{x0}" y="{y}" class="line {kind}" xml:space="preserve">{esc(text)}{appear(moment)}</text>')
            moment += 0.12
            row += 1
        moment += 0.55

    y = y0 + row * line_height
    elements.append(prompt(y, moment))
    cursor_x = x0 + prompt_len * char
    elements.append(
        f"""
  <rect x="{cursor_x:.1f}" y="{y - 15}" width="{char * 0.8:.1f}" height="19" fill="{PALETTE['amber']}">
    {appear(moment)}
  </rect>
  <rect x="{cursor_x:.1f}" y="{y - 15}" width="{char * 0.8:.1f}" height="19" fill="{PALETTE['bg']}">
    <animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.5;0.5;1" dur="1.05s" repeatCount="indefinite" />
  </rect>"""
    )

    title_bar = f"{user}: ~"
    texts = [user, host_sep, path, dollar, title_bar]
    for command, outputs in data["session"]:
        texts.append(command)
        texts.extend(text for text, _ in outputs)

    defs = card_defs("t") + f"""
    <clipPath id="t-card"><rect width="{width}" height="{height}" rx="18" /></clipPath>{''.join(clips)}"""
    style = fonts_for({"mono": texts}) + f"""
      .line {{ font: 400 {size}px {MONO}; fill: {PALETTE['text']}; white-space: pre; }}
      .bar {{ font: 400 12px {MONO}; fill: {PALETTE['faint']}; }}
      .user {{ fill: {PALETTE['green']}; font-weight: 700; }}
      .path {{ fill: {PALETTE['blue']}; font-weight: 700; }}
      .cmd {{ fill: {PALETTE['text']}; font-weight: 700; }}
      .text {{ fill: #c9d1d9; }}
      .dir {{ fill: {PALETTE['blue']}; }}
      .accent {{ fill: {PALETTE['amber']}; }}"""

    body = card_background("t", width, height) + f"""
  <g clip-path="url(#t-card)">
    <rect width="{width}" height="44" fill="#131920" />
    <rect y="44" width="{width}" height="1" fill="{PALETTE['line']}" />
  </g>
  <circle cx="26" cy="22" r="6" fill="#ff5f56" />
  <circle cx="46" cy="22" r="6" fill="#ffbd2e" />
  <circle cx="66" cy="22" r="6" fill="#27c93f" />
  <text x="{width / 2}" y="26" class="bar" text-anchor="middle">{esc(title_bar)}</text>{''.join(elements)}"""

    title = " / ".join(text for _, outputs in data["session"] for text, _ in outputs)
    return svg_document(width, height, title, defs, style, body)


# ---------------------------------------------------------------------------
# Technology stack
# ---------------------------------------------------------------------------


def load_icon(name: str) -> str:
    ICON_CACHE.mkdir(exist_ok=True)
    cached = ICON_CACHE / f"{name}.svg"
    if not cached.exists():
        if name == "make":
            cached.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" fill="none" viewBox="0 0 256 256">'
                '<rect width="256" height="256" rx="60" fill="#242938"/>'
                '<path d="M62 92h132M62 128h92M62 164h116" stroke="#7cc05a" stroke-width="16" stroke-linecap="round"/>'
                '<circle cx="190" cy="128" r="12" fill="#7cc05a"/></svg>',
                encoding="utf-8",
            )
        else:
            request = urllib.request.Request(f"https://skillicons.dev/icons?i={name}", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            inner = re.search(r"<g transform=\"translate\(0, 0\)\">\s*(<svg.*</svg>)\s*</g>", raw, re.DOTALL)
            cached.write_text(inner.group(1) if inner else raw, encoding="utf-8")
    return cached.read_text(encoding="utf-8")


def place_icon(name: str, x: float, y: float, size: int) -> str:
    svg = load_icon(name)
    prefix = f"i-{name}-"
    ids = set(re.findall(r'id="([^"]+)"', svg))
    for icon_id in ids:
        svg = svg.replace(f'id="{icon_id}"', f'id="{prefix}{icon_id}"')
        svg = svg.replace(f"url(#{icon_id})", f"url(#{prefix}{icon_id})")
        svg = svg.replace(f'href="#{icon_id}"', f'href="#{prefix}{icon_id}"')
    opening = re.match(r"<svg[^>]*>", svg).group(0)
    cleaned = re.sub(r'\s(width|height|x|y)="[^"]*"', "", opening)
    new_opening = cleaned.replace("<svg", f'<svg x="{x}" y="{y}" width="{size}" height="{size}"', 1)
    return svg.replace(opening, new_opening, 1)


def pop_in(delay: float, duration: float = 0.6) -> str:
    """Fade and slide a group in. SMIL keeps the tile visible where animations don't run."""
    total = delay + duration
    start = delay / total
    return (
        f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{start:.3f};1" dur="{total:.2f}s" />'
        f'<animateTransform attributeName="transform" type="translate" values="0 14;0 14;0 0" keyTimes="0;{start:.3f};1" '
        f'dur="{total:.2f}s" calcMode="spline" keySplines="0 0 1 1;0.2 0.8 0.2 1" />'
    )


def render_stack(locale: str) -> str:
    groups = CONTENT[locale]["stack"]
    width = 1000
    x0, pitch, icon = 40, 128, 56
    row_height = 148
    height = 46 + (len(groups) - 1) * row_height + 124

    body_parts: list[str] = []
    texts: list[str] = []
    tile_index = 0
    for row, (label, items) in enumerate(groups):
        label_y = 46 + row * row_height
        heading = f"// {label}"
        texts.append(heading)
        line_start = x0 + mono_width(heading, 12) + 16
        body_parts.append(
            f"""
  <text x="{x0}" y="{label_y}" class="group"><tspan class="slash">//</tspan> {esc(label)}</text>
  <rect x="{line_start:.0f}" y="{label_y - 5}" width="{width - 40 - line_start:.0f}" height="1" fill="url(#s-rule)" />"""
        )
        for column, (icon_name, name) in enumerate(items):
            x = x0 + column * pitch
            y = label_y + 20
            texts.append(name)
            body_parts.append(
                f"""
  <g>
    {pop_in(0.15 + tile_index * 0.055)}
    {place_icon(icon_name, x, y, icon)}
    <text x="{x + icon / 2}" y="{y + icon + 22}" class="tile-label" text-anchor="middle">{esc(name)}</text>
  </g>"""
            )
            tile_index += 1

    defs = card_defs("s") + f"""
    <linearGradient id="s-rule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{PALETTE['line']}" />
      <stop offset="1" stop-color="{PALETTE['line']}" stop-opacity="0" />
    </linearGradient>"""
    style = fonts_for({"mono": texts}) + f"""
      .group {{ font: 400 12px {MONO}; fill: {PALETTE['muted']}; text-transform: lowercase; }}
      .slash {{ fill: {PALETTE['amber']}; font-weight: 700; }}
      .tile-label {{ font: 400 11px {MONO}; fill: #c9d1d9; }}
"""

    body = card_background("s", width, height) + "".join(body_parts)
    names = [name for _, items in groups for _, name in items]
    return svg_document(width, height, ", ".join(names), defs, style, body)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------


def render_footer() -> str:
    width, height = 1000, 110
    text = "// EOF"
    size = 13
    text_width = mono_width(text, size)
    defs = f"""
    <linearGradient id="f-fade-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#000" />
      <stop offset="0.25" stop-color="#fff" />
      <stop offset="0.75" stop-color="#fff" />
      <stop offset="1" stop-color="#000" />
    </linearGradient>
    <mask id="f-fade" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}">
      <rect width="{width}" height="{height}" fill="url(#f-fade-grad)" />
    </mask>"""
    style = fonts_for({"mono": [text]}) + f"""
      .eof {{ font: 400 {size}px {MONO}; fill: {PALETTE['faint']}; }}"""
    body = f"""
  <g mask="url(#f-fade)">
    <path d="{wave_path(width, 240, 9, 40)}" stroke="{PALETTE['green']}" stroke-width="1.5" opacity="0.55">
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-240 0" dur="6s" repeatCount="indefinite" />
    </path>
    <path d="{wave_path(width, 170, 6, 46, 1.8)}" stroke="{PALETTE['blue']}" stroke-width="1.2" opacity="0.45">
      <animateTransform attributeName="transform" type="translate" from="-170 0" to="0 0" dur="4.8s" repeatCount="indefinite" />
    </path>
  </g>
  <text x="{(width - text_width) / 2:.1f}" y="92" class="eof">{text}</text>
  <rect x="{(width + text_width) / 2 + 4:.1f}" y="81" width="8" height="14" fill="{PALETTE['amber']}">
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.05s" repeatCount="indefinite" />
  </rect>"""
    return svg_document(width, height, "EOF", defs, style, body)


# ---------------------------------------------------------------------------
# Tic-tac-toe pieces
# ---------------------------------------------------------------------------


def tile_frame(win: bool) -> str:
    fill = "#0f2417" if win else PALETTE["tile"]
    stroke = PALETTE["green"] if win else PALETTE["line"]
    stroke_width = 2 if win else 1.2
    return f'<rect x="3" y="3" width="90" height="90" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" />'


def render_piece(kind: str, win: bool = False) -> str:
    if kind == "x":
        color = PALETTE["amber"]
        length = 50.9
        mark = f"""
  <path d="M30 30 L66 66" stroke="{color}" stroke-width="9" stroke-linecap="round" stroke-dasharray="{length}">
    <animate attributeName="stroke-dashoffset" values="{length};0" dur="0.3s" />
  </path>
  <path d="M66 30 L30 66" stroke="{color}" stroke-width="9" stroke-linecap="round" stroke-dasharray="{length}">
    <animate attributeName="stroke-dashoffset" values="{length};{length};0" keyTimes="0;0.5;1" dur="0.6s" />
  </path>"""
        title = "X"
    else:
        color = PALETTE["blue"]
        length = 119.4
        mark = f"""
  <circle cx="48" cy="48" r="19" stroke="{color}" stroke-width="9" stroke-dasharray="{length}" transform="rotate(-90 48 48)">
    <animate attributeName="stroke-dashoffset" values="{length};0" dur="0.5s" />
  </circle>"""
        title = "O"
    glow = ""
    if win:
        glow = f"""
  <rect x="3" y="3" width="90" height="90" rx="16" stroke="{PALETTE['green']}" stroke-width="2">
    <animate attributeName="stroke-opacity" values="1;0.3;1" dur="1.6s" repeatCount="indefinite" />
  </rect>"""
    return f"""<svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">
  {tile_frame(win)}{glow}{mark}
</svg>
"""


def render_empty(cell: int) -> str:
    style = fonts_for({"mono": [str(cell)]})
    return f"""<svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{cell}">
  <defs><style>{style} .n {{ font: 400 12px {MONO}; fill: {PALETTE['faint']}; }}</style></defs>
  {tile_frame(False)}
  <text x="14" y="25" class="n">{cell}</text>
  <path d="M48 38 V58 M38 48 H58" stroke="{PALETTE['muted']}" stroke-width="3" stroke-linecap="round">
    <animate attributeName="opacity" values="0.25;0.8;0.25" dur="2.6s" begin="{cell * 0.29:.2f}s" repeatCount="indefinite" />
  </path>
</svg>
"""


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "ttt").mkdir(exist_ok=True)
    for locale in CONTENT:
        (ASSETS / f"header{suffix(locale)}.svg").write_text(render_header(locale), encoding="utf-8", newline="\n")
        (ASSETS / f"terminal{suffix(locale)}.svg").write_text(render_terminal(locale), encoding="utf-8", newline="\n")
        (ASSETS / f"stack{suffix(locale)}.svg").write_text(render_stack(locale), encoding="utf-8", newline="\n")
    (ASSETS / "footer.svg").write_text(render_footer(), encoding="utf-8", newline="\n")
    for kind in ("x", "o"):
        (ASSETS / "ttt" / f"{kind}.svg").write_text(render_piece(kind), encoding="utf-8", newline="\n")
        (ASSETS / "ttt" / f"{kind}-win.svg").write_text(render_piece(kind, win=True), encoding="utf-8", newline="\n")
    for cell in range(1, 10):
        (ASSETS / "ttt" / f"empty-{cell}.svg").write_text(render_empty(cell), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
