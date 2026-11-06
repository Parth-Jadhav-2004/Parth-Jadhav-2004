"""Generate public GitHub profile cards without a third-party image service."""

import hashlib
import json
import math
import re
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "Parth-Jadhav-2004"
FONT = '-apple-system, "Segoe UI", Helvetica, Arial, sans-serif'


def esc(value):
    return escape(str(value), {'"': "&quot;", "'": "&#39;"})


def compute_streaks(days, today):
    contributions = {day["date"]: day["count"] for day in days
                     if day["date"] <= today.isoformat()}
    longest = 0
    run = 0
    previous_day = None
    for day, count in sorted(contributions.items()):
        current_day = date.fromisoformat(day)
        if previous_day is not None and current_day != previous_day + timedelta(days=1):
            run = 0
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
        previous_day = current_day
    current_day = today
    if not contributions.get(current_day.isoformat(), 0):
        current_day -= timedelta(days=1)
    current = 0
    while contributions.get(current_day.isoformat(), 0):
        current += 1
        current_day -= timedelta(days=1)
    return current, longest


def query_github(query):
    response = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        check=True, capture_output=True, text=True,
    )
    payload = json.loads(response.stdout)
    if payload.get("errors"):
        raise RuntimeError("GitHub returned GraphQL errors; existing cards preserved")
    return payload["data"]["user"]


def collect_stats():
    user = query_github(f'''query {{ user(login: "{USERNAME}") {{
      followers {{ totalCount }}
      pullRequests {{ totalCount }}
      contributionsCollection {{
        contributionCalendar {{ totalContributions weeks {{
          contributionDays {{ date contributionCount }}
        }} }}
      }}
    }} }}''')
    stars = 0
    cursor = None
    while True:
        after = f', after: {json.dumps(cursor)}' if cursor else ""
        repositories = query_github(f'''query {{ user(login: "{USERNAME}") {{
          repositories(first: 100, privacy: PUBLIC, ownerAffiliations: OWNER{after}) {{
            totalCount nodes {{ stargazerCount }}
            pageInfo {{ hasNextPage endCursor }}
          }}
        }} }}''')["repositories"]
        stars += sum(repository["stargazerCount"] for repository in repositories["nodes"])
        if not repositories["pageInfo"]["hasNextPage"]:
            break
        cursor = repositories["pageInfo"]["endCursor"]
        if not cursor:
            raise RuntimeError("Missing pagination cursor; existing cards preserved")
    collection = user["contributionsCollection"]
    days = [{"date": day["date"], "count": day["contributionCount"]}
            for week in collection["contributionCalendar"]["weeks"]
            for day in week["contributionDays"]]
    today = datetime.now(timezone.utc).date()
    current, longest = compute_streaks(days, today)
    return {
        "login": USERNAME,
        "current": current,
        "longest": longest,
        "total": collection["contributionCalendar"]["totalContributions"],
        "prs": user["pullRequests"]["totalCount"],
        "repos": repositories["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "updated": datetime.now(timezone.utc).strftime("%d %b %Y %H:%M"),
    }


def render_card(stats, dark):
    background, foreground, muted, border, accent, flame = (
        ("#0d1117", "#f0f6fc", "#8b949e", "#30363d", "#58a6ff", "#ff7b54") if dark else
        ("#ffffff", "#1f2328", "#656d76", "#d0d7de", "#0969da", "#fb8500")
    )
    circumference = 2 * math.pi * 44
    progress = min(stats["current"] / max(stats["longest"], 1), 1)
    current_text = format(stats["current"], ",")
    current_size = 36 if len(current_text) <= 3 else 24
    description = (
        f'GitHub activity for {stats["login"]}: {stats["current"]:,} day current streak, '
        f'{stats["longest"]:,} day longest streak, {stats["total"]:,} contributions in the past year; '
        f'{stats["prs"]:,} pull requests, {stats["repos"]:,} public repositories, '
        f'{stats["stars"]:,} stars, {stats["followers"]:,} followers. '
        f'Updated {stats["updated"]} UTC. Streaks use UTC days within the past-year calendar; '
        'today may still be in progress.'
    )
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="344" viewBox="0 0 840 344" role="img" aria-labelledby="title description" font-family="{esc(FONT)}">',
        '<title id="title">Parth Jadhav · GitHub activity</title>',
        f'<desc id="description">{esc(description)}</desc>',
        f'<rect x="0.5" y="0.5" width="839" height="343" rx="16" fill="{background}" stroke="{border}"/>',
        f'<g fill="{foreground}">',
        '<text x="32" y="48" font-size="20" font-weight="600">GitHub activity</text>',
        f'<text x="32" y="68" font-size="13" fill="{muted}">@{esc(stats["login"])} · past year</text>',
        '<g transform="translate(148, 150)">',
        f'<circle r="44" fill="none" stroke="{border}" stroke-width="8"/>',
        f'<circle r="44" fill="none" stroke="{accent}" stroke-width="8" stroke-linecap="round" stroke-dasharray="{circumference * progress:.2f} {circumference:.2f}" transform="rotate(-90)" opacity="{1 if progress else 0}"/>',
        f'<path d="M0 -30 C4 -23 9 -20 9 -15 A9 9 0 0 1 -9 -15 C-9 -20 -5 -23 0 -30Z" fill="{flame}"/>',
        f'<text y="24" text-anchor="middle" font-size="{current_size}" font-weight="700">{esc(current_text)}</text>',
        '</g>',
        f'<text x="148" y="222" text-anchor="middle" font-size="12" fill="{muted}">Current streak · days</text>',
        f'<path d="M280 100V210M570 100V210" stroke="{border}"/>',
    ]

    def stat(horizontal, vertical, number, label, size=22):
        elements.extend([
            f'<text x="{horizontal}" y="{vertical}" font-size="{size}" font-weight="700">{esc(format(number, ","))}</text>',
            f'<text x="{horizontal}" y="{vertical + (30 if size == 44 else 20)}" font-size="12" fill="{muted}">{esc(label)}</text>',
        ])

    stat(320, 150, stats["longest"], 'Longest streak · days (past year)', 44)
    stat(610, 150, stats["total"], 'Contributions · past year', 44)
    for index, (key, label) in enumerate((
        ("prs", "Pull requests"), ("repos", "Public repos"),
        ("stars", "Stars"), ("followers", "Followers"),
    )):
        stat(32 + index * 200, 262, stats[key], label)
    elements.append(f'<path d="M32 296H808" stroke="{border}"/>')
    elements.extend([
        f'<text x="32" y="325" font-size="11" fill="{muted}">Updated {esc(stats["updated"])} UTC</text>',
        '</g></svg>\n',
    ])
    return "\n".join(elements)


def main():
    stats = collect_stats()
    cards = {theme: render_card(stats, theme == "dark") for theme in ("dark", "light")}
    revision = hashlib.sha256("".join(cards.values()).encode()).hexdigest()[:12]
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    updated_readme, replacements = re.subn(
        r"assets/github-stats-(dark|light)\.svg(?:\?v=[a-f0-9]+)?",
        lambda match: f"assets/github-stats-{match[1]}.svg?v={revision}", readme,
    )
    if replacements != 2:
        raise RuntimeError("Expected two README card references; no files updated")
    for theme, card in cards.items():
        path = ROOT / "assets" / f"github-stats-{theme}.svg"
        if not path.exists() or path.read_text() != card:
            path.write_text(card)
    if readme != updated_readme:
        readme_path.write_text(updated_readme)


if __name__ == "__main__":
    main()
