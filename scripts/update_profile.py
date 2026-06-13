#!/usr/bin/env python3
"""Update generated sections in the GitHub profile READMEs."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".github" / "profile-config.json"
READMES = {
    "pt": ROOT / "README.md",
    "en": ROOT / "README.en.md",
}
BR_TZ = ZoneInfo("America/Sao_Paulo")
LANG_COLORS = {
    "Java": "b07219",
    "TypeScript": "3178c6",
    "C": "555555",
    "C++": "f34b7d",
    "Python": "3572A5",
    "CSS": "563d7c",
    "HTML": "e34c26",
    "Dockerfile": "384d54",
    "Makefile": "427819",
    "Dart": "00B4AB",
    "SQL": "336791",
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
    return f"https://img.shields.io/badge/{safe_label}-{safe_message}-{color}?style=for-the-badge{logo_part}"


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
    suffix = "bytes"
    return f"{format_int(value, locale)} {suffix}"


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


def collect_language_totals(repos: list[dict], excluded: set[str]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repos:
        if repo.get("fork") or repo["name"].lower() in excluded:
            continue
        languages = github_get(repo["languages_url"])
        for language, bytes_count in languages.items():
            totals[language] = totals.get(language, 0) + int(bytes_count)
    return totals


def collect_metrics(username: str, repos: list[dict], excluded: set[str]) -> dict:
    public_repos = [
        repo
        for repo in repos
        if not repo.get("fork") and repo["name"].lower() not in excluded
    ]
    if not public_repos:
        public_repos = [repo for repo in repos if not repo.get("fork")]
    language_totals = collect_language_totals(repos, excluded)
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

    repo_badge = badge_url(repos_label, str(public_repos), "8957e5", "github")
    updated_badge = badge_url(updated_label, today, "0969da", "githubactions")
    return "\n".join(
        [
            f"[![Profile views](https://komarev.com/ghpvc/?username={username}&color=1f6feb&style=for-the-badge&label={urllib.parse.quote(views_label, safe='')})](https://github.com/{username})",
            f"[![GitHub followers](https://img.shields.io/github/followers/{username}?style=for-the-badge&logo=github&label={urllib.parse.quote(followers_label, safe='')}&color=2ea043)](https://github.com/{username}?tab=followers)",
            f"[![GitHub repos]({repo_badge})](https://github.com/{username}?tab=repositories)",
            f"[![{updated_label}]({updated_badge})](https://github.com/{username}/{username}/actions)",
        ]
    )


def language_bar(percent: float) -> str:
    filled = max(1, round(percent / 5)) if percent > 0 else 0
    return "█" * filled + "░" * (20 - filled)


def render_language_metrics(username: str, metrics: dict, locale: str) -> str:
    language_totals = metrics["language_totals"]
    total_bytes = sum(language_totals.values())
    latest = metrics["latest_commit"]
    last_repo = metrics["last_updated_repo"]
    generated_at = metrics["generated_at"]

    if locale == "pt":
        metric_header = ("Métrica", "Valor")
        lang_header = ("Linguagem", "Uso", "Bytes")
        total_commits_label = "Commits públicos nas branches padrão"
        latest_commit_label = "Último commit público"
        latest_repo_label = "Repositório atualizado mais recentemente"
        generated_label = "Seção atualizada em"
        empty_latest = "Sem commits públicos encontrados"
        note = "Métricas geradas automaticamente pela GitHub API; a Action roda de hora em hora e também pode ser executada manualmente."
    else:
        metric_header = ("Metric", "Value")
        lang_header = ("Language", "Usage", "Bytes")
        total_commits_label = "Public commits on default branches"
        latest_commit_label = "Latest public commit"
        latest_repo_label = "Most recently updated repository"
        generated_label = "Section updated at"
        empty_latest = "No public commits found"
        note = "Metrics generated automatically from the GitHub API; the Action runs hourly and can also be triggered manually."

    if latest:
        latest_text = f"[{latest['repo']['name']}]({latest['url']}) · {format_datetime_br(latest['date'], locale)}"
    else:
        latest_text = empty_latest

    metric_rows = [
        f"| {total_commits_label} | {format_int(metrics['total_commits'], locale)} |",
        f"| {latest_commit_label} | {latest_text} |",
        f"| {latest_repo_label} | [{last_repo['name']}]({last_repo['html_url']}) |",
        f"| {generated_label} | {format_generated_date(generated_at)} |",
    ]

    language_rows: list[str] = []
    for language, bytes_count in sorted(language_totals.items(), key=lambda item: item[1], reverse=True)[:10]:
        percent = (bytes_count / total_bytes * 100) if total_bytes else 0
        color = LANG_COLORS.get(language, "6e7681")
        label = urllib.parse.quote(language, safe="")
        message = urllib.parse.quote(f"{percent:.1f}%".replace("-", "--"), safe="")
        badge = f"https://img.shields.io/badge/{label}-{message}-{color}?style=flat-square"
        language_rows.append(
            f"| ![{language}]({badge}) | `{language_bar(percent)}` {percent:.1f}% | {format_bytes(bytes_count, locale)} |"
        )

    return "\n".join(
        [
            f"| {metric_header[0]} | {metric_header[1]} |",
            "|---|---|",
            *metric_rows,
            "",
            f"| {lang_header[0]} | {lang_header[1]} | {lang_header[2]} |",
            "|---|---:|---:|",
            *language_rows,
            "",
            f"> {note}",
        ]
    )


def render_projects(username: str, projects: list[dict]) -> str:
    cards = ['<div align="center">']
    for repo in projects:
        name = repo["name"]
        url_name = urllib.parse.quote(name, safe="")
        cards.extend(
            [
                "",
                f'<a href="https://github.com/{username}/{name}">',
                f'  <img height="125" src="https://github-readme-stats.vercel.app/api/pin/?username={username}&repo={url_name}&theme=github_dark&hide_border=true" alt="{name}" />',
                "</a>",
            ]
        )
    cards.extend(["", "</div>"])
    return "\n".join(cards)


def replace_section(readme: str, name: str, content: str) -> str:
    pattern = re.compile(
        rf"<!-- PROFILE:{name}:START -->.*?<!-- PROFILE:{name}:END -->",
        re.DOTALL,
    )
    replacement = f"<!-- PROFILE:{name}:START -->\n{content}\n<!-- PROFILE:{name}:END -->"
    next_readme, count = pattern.subn(replacement, readme)
    if count != 1:
        raise RuntimeError(f"Could not find exactly one PROFILE:{name} section in README.")
    return next_readme


def update_readme(path: Path, locale: str, username: str, user: dict, projects: list[dict], metrics: dict) -> None:
    readme = path.read_text(encoding="utf-8")
    readme = replace_section(readme, "BADGES", render_badges(username, int(user["public_repos"]), locale))
    readme = replace_section(readme, "LANG_STATS", render_language_metrics(username, metrics, locale))
    readme = replace_section(readme, "PROJECTS", render_projects(username, projects))
    path.write_text(readme, encoding="utf-8", newline="\n")


def main() -> int:
    config = load_config()
    username = config.get("username", "kevennlaranjeira")
    excluded = {name.lower() for name in config.get("excludeRepos", [])}
    user = github_get(f"https://api.github.com/users/{username}")
    repos = fetch_repos(username)
    projects = select_projects(config, repos)
    metrics = collect_metrics(username, repos, excluded)

    for locale, path in READMES.items():
        update_readme(path, locale, username, user, projects, metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
