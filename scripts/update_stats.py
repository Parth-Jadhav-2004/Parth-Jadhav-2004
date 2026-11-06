"""Generate public GitHub profile cards without a third-party image service."""

import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "Parth-Jadhav-2004"


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
      contributionsCollection {{
        totalPullRequestContributions
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
    days = [day for week in collection["contributionCalendar"]["weeks"]
            for day in week["contributionDays"]]
    today = datetime.now(timezone.utc).date()
    contributions = {day["date"]: day["contributionCount"] for day in days}
    current_day = today
    if not contributions.get(current_day.isoformat(), 0):
        current_day -= timedelta(days=1)
    streak = 0
    while contributions.get(current_day.isoformat(), 0):
        streak += 1
        current_day -= timedelta(days=1)
    return {
        "metrics": [
            ("Contributions", collection["contributionCalendar"]["totalContributions"]),
            ("Current streak / days*", streak),
            ("Pull requests", collection["totalPullRequestContributions"]),
            ("Public repositories", repositories["totalCount"]),
            ("Public repo stars", stars),
            ("Followers", user["followers"]["totalCount"]),
        ],
        "weeks": [sum(day["contributionCount"] for day in week["contributionDays"])
                  for week in collection["contributionCalendar"]["weeks"][-12:]],
        "updated": datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC"),
    }


def render_card(stats, dark):
    background, foreground, muted, border, accent = (
        ("#0d1117", "#f0f6fc", "#8b949e", "#30363d", "#a5d6ff") if dark else
        ("#ffffff", "#24292f", "#57606a", "#d0d7de", "#0969da")
    )
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="370" viewBox="0 0 720 370" role="img" aria-labelledby="title description">',
        '<title id="title">Parth Jadhav · GitHub activity</title>',
        f'<desc id="description">{escape(", ".join(f"{label}: {value}" for label, value in stats["metrics"]))}. Updated {escape(stats["updated"])}. Contributions, pull requests and streak cover the past year; streak uses UTC days.</desc>',
        f'<rect x="0.5" y="0.5" width="719" height="369" rx="16" fill="{background}" stroke="{border}"/>',
        f'<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" fill="{foreground}">',
        '<text x="28" y="37" font-size="19" font-weight="600">GitHub activity</text>',
        f'<text x="28" y="60" font-size="12" fill="{muted}">A year of building, one contribution at a time.</text>',
    ]
    for index, (label, value) in enumerate(stats["metrics"]):
        horizontal = 28 + index % 3 * 232
        vertical = 108 + index // 3 * 75
        elements.extend([
            f'<text x="{horizontal}" y="{vertical}" font-size="29" font-weight="600">{value:,}</text>',
            f'<text x="{horizontal}" y="{vertical + 23}" font-size="12" fill="{muted}">{escape(label)}</text>',
        ])
    elements.append(f'<path d="M28 225H692" stroke="{border}"/>')
    elements.append(f'<text x="28" y="249" font-size="12" fill="{muted}">Contributions · last 12 weeks</text>')
    peak = max(max(stats["weeks"]), 1)
    for index, count in enumerate(stats["weeks"]):
        height = max(round(count / peak * 43), 2)
        elements.append(f'<rect x="{28 + index * 56}" y="{302 - height}" width="48" height="{height}" rx="3" fill="{accent}"><title>{count} contributions</title></rect>')
    elements.extend([
        f'<text x="28" y="329" font-size="11" fill="{muted}">*Past-year window · UTC days · today may still be in progress</text>',
        f'<text x="28" y="351" font-size="11" fill="{muted}">Updated {escape(stats["updated"])} · refresh requested every 6 hours</text>',
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
        (ROOT / "assets" / f"github-stats-{theme}.svg").write_text(card)
    readme_path.write_text(updated_readme)


if __name__ == "__main__":
    main()
