#!/usr/bin/env python3
"""Update generated sections in the GitHub profile READMEs."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from svg_kit import (
    DISPLAY,
    MONO,
    PALETTE,
    card_background,
    card_defs,
    esc,
    fonts_for,
    svg_document,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".github" / "profile-config.json"
ASSETS = ROOT / "assets"
PROJECT_ASSETS = ASSETS / "projects"
READMES = {
    "pt": ROOT / "README.md",
    "en": ROOT / "README.en.md",
}
BR_TZ = ZoneInfo("America/Sao_Paulo")
LANG_COLORS = {
    "Java": "b07219",
    "TypeScript": "3178c6",
    "JavaScript": "f1e05a",
    "C": "555555",
    "C++": "f34b7d",
    "Python": "3572A5",
    "CSS": "563d7c",
    "HTML": "e34c26",
    "Dockerfile": "384d54",
    "Makefile": "427819",
    "Dart": "00B4AB",
    "SQL": "336791",
    "TeX": "3D6117",
}


def load_config() -> dict:
    with CONFIG.open("r", encoding="utf-8") as file:
        return json.load(file)


def github_fetch(url: str) -> tuple[object, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "kevennlaranjeira-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        if exc.code in {409, 422}:
            return [], {}
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {exc.code} for {url}: {message}") from exc


def github_get(url: str) -> object:
    return github_fetch(url)[0]


def fetch_repos(username: str) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "type": "owner",
            }
        )
        batch = github_get(f"https://api.github.com/users/{username}/repos?{query}")
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected GitHub API response while fetching repositories.")
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def repo_by_name(repos: list[dict]) -> dict[str, dict]:
    return {repo["name"].lower(): repo for repo in repos}


def select_projects(config: dict, repos: list[dict]) -> list[dict]:
    max_projects = int(config.get("maxProjects", 3))
    featured_names = [name.lower() for name in config.get("featuredRepos", [])]
    excluded = {name.lower() for name in config.get("excludeRepos", [])}
    mode = str(config.get("selectionMode", "auto")).lower()
    lookup = repo_by_name(repos)

    selected: list[dict] = []
    seen: set[str] = set()

    for name in featured_names:
        repo = lookup.get(name)
        if repo and not repo.get("fork"):
            selected.append(repo)
            seen.add(repo["name"].lower())

    if mode == "featured":
        return selected[:max_projects]

    sort_key = "created_at" if mode == "newest" else "updated_at"
    candidates = sorted(
        (
            repo
            for repo in repos
            if not repo.get("fork")
            and repo["name"].lower() not in excluded
            and repo["name"].lower() not in seen
        ),
        key=lambda repo: repo.get(sort_key) or "",
        reverse=True,
    )
    selected.extend(candidates)
    return selected[:max_projects]


def badge_url(label: str, message: str, color: str, logo: str | None = None) -> str:
    safe_label = urllib.parse.quote(label, safe="")
    safe_message = urllib.parse.quote(message.replace("-", "--"), safe="")
    logo_part = f"&logo={urllib.parse.quote(logo, safe='')}&logoColor=white" if logo else ""
    return f"https://img.shields.io/badge/{safe_label}-{safe_message}-{color}?style=for-the-badge&labelColor=161b22{logo_part}"


def parse_github_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(BR_TZ)


def format_date_br(value: dt.date) -> str:
    return value.strftime("%d/%m/%Y")


def format_datetime_br(value: dt.datetime | None, locale: str) -> str:
    if not value:
        return "Sem commits" if locale == "pt" else "No commits"
    return value.astimezone(BR_TZ).strftime("%d/%m/%Y %H:%M BRT")


def format_generated_date(value: dt.datetime) -> str:
    return format_date_br(value.astimezone(BR_TZ).date())


def format_int(value: int, locale: str) -> str:
    formatted = f"{value:,}"
    return formatted.replace(",", ".") if locale == "pt" else formatted


def format_bytes(value: int, locale: str) -> str:
    kilobytes = value / 1024
    if kilobytes < 1:
        return f"{format_int(value, locale)} B"
    text = f"{kilobytes:.1f}"
    return f"{text.replace('.', ',') if locale == 'pt' else text} KB"


def count_commits(username: str, repo: dict) -> int:
    branch = repo.get("default_branch")
    if not branch:
        return 0
    query = urllib.parse.urlencode({"sha": branch, "per_page": 1})
    url = f"https://api.github.com/repos/{username}/{repo['name']}/commits?{query}"
    data, headers = github_fetch(url)
    if not isinstance(data, list) or not data:
        return 0

    link = headers.get("Link", "")
    match = re.search(r"[?&]page=(\d+)>;\s*rel=\"last\"", link)
    if match:
        return int(match.group(1))
    return len(data)


def latest_commit(username: str, repo: dict) -> dict | None:
    branch = repo.get("default_branch")
    if not branch:
        return None
    query = urllib.parse.urlencode({"sha": branch, "per_page": 1})
    url = f"https://api.github.com/repos/{username}/{repo['name']}/commits?{query}"
    data = github_get(url)
    if not isinstance(data, list) or not data:
        return None
    item = data[0]
    raw_date = (
        item.get("commit", {}).get("committer", {}).get("date")
        or item.get("commit", {}).get("author", {}).get("date")
    )
    return {
        "repo": repo,
        "date": parse_github_datetime(raw_date),
        "message": item.get("commit", {}).get("message", "").splitlines()[0],
        "url": item.get("html_url"),
    }


def collect_repo_languages(repos: list[dict], excluded: set[str]) -> dict[str, dict[str, int]]:
    languages: dict[str, dict[str, int]] = {}
    for repo in repos:
        if repo.get("fork") or repo["name"].lower() in excluded:
            continue
        languages[repo["name"]] = {name: int(size) for name, size in github_get(repo["languages_url"]).items()}
    return languages


def collect_metrics(username: str, repos: list[dict], excluded: set[str]) -> dict:
    public_repos = [
        repo
        for repo in repos
        if not repo.get("fork") and repo["name"].lower() not in excluded
    ]
    if not public_repos:
        public_repos = [repo for repo in repos if not repo.get("fork")]
    repo_languages = collect_repo_languages(repos, excluded)
    language_totals: dict[str, int] = {}
    for languages in repo_languages.values():
        for language, bytes_count in languages.items():
            language_totals[language] = language_totals.get(language, 0) + bytes_count

    total_commits = 0
    latest: dict | None = None
    for repo in public_repos:
        total_commits += count_commits(username, repo)
        commit = latest_commit(username, repo)
        if commit and commit["date"] and (not latest or commit["date"] > latest["date"]):
            latest = commit

    last_updated_repo = max(public_repos, key=lambda repo: repo.get("pushed_at") or repo.get("updated_at") or "")
    return {
        "language_totals": language_totals,
        "repo_languages": repo_languages,
        "total_commits": total_commits,
        "latest_commit": latest,
        "last_updated_repo": last_updated_repo,
        "generated_at": dt.datetime.now(BR_TZ),
    }


def render_badges(username: str, public_repos: int, locale: str) -> str:
    today = format_date_br(dt.datetime.now(BR_TZ).date())
    if locale == "pt":
        views_label = "VISITAS"
        followers_label = "Seguidores"
        repos_label = "Repositórios públicos"
        updated_label = "Atualizado"
    else:
        views_label = "VIEWS"
        followers_label = "Followers"
        repos_label = "Public repositories"
        updated_label = "Updated"

    repo_badge = badge_url(repos_label, str(public_repos), "d29922", "github")
    updated_badge = badge_url(updated_label, today, "1f6feb", "githubactions")
    return "\n".join(
        [
            f"[![Profile views](https://komarev.com/ghpvc/?username={username}&color=3fb950&style=for-the-badge&label={urllib.parse.quote(views_label, safe='')})](https://github.com/{username})",
            f"[![GitHub followers](https://img.shields.io/github/followers/{username}?style=for-the-badge&logo=github&label={urllib.parse.quote(followers_label, safe='')}&color=2ea043&labelColor=161b22)](https://github.com/{username}?tab=followers)",
            f"[![GitHub repos]({repo_badge})](https://github.com/{username}?tab=repositories)",
            f"[![{updated_label}]({updated_badge})](https://github.com/{username}/{username}/actions)",
        ]
    )


def short_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def grow_animation(attribute: str, target: float, delay: float, duration: float = 0.9) -> str:
    """Animate an attribute from 0 to `target` after `delay`, keeping the final value as the base."""
    total = delay + duration
    return (
        f'<animate attributeName="{attribute}" values="0;0;{target:g}" keyTimes="0;{delay / total:.3f};1" '
        f'dur="{total:.2f}s" calcMode="spline" keySplines="0 0 1 1;0.2 0.8 0.2 1" />'
    )


def render_language_svg(metrics: dict, locale: str) -> str:
    language_totals = metrics["language_totals"]
    total_bytes = sum(language_totals.values())
    latest = metrics["latest_commit"]
    last_repo = metrics["last_updated_repo"]
    generated_at = metrics["generated_at"]
    top_languages = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)[:8]

    if locale == "pt":
        title = "Linguagens"
        subtitle = "bytes de código nos repositórios públicos, via GitHub API"
        commit_label = "commits públicos"
        latest_label = "último commit"
        repo_label = "repo mais recente"
        updated_label = "atualizado em"
        empty_latest = "sem commits públicos"
        footer = "// uma GitHub Action refaz este card de hora em hora"
    else:
        title = "Languages"
        subtitle = "bytes of code across public repositories, via GitHub API"
        commit_label = "public commits"
        latest_label = "latest commit"
        repo_label = "latest repo"
        updated_label = "updated at"
        empty_latest = "no public commits"
        footer = "// a GitHub Action rebuilds this card every hour"

    latest_text = format_datetime_br(latest["date"], locale) if latest else empty_latest

    metric_items = [
        (commit_label, format_int(metrics["total_commits"], locale), "accent"),
        (latest_label, short_text(latest_text, 30), "value"),
        (repo_label, short_text(last_repo["name"], 30), "value"),
        (updated_label, format_generated_date(generated_at), "value"),
    ]

    width, height = 1000, 400
    texts = [subtitle, footer]
    lang_rows: list[str] = []
    y = 124
    for index, (language, bytes_count) in enumerate(top_languages):
        percent = (bytes_count / total_bytes * 100) if total_bytes else 0
        color = "#" + LANG_COLORS.get(language, "6e7681")
        bar_width = max(6, round(percent * 3.1))
        percent_text = f"{percent:.1f}%"
        size_text = format_bytes(bytes_count, locale)
        texts += [language, percent_text, size_text]
        lang_rows.append(
            f"""
  <g transform="translate(40 {y})">
    <circle cx="6" cy="7" r="5" fill="{color}" />
    <text x="22" y="12" class="lang">{esc(language)}</text>
    <rect x="150" y="2" width="310" height="10" rx="5" fill="{PALETTE['grid']}" />
    <rect x="150" y="2" width="{bar_width}" height="10" rx="5" fill="{color}">{grow_animation('width', bar_width, 0.2 + index * 0.08)}</rect>
    <text x="530" y="12" class="percent" text-anchor="end">{percent_text}</text>
    <text x="548" y="12" class="muted">{esc(size_text)}</text>
  </g>"""
        )
        y += 29

    metric_rows: list[str] = []
    metric_y = 124
    for label, value, kind in metric_items:
        texts += [label, value]
        metric_rows.append(
            f"""
  <text x="680" y="{metric_y}" class="metric-label">{esc(label)}</text>
  <text x="680" y="{metric_y + 24}" class="metric-{kind}">{esc(value)}</text>"""
        )
        metric_y += 58

    defs = card_defs("l") + f"""
    <linearGradient id="l-accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{PALETTE['green']}" />
      <stop offset="1" stop-color="{PALETTE['blue']}" />
    </linearGradient>"""
    style = fonts_for({"mono": texts, "display": [title]}) + f"""
      .title {{ font: 700 24px {DISPLAY}; fill: {PALETTE['text']}; }}
      .subtitle {{ font: 400 12px {MONO}; fill: {PALETTE['muted']}; }}
      .lang {{ font: 700 13px {MONO}; fill: {PALETTE['text']}; }}
      .percent {{ font: 700 13px {MONO}; fill: {PALETTE['text']}; }}
      .muted {{ font: 400 11px {MONO}; fill: {PALETTE['muted']}; }}
      .metric-label {{ font: 400 11px {MONO}; fill: {PALETTE['muted']}; }}
      .metric-value {{ font: 700 15px {MONO}; fill: {PALETTE['text']}; }}
      .metric-accent {{ font: 700 22px {MONO}; fill: {PALETTE['amber']}; }}
      .footer {{ font: 400 11px {MONO}; fill: {PALETTE['faint']}; }}"""

    body = card_background("l", width, height) + f"""
  <text x="40" y="56" class="title">{esc(title)}</text>
  <text x="40" y="80" class="subtitle">{esc(subtitle)}</text>
  <rect x="40" y="94" width="580" height="2" rx="1" fill="url(#l-accent)">{grow_animation('width', 580, 0.05, 0.8)}</rect>
  <rect x="650" y="96" width="310" height="240" rx="12" fill="{PALETTE['panel']}" stroke="{PALETTE['line']}" />
  {''.join(lang_rows)}
  {''.join(metric_rows)}
  <text x="40" y="372" class="footer">{esc(footer)}</text>"""

    return svg_document(width, height, f"{title}: {subtitle}", defs, style, body)


def wrap_description(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = short_text(lines[-1] + " …", width)
    return lines


def render_project_svg(username: str, repo: dict, languages: dict[str, int], description: str, locale: str) -> str:
    width, height = 500, 214
    name = repo["name"]
    pushed = parse_github_datetime(repo.get("pushed_at"))
    updated = ("atualizado " if locale == "pt" else "updated ") + (format_date_br(pushed.date()) if pushed else "")
    owner = f"{username} /"
    lines = wrap_description(description, 48, 3)

    total = sum(languages.values())
    ordered = sorted(languages.items(), key=lambda item: item[1], reverse=True)
    bar_x, bar_width = 28, width - 56
    segments: list[str] = []
    cursor = 0.0
    for language, size in ordered:
        segment = bar_width * size / total if total else 0
        color = "#" + LANG_COLORS.get(language, "6e7681")
        segments.append(f'<rect x="{bar_x + cursor:.1f}" y="164" width="{segment + 0.5:.1f}" height="8" fill="{color}" />')
        cursor += segment

    legend: list[str] = []
    legend_x = 28
    texts = [owner, name, updated, *lines]
    for language, size in ordered[:3]:
        label = f"{language} {size / total * 100:.0f}%" if total else language
        color = "#" + LANG_COLORS.get(language, "6e7681")
        texts.append(label)
        legend.append(
            f'<circle cx="{legend_x + 4}" cy="192" r="4" fill="{color}" />'
            f'<text x="{legend_x + 14}" y="196" class="legend">{esc(label)}</text>'
        )
        legend_x += 14 + len(label) * 11 * 0.7 + 18

    stars = int(repo.get("stargazers_count") or 0)
    star_text = f"★ {stars}" if stars else ""
    if star_text:
        texts.append(star_text)

    defs = card_defs("p") + f"""
    <clipPath id="p-bar"><rect x="{bar_x}" y="164" width="{bar_width}" height="8" rx="4">{grow_animation('width', bar_width, 0.25, 1.1)}</rect></clipPath>"""
    style = fonts_for({"mono": texts, "display": [name]}) + f"""
      .owner {{ font: 400 11px {MONO}; fill: {PALETTE['muted']}; }}
      .name {{ font: 700 19px {DISPLAY}; fill: {PALETTE['text']}; }}
      .updated {{ font: 400 10px {MONO}; fill: {PALETTE['faint']}; }}
      .desc {{ font: 400 12px {MONO}; fill: #c9d1d9; }}
      .legend {{ font: 400 11px {MONO}; fill: {PALETTE['muted']}; }}
      .stars {{ font: 700 11px {MONO}; fill: {PALETTE['amber']}; }}"""

    description_text = "".join(
        f'\n  <text x="28" y="{104 + index * 20}" class="desc">{esc(line)}</text>' for index, line in enumerate(lines)
    )
    body = card_background("p", width, height, radius=14) + f"""
  <text x="28" y="38" class="owner">{esc(owner)}</text>
  <text x="{width - 28}" y="38" class="updated" text-anchor="end">{esc(updated)}</text>
  <text x="28" y="68" class="name">{esc(name)}</text>{description_text}
  <rect x="{bar_x}" y="164" width="{bar_width}" height="8" rx="4" fill="{PALETTE['grid']}" />
  <g clip-path="url(#p-bar)">{''.join(segments)}</g>
  {''.join(legend)}
  <text x="{width - 28}" y="196" class="stars" text-anchor="end">{esc(star_text)}</text>"""

    return svg_document(width, height, f"{name}: {description}", defs, style, body)


def project_asset(name: str, locale: str) -> str:
    return f"assets/projects/{name}{'' if locale == 'pt' else '-en'}.svg"


def render_language_metrics(username: str, metrics: dict, locale: str) -> str:
    asset = "assets/language-stats.svg" if locale == "pt" else "assets/language-stats-en.svg"
    alt = (
        "Métricas automáticas de linguagens e commits"
        if locale == "pt"
        else "Automatic language and commit metrics"
    )
    return "\n".join(
        [
            '<div align="center">',
            f'  <img src="{asset}" alt="{alt}" width="100%" />',
            "</div>",
        ]
    )


def render_projects(username: str, projects: list[dict], locale: str) -> str:
    cards = ['<div align="center">', ""]
    for repo in projects:
        name = repo["name"]
        cards.append(
            f'<a href="https://github.com/{username}/{name}"><img src="{project_asset(name, locale)}" width="48%" alt="{esc(name)}" /></a>'
        )
    cards.extend(["", "</div>"])
    return "\n".join(cards)


def replace_section(readme: str, name: str, content: str) -> str:
    pattern = re.compile(
        rf"<!-- PROFILE:{name}:START -->.*?<!-- PROFILE:{name}:END -->",
        re.DOTALL,
    )
    replacement = f"<!-- PROFILE:{name}:START -->\n{content}\n<!-- PROFILE:{name}:END -->"
    next_readme, count = pattern.subn(lambda _: replacement, readme)
    if count != 1:
        raise RuntimeError(f"Could not find exactly one PROFILE:{name} section in README.")
    return next_readme


def update_readme(path: Path, locale: str, username: str, user: dict, projects: list[dict], metrics: dict) -> None:
    readme = path.read_text(encoding="utf-8")
    readme = replace_section(readme, "BADGES", render_badges(username, int(user["public_repos"]), locale))
    readme = replace_section(readme, "LANG_STATS", render_language_metrics(username, metrics, locale))
    readme = replace_section(readme, "PROJECTS", render_projects(username, projects, locale))
    path.write_text(readme, encoding="utf-8", newline="\n")


def write_language_assets(metrics: dict) -> None:
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "language-stats.svg").write_text(
        render_language_svg(metrics, "pt"),
        encoding="utf-8",
        newline="\n",
    )
    (ASSETS / "language-stats-en.svg").write_text(
        render_language_svg(metrics, "en"),
        encoding="utf-8",
        newline="\n",
    )


def write_project_assets(config: dict, username: str, projects: list[dict], metrics: dict) -> None:
    PROJECT_ASSETS.mkdir(parents=True, exist_ok=True)
    descriptions = config.get("descriptions", {})
    expected: set[str] = set()
    for repo in projects:
        name = repo["name"]
        for locale in READMES:
            description = descriptions.get(name, {}).get(locale) or repo.get("description") or ""
            asset = ROOT / project_asset(name, locale)
            expected.add(asset.name)
            languages = metrics["repo_languages"].get(name, {})
            asset.write_text(
                render_project_svg(username, repo, languages, description, locale),
                encoding="utf-8",
                newline="\n",
            )
    for stale in PROJECT_ASSETS.glob("*.svg"):
        if stale.name not in expected:
            stale.unlink()


def main() -> int:
    config = load_config()
    username = config.get("username", "kevennlaranjeira")
    excluded = {name.lower() for name in config.get("excludeRepos", [])}
    user = github_get(f"https://api.github.com/users/{username}")
    repos = fetch_repos(username)
    projects = select_projects(config, repos)
    metrics = collect_metrics(username, repos, excluded)
    write_language_assets(metrics)
    write_project_assets(config, username, projects, metrics)

    for locale, path in READMES.items():
        update_readme(path, locale, username, user, projects, metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
