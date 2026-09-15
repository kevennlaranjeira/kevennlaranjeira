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
                [
                    ("algoritmos/  arquiteturas/  backend/  bancos-de-dados/", "dir"),
                    ("integração-de-dados/  processamento-de-imagens/  automação/", "dir"),
                ],
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
                [
                    ("algorithms/  architectures/  backend/  databases/", "dir"),
                    ("data-integration/  image-processing/  automation/", "dir"),
                ],
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
# Sorting race
# ---------------------------------------------------------------------------

RACE_VALUES = [12, 10, 11, 5, 6, 14, 13, 4, 9, 2, 8, 1, 3, 7]
RACE_TEXT = {
    "pt": {
        "title": "Corrida de ordenação",
        "subtitle": "mesmo vetor embaralhado · cada comparação e cada troca levam o mesmo tempo",
        "place": "{place}º lugar · {ops} operações",
    },
    "en": {
        "title": "Sorting race",
        "subtitle": "same shuffled array · every comparison and every swap takes the same time",
        "place": "{place} place · {ops} operations",
    },
}
ORDINALS_EN = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}

# Seconds each operation takes on screen
COMPARE_TIME = 0.05
SWAP_TIME = 0.14
MERGE_TIME = 0.34


def bubble_trace(values: list[int]) -> list[tuple]:
    arr, events = list(values), []
    for end in range(len(arr) - 1, 0, -1):
        swapped = False
        for i in range(end):
            events.append(("cmp",))
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                events.append(("swap", i, i + 1))
                swapped = True
        if not swapped:
            break
    return events


def heap_trace(values: list[int]) -> list[tuple]:
    arr, events = list(values), []

    def sift(root: int, end: int) -> None:
        while 2 * root + 1 < end:
            child = 2 * root + 1
            if child + 1 < end:
                events.append(("cmp",))
                if arr[child] < arr[child + 1]:
                    child += 1
            events.append(("cmp",))
            if arr[root] >= arr[child]:
                return
            arr[root], arr[child] = arr[child], arr[root]
            events.append(("swap", root, child))
            root = child

    for start in range(len(arr) // 2 - 1, -1, -1):
        sift(start, len(arr))
    for end in range(len(arr) - 1, 0, -1):
        arr[0], arr[end] = arr[end], arr[0]
        events.append(("swap", 0, end))
        sift(0, end)
    return events


def merge_trace(values: list[int]) -> list[tuple]:
    arr, events = list(values), []

    def sort(lo: int, hi: int) -> None:
        if hi - lo < 2:
            return
        mid = (lo + hi) // 2
        sort(lo, mid)
        sort(mid, hi)
        left, right = arr[lo:mid], arr[mid:hi]
        merged: list[int] = []
        i = j = 0
        while i < len(left) and j < len(right):
            events.append(("cmp",))
            if left[i] <= right[j]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        merged += left[i:] + right[j:]
        arr[lo:hi] = merged
        events.append(("place", lo, merged))

    sort(0, len(arr))
    return events


def quick_trace(values: list[int]) -> list[tuple]:
    """Hoare partition with the middle element as pivot, like SortLab's middle-pivot QuickSort."""
    arr, events = list(values), []

    def sort(lo: int, hi: int) -> None:
        if lo >= hi:
            return
        pivot = arr[(lo + hi) // 2]
        i, j = lo, hi
        while i <= j:
            events.append(("cmp",))
            while arr[i] < pivot:
                i += 1
                events.append(("cmp",))
            events.append(("cmp",))
            while arr[j] > pivot:
                j -= 1
                events.append(("cmp",))
            if i <= j:
                if i != j:
                    arr[i], arr[j] = arr[j], arr[i]
                    events.append(("swap", i, j))
                i += 1
                j -= 1
        sort(lo, j)
        sort(i, hi)

    sort(0, len(arr) - 1)
    return events


RACE_ALGORITHMS = [
    ("bubble sort", "O(n²)", bubble_trace),
    ("heap sort", "O(n log n)", heap_trace),
    ("merge sort", "O(n log n)", merge_trace),
    ("quick sort", "O(n log n)", quick_trace),
]


def run_trace(values: list[int], events: list[tuple], start: float) -> tuple[dict, dict, float, int]:
    """Turn a trace into per-bar position keyframes and highlight windows."""
    arr = list(values)
    tracks = {value: [(0.0, index), (start, index)] for index, value in enumerate(arr)}
    flashes: dict[int, list[tuple[float, float]]] = {value: [] for value in arr}
    moment, operations = start, 0

    for event in events:
        if event[0] == "cmp":
            moment += COMPARE_TIME
            operations += 1
        elif event[0] == "swap":
            _, i, j = event
            for value, source, target in ((arr[i], i, j), (arr[j], j, i)):
                tracks[value] += [(moment, source), (moment + SWAP_TIME, target)]
                flashes[value].append((moment, moment + SWAP_TIME))
            arr[i], arr[j] = arr[j], arr[i]
            moment += SWAP_TIME
            operations += 1
        else:
            _, lo, merged = event
            positions = {value: index for index, value in enumerate(arr)}
            for offset, value in enumerate(merged):
                if positions[value] != lo + offset:
                    tracks[value] += [(moment, positions[value]), (moment + MERGE_TIME, lo + offset)]
                    flashes[value].append((moment, moment + MERGE_TIME))
            arr[lo : lo + len(merged)] = merged
            moment += MERGE_TIME
            operations += len(merged)

    if arr != sorted(values):
        raise ValueError("trace did not sort the array")
    return tracks, flashes, moment, operations


def linear_keyframes(points: list[tuple[float, float]], total: float) -> tuple[str, str]:
    cleaned: list[tuple[float, float]] = []
    for time, value in points:
        if cleaned and time <= cleaned[-1][0]:
            if value == cleaned[-1][1]:
                continue
            time = cleaned[-1][0] + 0.001
        cleaned.append((time, value))
    if cleaned[-1][0] < total:
        cleaned.append((total, cleaned[-1][1]))
    values = ";".join(f"{value:g}" for _, value in cleaned)
    key_times = ";".join(f"{time / total:.5f}" for time, _ in cleaned)
    return values, key_times


def bar_color(value: int, count: int) -> str:
    start = (0x3F, 0xB9, 0x50)
    end = (0x58, 0xA6, 0xFF)
    ratio = (value - 1) / (count - 1)
    return "#" + "".join(f"{round(a + (b - a) * ratio):02x}" for a, b in zip(start, end))


def render_sorting_race(locale: str) -> str:
    text = RACE_TEXT[locale]
    width, height = 1000, 330
    count = len(RACE_VALUES)
    start = 0.8
    panel_width, gap, x0, panel_y, panel_height = 220, 20, 40, 104, 200
    pitch, bar_width, max_bar = 15, 11, 112
    baseline = panel_y + 150

    runs = []
    for name, complexity, tracer in RACE_ALGORITHMS:
        tracks, flashes, finish, operations = run_trace(RACE_VALUES, tracer(RACE_VALUES), start)
        runs.append((name, complexity, tracks, flashes, finish, operations))
    total = max(run[4] for run in runs) + 3.0
    order = sorted(range(len(runs)), key=lambda index: runs[index][4])
    places = {index: position + 1 for position, index in enumerate(order)}

    texts = [text["title"], text["subtitle"]]
    panels: list[str] = []
    for index, (name, complexity, tracks, flashes, finish, operations) in enumerate(runs):
        px = x0 + index * (panel_width + gap)
        bars_x = px + (panel_width - (count - 1) * pitch - bar_width) / 2
        place = places[index]
        place_label = text["place"].format(place=place if locale == "pt" else ORDINALS_EN[place], ops=operations)
        texts += [name, complexity, place_label]

        bars = []
        for value in RACE_VALUES:
            points = [(time, round(bars_x + slot * pitch, 1)) for time, slot in tracks[value]]
            x_values, x_times = linear_keyframes(points, total)
            base = bar_color(value, count)
            color_points = [(0.0, base)]
            for begin, end in flashes[value]:
                color_points += [(begin, PALETTE["amber"]), (end, base)]
            color_values = ";".join(color for _, color in color_points)
            color_times = ";".join(f"{time / total:.5f}" for time, _ in color_points)
            bar_height = max_bar * value / count
            initial_x = bars_x + RACE_VALUES.index(value) * pitch
            bars.append(
                f"""
      <rect x="{initial_x:.1f}" y="{baseline - bar_height:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="2" fill="{base}">
        <animate attributeName="x" dur="{total:.2f}s" repeatCount="indefinite" values="{x_values}" keyTimes="{x_times}" />
        <animate attributeName="fill" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" values="{color_values}" keyTimes="{color_times}" />
      </rect>"""
            )

        finished_values, finished_times = discrete_keytimes([(0.0, 0), (finish, 1), (total, 1)], total)
        progress_width = panel_width - 32
        panels.append(
            f"""
  <g>
    <rect x="{px}" y="{panel_y}" width="{panel_width}" height="{panel_height}" rx="12" fill="{PALETTE['panel']}" stroke="{PALETTE['line']}" />
    <rect x="{px}" y="{panel_y}" width="{panel_width}" height="{panel_height}" rx="12" stroke="{PALETTE['green']}" stroke-width="1.5">
      <animate attributeName="opacity" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" values="{finished_values}" keyTimes="{finished_times}" />
    </rect>
    <text x="{px + 16}" y="{panel_y + 28}" class="algo">{esc(name)}</text>
    <text x="{px + panel_width - 16}" y="{panel_y + 28}" class="complexity" text-anchor="end">{esc(complexity)}</text>{''.join(bars)}
    <rect x="{px + 16}" y="{baseline + 14}" width="{progress_width}" height="4" rx="2" fill="{PALETTE['grid']}" />
    <rect x="{px + 16}" y="{baseline + 14}" width="{progress_width}" height="4" rx="2" fill="url(#r-progress)">
      <animate attributeName="width" dur="{total:.2f}s" repeatCount="indefinite" values="0;0;{progress_width};{progress_width}" keyTimes="0;{start / total:.4f};{finish / total:.4f};1" />
    </rect>
    <text x="{px + 16}" y="{baseline + 38}" class="place place-{place}">{esc(place_label)}
      <animate attributeName="opacity" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" values="{finished_values}" keyTimes="{finished_times}" />
    </text>
  </g>"""
        )

    fade_times = f"0;{0.4 / total:.4f};{(total - 0.45) / total:.4f};1"
    defs = card_defs("r") + f"""
    <linearGradient id="r-progress" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{PALETTE['green']}" />
      <stop offset="1" stop-color="{PALETTE['blue']}" />
    </linearGradient>"""
    style = fonts_for({"mono": texts[1:], "display": [text["title"]]}) + f"""
      .title {{ font: 700 24px {DISPLAY}; fill: {PALETTE['text']}; }}
      .subtitle {{ font: 400 12px {MONO}; fill: {PALETTE['muted']}; }}
      .algo {{ font: 700 13px {MONO}; fill: {PALETTE['text']}; }}
      .complexity {{ font: 400 11px {MONO}; fill: {PALETTE['faint']}; }}
      .place {{ font: 700 11px {MONO}; fill: {PALETTE['muted']}; }}
      .place-1 {{ fill: {PALETTE['amber']}; }}"""
    body = card_background("r", width, height) + f"""
  <text x="40" y="56" class="title">{esc(text['title'])}</text>
  <text x="40" y="80" class="subtitle">{esc(text['subtitle'])}</text>
  <g>
    <animate attributeName="opacity" dur="{total:.2f}s" repeatCount="indefinite" values="0;1;1;0" keyTimes="{fade_times}" />{''.join(panels)}
  </g>"""
    title = f"{text['title']}: " + ", ".join(name for name, *_ in RACE_ALGORITHMS)
    return svg_document(width, height, title, defs, style, body)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for locale in CONTENT:
        (ASSETS / f"header{suffix(locale)}.svg").write_text(render_header(locale), encoding="utf-8", newline="\n")
        (ASSETS / f"terminal{suffix(locale)}.svg").write_text(render_terminal(locale), encoding="utf-8", newline="\n")
        (ASSETS / f"stack{suffix(locale)}.svg").write_text(render_stack(locale), encoding="utf-8", newline="\n")
        (ASSETS / f"sorting-race{suffix(locale)}.svg").write_text(render_sorting_race(locale), encoding="utf-8", newline="\n")
    (ASSETS / "footer.svg").write_text(render_footer(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
