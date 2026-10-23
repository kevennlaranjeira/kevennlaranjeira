"""Animated cards for the "projects in motion" section: VotoDistribuido and projeto_pdi."""

from __future__ import annotations

import math

from svg_kit import (
    DISPLAY,
    MONO,
    PALETTE,
    card_background,
    card_defs,
    discrete_keytimes,
    esc,
    fonts_for,
    linear_keyframes,
    svg_document,
)


def flash_animation(windows: list[tuple[float, float]], total: float, attribute: str = "opacity") -> str:
    """Discrete on/off animation that is 'on' (1) inside each window."""
    points: list[tuple[float, float]] = [(0.0, 0)]
    for begin, end in sorted(windows):
        points += [(begin, 1), (end, 0)]
    points.append((total, 0))
    values, key_times = discrete_keytimes(points, total)
    return (
        f'<animate attributeName="{attribute}" dur="{total:.2f}s" repeatCount="indefinite" '
        f'calcMode="discrete" values="{values}" keyTimes="{key_times}" />'
    )


def loop_fade(total: float) -> str:
    return (
        f'<animate attributeName="opacity" dur="{total:.2f}s" repeatCount="indefinite" values="0;1;1;0" '
        f'keyTimes="0;{0.4 / total:.4f};{(total - 0.45) / total:.4f};1" />'
    )


# ---------------------------------------------------------------------------
# VotoDistribuido: one vote through the architecture
# ---------------------------------------------------------------------------

VOTE_TEXT = {
    "pt": {
        "title": "Fluxo de um voto",
        "subtitle": "arquitetura do VotoDistribuido · coletores replicados, fila assíncrona e resultado ao vivo",
        "browser": ("navegador", "usuário"),
        "frontend": ("frontend", "Angular"),
        "proxy": ("nginx-proxy", "balanceador"),
        "collector": ("coletor {n}", "Spring Boot"),
        "queue": ("RabbitMQ", "fila"),
        "core": ("core", "agregador"),
        "live": "resultado ao vivo",
    },
    "en": {
        "title": "Path of a vote",
        "subtitle": "VotoDistribuido architecture · replicated collectors, async queue and live results",
        "browser": ("browser", "user"),
        "frontend": ("frontend", "Angular"),
        "proxy": ("nginx-proxy", "load balancer"),
        "collector": ("collector {n}", "Spring Boot"),
        "queue": ("RabbitMQ", "queue"),
        "core": ("core", "aggregator"),
        "live": "live results",
    },
}

VOTES = ["A", "B", "A", "C", "B", "A", "C", "A", "B"]
CANDIDATE_COLORS = {"A": PALETTE["green"], "B": PALETTE["blue"], "C": PALETTE["red"]}

ROW_Y = 232
COLLECTOR_Y = [163, 232, 301]
NODES = {
    "browser": (40, 204, 110, 56),
    "frontend": (180, 204, 120, 56),
    "proxy": (335, 204, 120, 56),
    "collector0": (490, 140, 120, 46),
    "collector1": (490, 209, 120, 46),
    "collector2": (490, 278, 120, 46),
    "queue": (645, 192, 140, 80),
    "core": (820, 204, 140, 56),
    "db_votes": (470, 348, 160, 36),
    "db_core": (820, 348, 140, 36),
}
QUEUE_ENTRY_X = 660
QUEUE_HEAD_X = 766
QUEUE_PITCH = 21
WS_ROUTE = [(890, 204), (890, 118), (240, 118), (240, 204)]

SPEED = 430.0
WS_SPEED = 900.0
NODE_PAUSE = 0.12
EMIT_INTERVAL = 0.55
TAKE_TIME = 0.3
PROCESS_TIME = 0.5
SHIFT_TIME = 0.18


def travel(points: list[tuple[float, float, float]], route: list[tuple[float, float]], speed: float, pause_at: set[int] | None = None) -> float:
    """Append timed positions following `route`; returns the arrival time."""
    moment, x, y = points[-1]
    for index, (nx, ny) in enumerate(route):
        moment += math.hypot(nx - x, ny - y) / speed
        points.append((moment, nx, ny))
        if pause_at and index in pause_at:
            moment += NODE_PAUSE
            points.append((moment, nx, ny))
        x, y = nx, ny
    return moment


def simulate_votes() -> dict:
    """Event simulation: votes reach the queue faster than the aggregator consumes them."""
    tracks: dict[int, list[tuple[float, float, float]]] = {}
    visible: dict[int, tuple[float, float]] = {}
    flashes: dict[str, list[tuple[float, float]]] = {name: [] for name in NODES}
    arrivals: list[tuple[float, int]] = []

    for vote, _ in enumerate(VOTES):
        start = 0.6 + vote * EMIT_INTERVAL
        lane = vote % 3
        cy = COLLECTOR_Y[lane]
        points = [(start, 95.0, ROW_Y)]
        route = [(240, ROW_Y), (395, ROW_Y), (472, ROW_Y), (472, cy), (550, cy), (627, cy), (627, ROW_Y), (QUEUE_ENTRY_X, ROW_Y)]
        travel(points, route, SPEED, pause_at={0, 1, 4})
        reach = {name: next(t for t, x, y in points if (x, y) == target) for name, target in (("frontend", (240, ROW_Y)), ("proxy", (395, ROW_Y)), (f"collector{lane}", (550, cy)))}
        for name, moment in reach.items():
            flashes[name].append((moment, moment + 0.28))
        flashes["db_votes"].append((reach[f"collector{lane}"] + 0.05, reach[f"collector{lane}"] + 0.3))
        tracks[vote] = points
        arrivals.append((points[-1][0], vote))

    waiting: list[int] = []
    settle: dict[int, float] = {}
    slot_x: dict[int, float] = {}
    core_free = 0.0
    ws_tracks: dict[int, list[tuple[float, float, float]]] = {}
    tallies: list[tuple[float, str]] = []
    pending = sorted(arrivals)
    index = 0

    while index < len(pending) or waiting:
        next_arrival = pending[index][0] if index < len(pending) else math.inf
        next_take = max(core_free, settle[waiting[0]]) if waiting else math.inf
        if next_arrival <= next_take:
            moment, vote = pending[index]
            index += 1
            flashes["queue"].append((moment, moment + 0.28))
            x = QUEUE_HEAD_X - len(waiting) * QUEUE_PITCH
            tracks[vote].append((moment + (x - QUEUE_ENTRY_X) / SPEED, x, ROW_Y))
            settle[vote] = tracks[vote][-1][0]
            slot_x[vote] = x
            waiting.append(vote)
            continue

        moment = next_take
        head = waiting.pop(0)
        tracks[head] += [(moment, QUEUE_HEAD_X, ROW_Y), (moment + TAKE_TIME, 890, ROW_Y)]
        visible[head] = (tracks[head][0][0], moment + TAKE_TIME)
        done = moment + TAKE_TIME + PROCESS_TIME
        flashes["core"].append((moment + TAKE_TIME, done))
        flashes["db_core"].append((moment + TAKE_TIME + 0.2, moment + TAKE_TIME + 0.45))
        ws = [(done, *WS_ROUTE[0])]
        arrival = travel(ws, WS_ROUTE[1:], WS_SPEED)
        ws_tracks[head] = ws
        flashes["frontend"].append((arrival, arrival + 0.28))
        tallies.append((arrival, VOTES[head]))
        core_free = done

        for position, vote in enumerate(waiting):
            begin = max(moment, settle[vote])
            target = QUEUE_HEAD_X - position * QUEUE_PITCH
            tracks[vote] += [(begin, slot_x[vote], ROW_Y), (begin + SHIFT_TIME, target, ROW_Y)]
            settle[vote] = begin + SHIFT_TIME
            slot_x[vote] = target

    return {"tracks": tracks, "visible": visible, "ws": ws_tracks, "flashes": flashes, "tallies": tallies}


def animated_dot(points: list[tuple[float, float, float]], window: tuple[float, float], total: float, color: str, radius: float) -> str:
    cx_values, cx_times = linear_keyframes([(t, round(x, 1)) for t, x, _ in points], total)
    cy_values, cy_times = linear_keyframes([(t, round(y, 1)) for t, _, y in points], total)
    return f"""
    <circle cx="{points[0][1]:.1f}" cy="{points[0][2]:.1f}" r="{radius}" fill="{color}" opacity="0">
      <animate attributeName="cx" dur="{total:.2f}s" repeatCount="indefinite" values="{cx_values}" keyTimes="{cx_times}" />
      <animate attributeName="cy" dur="{total:.2f}s" repeatCount="indefinite" values="{cy_values}" keyTimes="{cy_times}" />
      {flash_animation([window], total)}
    </circle>"""


def render_vote_flow(locale: str) -> str:
    text = VOTE_TEXT[locale]
    width, height = 1000, 410
    sim = simulate_votes()
    total = max(moment for moment, _ in sim["tallies"]) + 2.6

    texts = [text["subtitle"], text["live"], "WebSocket", "postgres_eleicao", "postgres_core", "A", "B", "C", "0123456789"]
    labels = {
        "browser": text["browser"],
        "frontend": text["frontend"],
        "proxy": text["proxy"],
        "queue": text["queue"],
        "core": text["core"],
        "db_votes": ("postgres_eleicao", ""),
        "db_core": ("postgres_core", ""),
    }
    for lane in range(3):
        name, sub = text["collector"]
        labels[f"collector{lane}"] = (name.format(n=lane + 1), sub)

    nodes: dict[str, str] = {}
    for name, (x, y, w, h) in NODES.items():
        title, sub = labels[name]
        texts += [title, sub]
        title_y = y + (h / 2 - 2 if sub else h / 2 + 4)
        if name == "queue":
            title_y = y + 20
        nodes[name] = (
            f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PALETTE['panel']}" stroke="{PALETTE['line']}" />
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" stroke="{PALETTE['amber']}" stroke-width="1.6" opacity="0">{flash_animation(sim['flashes'][name], total)}</rect>
  <text x="{x + w / 2}" y="{title_y}" class="node" text-anchor="middle">{esc(title)}</text>"""
            + (f'\n  <text x="{x + w / 2}" y="{title_y + 15}" class="sub" text-anchor="middle">{esc(sub)}</text>' if sub and name != "queue" else "")
        )
    queue_x, queue_y, queue_w, _ = NODES["queue"]
    queue_slots = "".join(
        f'<rect x="{QUEUE_HEAD_X - k * QUEUE_PITCH - 8}" y="{ROW_Y - 8}" width="16" height="16" rx="4" fill="{PALETTE["grid"]}" />'
        for k in range(5)
    )
    queue_sub = f'<text x="{queue_x + queue_w / 2}" y="{queue_y + 70}" class="sub" text-anchor="middle">{esc(text["queue"][1])}</text>'

    edges = [
        "M150 232 H180",
        "M300 232 H335",
        "M455 232 H472 V163 H490",
        "M472 232 H490",
        "M472 232 V301 H490",
        "M610 163 H627 V232 H645",
        "M610 232 H645",
        "M610 301 H627 V232",
        "M785 232 H820",
        "M550 324 V348",
        "M890 260 V348",
    ]
    edge_paths = "".join(f'\n  <path d="{d}" class="edge" />' for d in edges)
    ws_path = "M" + " L".join(f"{x},{y}" for x, y in WS_ROUTE)

    # Dots are drawn above the queue but below the other boxes, so a vote disappears
    # into a service while it is being handled and only shows on wires and in the queue
    dots = []
    for vote, points in sim["tracks"].items():
        dots.append(animated_dot(points, sim["visible"][vote], total, CANDIDATE_COLORS[VOTES[vote]], 6))
    for vote, points in sim["ws"].items():
        dots.append(animated_dot(points, (points[0][0], points[-1][0]), total, CANDIDATE_COLORS[VOTES[vote]], 4))

    # Live tally: bar width and count step up each time a WebSocket update lands
    unit = 46
    tally_parts = [f'<text x="40" y="318" class="live">{esc(text["live"])}</text>']
    for row, candidate in enumerate("ABC"):
        y = 332 + row * 20
        times = [moment for moment, name in sim["tallies"] if name == candidate]
        final = len(times) * unit
        width_points = [(0.0, 0.0)] + [(moment, (k + 1) * unit) for k, moment in enumerate(times)] + [(total, final)]
        values, key_times = discrete_keytimes(width_points, total)
        tally_parts.append(
            f"""
  <text x="40" y="{y + 9}" class="candidate">{candidate}</text>
  <rect x="58" y="{y}" width="{4 * unit}" height="10" rx="5" fill="{PALETTE['grid']}" />
  <rect x="58" y="{y}" width="{final}" height="10" rx="5" fill="{CANDIDATE_COLORS[candidate]}">
    <animate attributeName="width" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" values="{values}" keyTimes="{key_times}" />
  </rect>"""
        )
        bounds = [0.0, *times, total]
        for count in range(len(times) + 1):
            tally_parts.append(
                f'<text x="{58 + 4 * unit + 10}" y="{y + 9}" class="count">{count}{flash_animation([(bounds[count], bounds[count + 1])], total)}</text>'
            )

    defs = card_defs("v")
    style = fonts_for({"mono": texts, "display": [text["title"]]}) + f"""
      .title {{ font: 700 24px {DISPLAY}; fill: {PALETTE['text']}; }}
      .subtitle {{ font: 400 12px {MONO}; fill: {PALETTE['muted']}; }}
      .node {{ font: 700 12px {MONO}; fill: {PALETTE['text']}; }}
      .sub {{ font: 400 10px {MONO}; fill: {PALETTE['faint']}; }}
      .edge {{ stroke: #30363d; stroke-width: 1.5; stroke-dasharray: 3 6; }}
      .ws {{ stroke: {PALETTE['blue']}; stroke-width: 1.4; stroke-dasharray: 2 6; opacity: 0.55; }}
      .ws-label {{ font: 400 10px {MONO}; fill: {PALETTE['blue']}; }}
      .live {{ font: 400 11px {MONO}; fill: {PALETTE['muted']}; }}
      .candidate {{ font: 700 11px {MONO}; fill: {PALETTE['text']}; }}
      .count {{ font: 700 11px {MONO}; fill: {PALETTE['text']}; }}"""

    flow = '<animate attributeName="stroke-dashoffset" values="9;0" dur="0.7s" repeatCount="indefinite" />'
    body = card_background("v", width, height) + f"""
  <text x="40" y="56" class="title">{esc(text['title'])}</text>
  <text x="40" y="80" class="subtitle">{esc(text['subtitle'])}</text>
  <g>{edge_paths.replace('class="edge" />', f'class="edge">{flow}</path>')}
    <path d="{ws_path}" class="ws">{flow}</path>
    <text x="565" y="111" class="ws-label" text-anchor="middle">WebSocket</text>
  </g>
  {nodes.pop('queue')}
  {queue_slots}{queue_sub}
  <g>{loop_fade(total)}{''.join(dots)}
  </g>
  {''.join(nodes.values())}
  {''.join(tally_parts)}"""
    return svg_document(width, height, f"{text['title']}: {text['subtitle']}", defs, style, body)


# ---------------------------------------------------------------------------
# projeto_pdi: Sobel filter sweeping an image
# ---------------------------------------------------------------------------

SOBEL_TEXT = {
    "pt": {
        "title": "Filtro de Sobel",
        "subtitle": "a janela 3×3 percorre a imagem e calcula o gradiente de cada pixel · como no projeto_pdi",
        "input": "entrada",
        "output": "bordas",
    },
    "en": {
        "title": "Sobel filter",
        "subtitle": "a 3×3 window sweeps the image and computes each pixel's gradient · as in projeto_pdi",
        "input": "input",
        "output": "edges",
    },
}
IMAGE_W, IMAGE_H, CELL = 36, 20, 7
GX = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
GY = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]


def scene() -> list[list[float]]:
    """A small grayscale scene: sky, sun, house with windows, tree and ground."""
    image = []
    for y in range(IMAGE_H):
        row = []
        for x in range(IMAGE_W):
            value = 0.16 + 0.1 * y / IMAGE_H
            if y >= 16:
                value = 0.34
            if math.hypot(x - 28, y - 4.5) <= 3.1:
                value = 0.95
            if 4 <= x <= 13 and 9 <= y <= 17:
                value = 0.62
                if (x in (6, 7, 10, 11)) and (y in (11, 12)):
                    value = 0.28
                if 8 <= x <= 9 and y >= 14:
                    value = 0.3
            roof_half = (y - 3) * 1.0
            if 3 <= y <= 8 and abs(x - 8.5) <= roof_half + 0.5:
                value = 0.8
            if math.hypot(x - 20.5, y - 10) <= 3.2:
                value = 0.5
            if 20 <= x <= 21 and 13 <= y <= 16:
                value = 0.42
            row.append(value)
        image.append(row)
    return image


def sobel(image: list[list[float]]) -> list[list[float]]:
    height, width = len(image), len(image[0])

    def at(x: int, y: int) -> float:
        return image[min(max(y, 0), height - 1)][min(max(x, 0), width - 1)]

    magnitude = []
    for y in range(height):
        row = []
        for x in range(width):
            gx = sum(GX[j][i] * at(x + i - 1, y + j - 1) for j in range(3) for i in range(3))
            gy = sum(GY[j][i] * at(x + i - 1, y + j - 1) for j in range(3) for i in range(3))
            row.append(math.hypot(gx, gy))
        magnitude.append(row)
    peak = max(max(row) for row in magnitude) or 1.0
    return [[value / peak for value in row] for row in magnitude]


def mix(color_a: str, color_b: str, ratio: float) -> str:
    a = [int(color_a[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * ratio):02x}" for x, y in zip(a, b))


def gray(value: float) -> str:
    return mix("#0b0f14", "#e6edf3", value)


def edge_color(value: float) -> str:
    if value < 0.06:
        return PALETTE["bg"]
    if value < 0.5:
        return mix(PALETTE["bg"], PALETTE["green"], value / 0.5)
    return mix(PALETTE["green"], PALETTE["blue"], (value - 0.5) / 0.5)


def pixel_runs(image: list[list[float]], color, x0: float, y0: float) -> str:
    """Draw one rect per horizontal run of equal color instead of one per pixel."""
    rects = []
    for y, row in enumerate(image):
        colors = [color(value) for value in row]
        start = 0
        for x in range(1, len(row) + 1):
            if x == len(row) or colors[x] != colors[start]:
                rects.append(
                    f'<rect x="{x0 + start * CELL}" y="{y0 + y * CELL}" width="{(x - start) * CELL}" height="{CELL}" fill="{colors[start]}" />'
                )
                start = x
    return "".join(rects)


def kernel_grid(matrix: list[list[int]], x0: float, y0: float, label: str) -> str:
    size = 26
    cells = [f'<text x="{x0 + 1.5 * size}" y="{y0 - 10}" class="klabel" text-anchor="middle">{label}</text>']
    for j, row in enumerate(matrix):
        for i, weight in enumerate(row):
            x, y = x0 + i * size, y0 + j * size
            tone = PALETTE["green"] if weight > 0 else PALETTE["blue"] if weight < 0 else PALETTE["faint"]
            cells.append(
                f'<rect x="{x}" y="{y}" width="{size - 3}" height="{size - 3}" rx="4" fill="{PALETTE["panel"]}" stroke="{PALETTE["line"]}" />'
                f'<text x="{x + (size - 3) / 2}" y="{y + 16}" class="weight" fill="{tone}" text-anchor="middle">{f"{weight:+d}" if weight else "0"}</text>'
            )
    return "".join(cells)


def render_sobel(locale: str) -> str:
    text = SOBEL_TEXT[locale]
    width, height = 1000, 300
    image = scene()
    edges = sobel(image)
    image_w, image_h = IMAGE_W * CELL, IMAGE_H * CELL
    in_x, out_x, top = 40, width - 40 - image_w, 128

    start, row_time = 0.6, 0.34
    total = start + IMAGE_H * row_time + 2.6

    # The window moves left to right along each row; the output row is revealed behind it
    window_x, window_y, cursor_x, cursor_y, reveal = [], [], [], [], []
    for row in range(IMAGE_H):
        begin, end = start + row * row_time, start + (row + 1) * row_time
        window_x += [(begin, in_x - CELL), (end, in_x + (IMAGE_W - 2) * CELL)]
        cursor_x += [(begin, out_x), (end, out_x + (IMAGE_W - 1) * CELL)]
        window_y.append((begin, top + (row - 1) * CELL))
        cursor_y.append((begin, top + row * CELL))
        values, key_times = linear_keyframes([(0.0, 0), (begin, 0), (end, image_w), (total, image_w)], total)
        reveal.append(
            f'<rect x="{out_x}" y="{top + row * CELL}" width="{image_w}" height="{CELL}">'
            f'<animate attributeName="width" dur="{total:.2f}s" repeatCount="indefinite" values="{values}" keyTimes="{key_times}" /></rect>'
        )
    scan_end = start + IMAGE_H * row_time
    window_x.append((total, in_x - CELL))
    cursor_x.append((total, out_x))
    wx_values, wx_times = linear_keyframes(window_x, total)
    cx_values, cx_times = linear_keyframes(cursor_x, total)
    wy_values, wy_times = discrete_keytimes(window_y + [(total, top - CELL)], total)
    cy_values, cy_times = discrete_keytimes(cursor_y + [(total, top)], total)
    scanning = flash_animation([(start, scan_end)], total)

    mid_x = in_x + image_w + (out_x - in_x - image_w) / 2
    texts = [text["subtitle"], text["input"], text["output"], "Gx", "Gy", "+1+2-1-20", "|G| = √(Gx² + Gy²)"]
    defs = card_defs("e") + f"""
    <clipPath id="e-reveal">{''.join(reveal)}</clipPath>
    <linearGradient id="e-arrow" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{PALETTE['green']}" />
      <stop offset="1" stop-color="{PALETTE['blue']}" />
    </linearGradient>"""
    style = fonts_for({"mono": texts, "display": [text["title"]]}) + f"""
      .title {{ font: 700 24px {DISPLAY}; fill: {PALETTE['text']}; }}
      .subtitle {{ font: 400 12px {MONO}; fill: {PALETTE['muted']}; }}
      .label {{ font: 400 11px {MONO}; fill: {PALETTE['muted']}; }}
      .klabel {{ font: 700 12px {MONO}; fill: {PALETTE['text']}; }}
      .weight {{ font: 700 11px {MONO}; }}
      .formula {{ font: 400 12px {MONO}; fill: {PALETTE['muted']}; }}"""

    body = card_background("e", width, height) + f"""
  <text x="40" y="56" class="title">{esc(text['title'])}</text>
  <text x="40" y="80" class="subtitle">{esc(text['subtitle'])}</text>
  <text x="{in_x}" y="{top - 10}" class="label">{esc(text['input'])}</text>
  <text x="{out_x}" y="{top - 10}" class="label">{esc(text['output'])}</text>
  <g>{pixel_runs(image, gray, in_x, top)}</g>
  <rect x="{out_x}" y="{top}" width="{image_w}" height="{image_h}" fill="{PALETTE['bg']}" stroke="{PALETTE['line']}" />
  <g clip-path="url(#e-reveal)">{pixel_runs(edges, edge_color, out_x, top)}</g>
  <rect x="{in_x - CELL}" y="{top - CELL}" width="{3 * CELL}" height="{3 * CELL}" stroke="{PALETTE['amber']}" stroke-width="1.6" opacity="0">
    <animate attributeName="x" dur="{total:.2f}s" repeatCount="indefinite" values="{wx_values}" keyTimes="{wx_times}" />
    <animate attributeName="y" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" values="{wy_values}" keyTimes="{wy_times}" />
    {scanning}
  </rect>
  <rect x="{out_x}" y="{top}" width="{CELL}" height="{CELL}" fill="{PALETTE['amber']}" opacity="0">
    <animate attributeName="x" dur="{total:.2f}s" repeatCount="indefinite" values="{cx_values}" keyTimes="{cx_times}" />
    <animate attributeName="y" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" values="{cy_values}" keyTimes="{cy_times}" />
    {scanning}
  </rect>
  {kernel_grid(GX, mid_x - 92, top + 22, 'Gx')}
  {kernel_grid(GY, mid_x + 16, top + 22, 'Gy')}
  <text x="{mid_x}" y="{top + 122}" class="formula" text-anchor="middle">|G| = √(Gx² + Gy²)</text>
  <path d="M{mid_x - 70} {top + 146} H{mid_x + 62}" stroke="url(#e-arrow)" stroke-width="2" stroke-dasharray="4 5">
    <animate attributeName="stroke-dashoffset" values="9;0" dur="0.7s" repeatCount="indefinite" />
  </path>
  <path d="M{mid_x + 62} {top + 141} L{mid_x + 70} {top + 146} L{mid_x + 62} {top + 151}" stroke="{PALETTE['blue']}" stroke-width="2" stroke-linejoin="round" />"""
    return svg_document(width, height, f"{text['title']}: {text['subtitle']}", defs, style, body)
