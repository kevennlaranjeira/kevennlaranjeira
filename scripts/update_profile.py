#!/usr/bin/env python3
"""Update generated sections in the GitHub profile README."""

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


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONFIG = ROOT / ".github" / "profile-config.json"


def load_config() -> dict:
    with CONFIG.open("r", encoding="utf-8") as file:
        return json.load(file)


def github_get(url: str) -> object:
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
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {exc.code} for {url}: {message}") from exc


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
    safe_label = urllib.parse.quote(label)
    safe_message = urllib.parse.quote(message.replace("-", "--"))
    logo_part = f"&logo={urllib.parse.quote(logo)}&logoColor=white" if logo else ""
    return f"https://img.shields.io/badge/{safe_label}-{safe_message}-{color}?style=for-the-badge{logo_part}"


def render_badges(username: str, public_repos: int) -> str:
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    repo_badge = badge_url("Repositórios públicos", str(public_repos), "8957e5", "github")
    updated_badge = badge_url("Atualizado", today, "0969da", "githubactions")
    return "\n".join(
        [
            f"[![Profile views](https://komarev.com/ghpvc/?username={username}&color=1f6feb&style=for-the-badge&label=VISITAS)](https://github.com/{username})",
            f"[![GitHub followers](https://img.shields.io/github/followers/{username}?style=for-the-badge&logo=github&label=Seguidores&color=2ea043)](https://github.com/{username}?tab=followers)",
            f"[![GitHub repos]({repo_badge})](https://github.com/{username}?tab=repositories)",
            f"[![Atualizado]({updated_badge})](https://github.com/{username}/{username}/actions)",
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
        raise RuntimeError(f"Could not find exactly one PROFILE:{name} section in README.md.")
    return next_readme


def main() -> int:
    config = load_config()
    username = config.get("username", "kevennlaranjeira")
    user = github_get(f"https://api.github.com/users/{username}")
    repos = fetch_repos(username)
    projects = select_projects(config, repos)

    readme = README.read_text(encoding="utf-8")
    readme = replace_section(readme, "BADGES", render_badges(username, int(user["public_repos"])))
    readme = replace_section(readme, "PROJECTS", render_projects(username, projects))
    README.write_text(readme, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
