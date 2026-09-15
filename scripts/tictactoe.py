#!/usr/bin/env python3
"""Tic-tac-toe played through GitHub issues.

Visitors click an empty cell in the profile README, which opens an issue titled
"ttt|<cell>". The workflow runs `play`, which applies every pending move, lets
the bot answer, saves game/state.json, re-renders both READMEs and writes an
outbox. Only after the commit is pushed does `notify` comment on and close the
issues, so a failed push leaves them open for the next run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import random
import re
import sys
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from update_profile import replace_section

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "game" / "state.json"
READMES = {"pt": ROOT / "README.md", "en": ROOT / "README.en.md"}
BR_TZ = ZoneInfo("America/Sao_Paulo")
TITLE_PREFIX = "ttt|"
TITLE_PATTERN = re.compile(r"^\s*ttt\|([1-9])\s*$", re.IGNORECASE)
LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))

# Chance of the bot playing a random cell instead of the best one. A perfect
# bot can never lose, which gets boring fast.
MISTAKE_RATE = 0.2

TEXT = {
    "pt": {
        "turn": "Partida #{game} · sua vez, você joga com X",
        "last": {
            "x": "Partida #{game}: {player} venceu o bot",
            "o": "Partida #{game}: o bot venceu {player}",
            "draw": "Partida #{game}: empate entre {player} e o bot",
        },
        "score": "Placar geral: visitantes <b>{visitors}</b> · bot <b>{bot}</b> · empates <b>{draws}</b>",
        "ranking": ["#", "Jogador", "Vitórias", "Empates", "Jogadas"],
        "ranking_empty": "Ninguém entrou no ranking ainda.",
        "recent": "Últimas jogadas",
        "recent_item": "{player} na casa {cell}",
        "recent_bot": ", bot na {cell}",
        "cell_alt": "casa {n} livre",
        "issue_body": (
            "Clique em **Create** para enviar sua jogada. Não precisa escrever nada aqui.\n\n"
            "Em menos de um minuto o bot responde nesta issue e o tabuleiro do perfil muda."
        ),
        "board_link": "https://github.com/{owner}#jogo-da-velha",
    },
    "en": {
        "turn": "Game #{game} · your turn, you play X",
        "last": {
            "x": "Game #{game}: {player} beat the bot",
            "o": "Game #{game}: the bot beat {player}",
            "draw": "Game #{game}: {player} and the bot tied",
        },
        "score": "Scoreboard: visitors <b>{visitors}</b> · bot <b>{bot}</b> · draws <b>{draws}</b>",
        "ranking": ["#", "Player", "Wins", "Draws", "Moves"],
        "ranking_empty": "Nobody is on the leaderboard yet.",
        "recent": "Latest moves",
        "recent_item": "{player} on cell {cell}",
        "recent_bot": ", bot on {cell}",
        "cell_alt": "cell {n} empty",
        "issue_body": (
            "Click **Create** to send your move. You don't need to write anything.\n\n"
            "In less than a minute the bot answers here and the board on the profile changes."
        ),
        "board_link": "https://github.com/{owner}/{owner}/blob/main/README.en.md#tic-tac-toe",
    },
}


# ---------------------------------------------------------------------------
# Game rules
# ---------------------------------------------------------------------------


def new_state() -> dict:
    return {
        "game": 1,
        "board": [""] * 9,
        "stats": {"visitors": 0, "bot": 0, "draws": 0},
        "players": {},
        "recent": [],
        "last_game": None,
    }


def outcome(board: list[str] | tuple[str, ...]) -> tuple[str | None, list[int]]:
    for line in LINES:
        a, b, c = line
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], list(line)
    if all(board):
        return "draw", []
    return None, []


@lru_cache(maxsize=None)
def minimax(board: tuple[str, ...], player: str) -> int:
    """Score for the bot (O): positive means O wins, faster wins score higher."""
    result, _ = outcome(board)
    empty = board.count("")
    if result == "o":
        return 1 + empty
    if result == "x":
        return -1 - empty
    if result == "draw":
        return 0
    scores = []
    for index, cell in enumerate(board):
        if not cell:
            following = list(board)
            following[index] = player
            scores.append(minimax(tuple(following), "x" if player == "o" else "o"))
    return max(scores) if player == "o" else min(scores)


def bot_move(board: list[str], rng: random.Random) -> int:
    empty = [index for index, cell in enumerate(board) if not cell]
    if rng.random() < MISTAKE_RATE:
        return rng.choice(empty)
    scored = []
    for index in empty:
        following = list(board)
        following[index] = "o"
        scored.append((minimax(tuple(following), "x"), index))
    best = max(score for score, _ in scored)
    return rng.choice([index for score, index in scored if score == best])


def apply_move(state: dict, login: str, cell: int, rng: random.Random, now: dt.datetime) -> dict:
    board = state["board"]
    if board[cell]:
        return {"status": "occupied", "login": login, "cell": cell}

    game = state["game"]
    board[cell] = "x"
    player = state["players"].setdefault(login, {"wins": 0, "draws": 0, "losses": 0, "moves": 0})
    player["moves"] += 1

    result, line = outcome(board)
    bot_cell = None
    if result is None:
        bot_cell = bot_move(board, rng)
        board[bot_cell] = "o"
        result, line = outcome(board)

    event = {
        "status": "played",
        "game": game,
        "login": login,
        "cell": cell,
        "bot_cell": bot_cell,
        "result": result,
        "line": line,
        "board": list(board),
        "at": now.isoformat(timespec="minutes"),
    }

    if result:
        state["stats"][{"x": "visitors", "o": "bot", "draw": "draws"}[result]] += 1
        player[{"x": "wins", "o": "losses", "draw": "draws"}[result]] += 1
        state["last_game"] = {"game": game, "result": result, "login": login, "board": list(board), "line": line}
        state["game"] += 1
        state["board"] = [""] * 9

    summary = {key: event[key] for key in ("game", "login", "cell", "bot_cell", "result", "at")}
    state["recent"] = [summary, *state["recent"]][:5]
    return event


# ---------------------------------------------------------------------------
# README rendering
# ---------------------------------------------------------------------------


def player_link(login: str) -> str:
    safe = html.escape(login)
    return f'<a href="https://github.com/{safe}">@{safe}</a>'


def issue_url(repo: str, cell: int, locale: str) -> str:
    query = urllib.parse.urlencode(
        {"title": f"{TITLE_PREFIX}{cell + 1}", "body": TEXT[locale]["issue_body"]},
        quote_via=urllib.parse.quote,
    )
    return f"https://github.com/{repo}/issues/new?{query}"


def render_board(board: list[str], repo: str, locale: str, size: int, line: list[int] | None = None, clickable: bool = True) -> str:
    rows = []
    for row in range(3):
        cells = []
        for column in range(3):
            index = row * 3 + column
            piece = board[index]
            if piece:
                name = f"{piece}-win" if line and index in line else piece
                cells.append(f'<td><img src="assets/ttt/{name}.svg" width="{size}" alt="{piece.upper()}" /></td>')
            elif clickable:
                alt = TEXT[locale]["cell_alt"].format(n=index + 1)
                url = html.escape(issue_url(repo, index, locale))
                cells.append(f'<td><a href="{url}"><img src="assets/ttt/empty-{index + 1}.svg" width="{size}" alt="{alt}" /></a></td>')
            else:
                cells.append(f'<td><img src="assets/ttt/empty-{index + 1}.svg" width="{size}" alt="" /></td>')
        rows.append("  <tr>" + "".join(cells) + "</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def render_game(state: dict, repo: str, locale: str) -> str:
    text = TEXT[locale]
    parts = [f"<p><code>{html.escape(text['turn'].format(game=state['game']))}</code></p>", ""]
    parts.append(render_board(state["board"], repo, locale, 84))

    last = state.get("last_game")
    if last:
        summary = text["last"][last["result"]].format(game=last["game"], player=player_link(last["login"]))
        parts += ["", f"<p><sub>{summary}</sub></p>", render_board(last["board"], repo, locale, 34, last["line"], clickable=False)]

    parts += ["", f"<p>{text['score'].format(**state['stats'])}</p>"]

    players = sorted(
        state["players"].items(),
        key=lambda item: (-item[1]["wins"], -item[1]["draws"], -item[1]["moves"], item[0].lower()),
    )[:5]
    if players:
        header = "".join(f"<th>{label}</th>" for label in text["ranking"])
        rows = [
            f"  <tr><td>{position}</td><td>{player_link(login)}</td><td>{data['wins']}</td><td>{data['draws']}</td><td>{data['moves']}</td></tr>"
            for position, (login, data) in enumerate(players, start=1)
        ]
        parts += ["", "<table>", f"  <tr>{header}</tr>", *rows, "</table>"]
    else:
        parts += ["", f"<p><sub>{text['ranking_empty']}</sub></p>"]

    if state["recent"]:
        items = []
        for move in state["recent"]:
            item = text["recent_item"].format(player=player_link(move["login"]), cell=move["cell"] + 1)
            if move["bot_cell"] is not None:
                item += text["recent_bot"].format(cell=move["bot_cell"] + 1)
            items.append(item)
        parts += ["", f"<p><sub>{text['recent']}: " + " · ".join(items) + "</sub></p>"]

    return "\n".join(parts)


def update_readmes(state: dict, repo: str) -> None:
    for locale, path in READMES.items():
        readme = path.read_text(encoding="utf-8")
        readme = replace_section(readme, "GAME", render_game(state, repo, locale))
        path.write_text(readme, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Issue replies
# ---------------------------------------------------------------------------


def ascii_board(board: list[str]) -> str:
    cells = [piece.upper() if piece else str(index + 1) for index, piece in enumerate(board)]
    rows = [" " + " │ ".join(cells[row * 3 : row * 3 + 3]) for row in range(3)]
    return "\n───┼───┼───\n".join(rows)


def links(owner: str) -> str:
    pt = TEXT["pt"]["board_link"].format(owner=owner)
    en = TEXT["en"]["board_link"].format(owner=owner)
    return f"[Voltar ao tabuleiro]({pt}) · [Back to the board]({en})"


def comment_for(event: dict, owner: str) -> str:
    login = event["login"]
    if event["status"] == "invalid":
        return (
            "Não entendi essa jogada. Use os links das casas no tabuleiro do perfil.\n"
            "I couldn't read this move. Use the cell links on the profile board.\n\n" + links(owner)
        )
    if event["status"] == "occupied":
        cell = event["cell"] + 1
        return (
            f"A casa {cell} já foi ocupada por outra jogada. Escolha uma casa livre.\n"
            f"Cell {cell} was already taken by another move. Pick a free cell.\n\n" + links(owner)
        )

    cell = event["cell"] + 1
    bot = event["bot_cell"]
    if bot is None:
        pt = f"@{login} jogou na casa {cell}."
        en = f"@{login} played cell {cell}."
    else:
        pt = f"@{login} jogou na casa {cell} e o bot respondeu na casa {bot + 1}."
        en = f"@{login} played cell {cell} and the bot answered on cell {bot + 1}."

    result = event["result"]
    endings = {
        "x": ("Você venceu o bot! Seu nome entrou no ranking.", "You beat the bot! You're on the leaderboard now."),
        "o": ("O bot venceu essa. Uma nova partida já começou.", "The bot won this one. A new game has already started."),
        "draw": ("Deu empate. Uma nova partida já começou.", "It's a draw. A new game has already started."),
        None: ("A partida continua, qualquer visitante pode jogar a próxima.", "The game goes on, any visitor can make the next move."),
    }
    ending_pt, ending_en = endings[result]
    return f"{pt}\n{en}\n\n```\n{ascii_board(event['board'])}\n```\n\n{ending_pt}\n{ending_en}\n\n{links(owner)}"


# ---------------------------------------------------------------------------
# GitHub API and commands
# ---------------------------------------------------------------------------


def github_request(method: str, url: str, payload: dict | None = None) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "User-Agent": "kevennlaranjeira-tictactoe",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else None


def pending_issues(repo: str) -> list[dict]:
    query = urllib.parse.urlencode({"state": "open", "sort": "created", "direction": "asc", "per_page": 100})
    issues = github_request("GET", f"https://api.github.com/repos/{repo}/issues?{query}")
    return [
        issue
        for issue in issues
        if "pull_request" not in issue and issue["title"].strip().lower().startswith(TITLE_PREFIX)
    ]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return new_state()


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def command_play(repo: str, outbox: Path) -> None:
    owner = repo.split("/")[0]
    state = load_state()
    rng = random.Random()
    messages = []
    for issue in pending_issues(repo):
        login = issue["user"]["login"]
        match = TITLE_PATTERN.match(issue["title"])
        if match:
            event = apply_move(state, login, int(match.group(1)) - 1, rng, dt.datetime.now(BR_TZ))
        else:
            event = {"status": "invalid", "login": login}
        reason = "completed" if event["status"] == "played" else "not_planned"
        messages.append({"number": issue["number"], "body": comment_for(event, owner), "reason": reason})
        print(f"#{issue['number']} {login}: {event['status']}")

    save_state(state)
    update_readmes(state, repo)
    outbox.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")


def command_notify(repo: str, outbox: Path) -> None:
    if not outbox.exists():
        return
    for message in json.loads(outbox.read_text(encoding="utf-8")):
        base = f"https://api.github.com/repos/{repo}/issues/{message['number']}"
        github_request("POST", f"{base}/comments", {"body": message["body"]})
        github_request("PATCH", base, {"state": "closed", "state_reason": message["reason"]})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["play", "notify", "render"])
    parser.add_argument("--outbox", type=Path, default=ROOT / "game" / ".outbox.json")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "kevennlaranjeira/kevennlaranjeira"))
    args = parser.parse_args()

    if args.command == "play":
        command_play(args.repo, args.outbox)
    elif args.command == "notify":
        command_notify(args.repo, args.outbox)
    else:
        state = load_state()
        save_state(state)
        update_readmes(state, args.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
