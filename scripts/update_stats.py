#!/usr/bin/env python3
"""Regenerate stats.svg from the live GitHub API.

The card in the profile README used to be a hand-written SVG with hard-coded
numbers, so it never moved. This script rebuilds the same card from live data
and is run by .github/workflows/stats.yml on a schedule.

Only the standard library is used so the workflow needs no pip install.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
USER_AGENT = "zhangzhanglaila-profile-stats"


def api_get(url: str, token: str | None) -> object:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", USER_AGENT)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_repos(user: str, token: str | None) -> list[dict]:
    repos: list[dict] = []
    for page in range(1, 11):
        url = f"{API}/users/{user}/repos?per_page=100&type=owner&sort=pushed&page={page}"
        batch = api_get(url, token)
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
    return repos


def summarize(user: str, token: str | None) -> dict[str, object]:
    repos = [repo for repo in fetch_repos(user, token) if not repo.get("private")]

    stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
    forks = sum(int(repo.get("forks_count") or 0) for repo in repos)

    # Main language = the primary language of the most owned repositories.
    # Counting repos (instead of summing bytes) keeps a project that ships a
    # large built frontend from being reported as "HTML", and costs no extra
    # API requests. Ties break on stars, then alphabetically, so the card is
    # deterministic between runs.
    repo_count: dict[str, int] = {}
    star_count: dict[str, int] = {}
    for repo in repos:
        if repo.get("fork") or not repo.get("language"):
            continue
        name = repo["language"]
        repo_count[name] = repo_count.get(name, 0) + 1
        star_count[name] = star_count.get(name, 0) + int(repo.get("stargazers_count") or 0)

    main_language = (
        min(repo_count, key=lambda name: (-repo_count[name], -star_count[name], name))
        if repo_count
        else "n/a"
    )

    return {
        "stars": stars,
        "repos": len(repos),
        "forks": forks,
        "language": main_language,
        # Date only: the workflow runs hourly, and a full timestamp would make
        # every run rewrite the file and commit a no-op change.
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def format_count(value: int) -> str:
    if value < 1000:
        return str(value)
    if value < 1_000_000:
        trimmed = f"{value / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{trimmed}k"
    return f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"


def value_font_size(text: str, box_width: int = 150) -> int:
    """Keep the monospace value text inside its panel."""
    # ui-monospace advance width is about 0.6em.
    size = min(32, int(box_width / (0.6 * max(len(text), 1))))
    return max(size, 12)


def escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render(stats: dict[str, object]) -> str:
    stars = format_count(int(stats["stars"]))
    repos = format_count(int(stats["repos"]))
    forks = format_count(int(stats["forks"]))
    language = escape(str(stats["language"]))
    updated = escape(str(stats["updated"]))

    language_size = value_font_size(str(stats["language"]), box_width=132)

    return f"""<svg width="760" height="220" viewBox="0 0 760 220" fill="none" xmlns="http://www.w3.org/2000/svg">
  <title>Live GitHub stats for zhangzhanglaila</title>
  <defs>
    <linearGradient id="panel" x1="0" y1="0" x2="760" y2="220" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0B1020"/>
      <stop offset="0.55" stop-color="#102A43"/>
      <stop offset="1" stop-color="#0B1020"/>
    </linearGradient>
    <linearGradient id="line" x1="56" y1="48" x2="700" y2="184" gradientUnits="userSpaceOnUse">
      <stop stop-color="#42E8C4"/>
      <stop offset="0.5" stop-color="#70A5FF"/>
      <stop offset="1" stop-color="#F85D7F"/>
    </linearGradient>
    <style>
      .title {{ fill: #F8FAFC; font: 700 24px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0; }}
      .label {{ fill: #9FB3C8; font: 600 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0; }}
      .value {{ fill: #F8FAFC; font: 800 32px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0; }}
      .note {{ fill: #DDE7F3; font: 500 15px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0; }}
      .live {{ fill: #42E8C4; font: 700 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 1.6; }}
    </style>
  </defs>
  <rect width="760" height="220" rx="24" fill="url(#panel)"/>
  <path d="M44 172 C134 112 212 188 304 124 C400 56 484 110 574 68 C628 42 670 42 716 58" stroke="url(#line)" stroke-width="2.5" opacity="0.8" fill="none"/>
  <circle cx="672" cy="44" r="5" fill="#42E8C4"/>
  <text class="live" x="686" y="48">LIVE</text>
  <text class="title" x="44" y="48">GitHub Snapshot</text>
  <text class="note" x="44" y="78">Synced from the GitHub API on {updated}</text>

  <g transform="translate(44 112)">
    <rect width="148" height="72" rx="14" fill="#111C2E" stroke="#243B53"/>
    <text class="label" x="18" y="26">TOTAL STARS</text>
    <text class="value" x="18" y="58">{stars}</text>
  </g>
  <g transform="translate(212 112)">
    <rect width="148" height="72" rx="14" fill="#111C2E" stroke="#243B53"/>
    <text class="label" x="18" y="26">PUBLIC REPOS</text>
    <text class="value" x="18" y="58">{repos}</text>
  </g>
  <g transform="translate(380 112)">
    <rect width="148" height="72" rx="14" fill="#111C2E" stroke="#243B53"/>
    <text class="label" x="18" y="26">TOTAL FORKS</text>
    <text class="value" x="18" y="58">{forks}</text>
  </g>
  <g transform="translate(548 112)">
    <rect width="168" height="72" rx="14" fill="#111C2E" stroke="#243B53"/>
    <text class="label" x="18" y="26">MAIN LANGUAGE</text>
    <text class="value" x="18" y="58" font-size="{language_size}">{language}</text>
  </g>
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the GitHub stats card.")
    parser.add_argument("--user", default=os.environ.get("GH_USER", "zhangzhanglaila"))
    parser.add_argument("--out", default="stats.svg")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN") or None)
    args = parser.parse_args()

    stats = summarize(args.user, args.token)
    svg = render(stats)

    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(svg)

    print(
        "stars={stars} repos={repos} forks={forks} language={language} -> {out}".format(
            out=args.out, **stats
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
