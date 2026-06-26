"""
generate.py — builds dark_mode.svg and light_mode.svg for chmosama's profile.
No emojis, no custom fonts — renders cleanly in GitHub's SVG viewer.
Requires: GH_TOKEN env var (classic PAT, read:user + repo scopes).
"""

import os
import datetime
import requests

TOKEN    = os.environ["GH_TOKEN"]
USERNAME = "chmosama"
HEADERS  = {
    "Authorization": f"bearer {TOKEN}",
    "Content-Type":  "application/json",
}

def gql(query, variables=None):
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, **({"variables": variables} if variables else {})},
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()["data"]

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    following  { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
    repositoriesContributedTo(
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
      includeUserRepositories: true
      privacy: PUBLIC
    ) { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions }
    }
    pullRequests(states: MERGED) { totalCount }
    issues(states: OPEN)         { totalCount }
  }
}
"""

now   = datetime.datetime.utcnow()
year  = now.year
data  = gql(QUERY, {
    "login": USERNAME,
    "from":  f"{year}-01-01T00:00:00Z",
    "to":    now.strftime("%Y-%m-%dT%H:%M:%SZ"),
})["user"]

created   = datetime.datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
age_years = (datetime.datetime.now(datetime.timezone.utc) - created).days / 365.25
cc        = data["contributionsCollection"]

stats = {
    "repos":               data["repositories"]["totalCount"],
    "followers":           data["followers"]["totalCount"],
    "following":           data["following"]["totalCount"],
    f"commits_{year}":     cc["totalCommitContributions"],
    "prs_merged":          data["pullRequests"]["totalCount"],
    f"contributions_{year}": cc["contributionCalendar"]["totalContributions"],
    "repos_contributed_to": data["repositoriesContributedTo"]["totalCount"],
    "open_issues":         data["issues"]["totalCount"],
    "account_age":         f"{age_years:.1f} years",
}

updated = now.strftime("%d %b %Y, %H:%M UTC")
print(stats)


def fmt(v):
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def make_svg(dark: bool) -> str:
    bg       = "#0d1117" if dark else "#ffffff"
    surface  = "#161b22" if dark else "#f6f8fa"
    border   = "#30363d" if dark else "#d0d7de"
    divider  = "#21262d" if dark else "#eaeef2"
    label    = "#8b949e" if dark else "#57606a"
    value    = "#3fb950" if dark else "#1a7f37"
    accent   = "#58a6ff" if dark else "#0969da"
    text_pri = "#e6edf3" if dark else "#1f2328"
    prompt   = "#3fb950" if dark else "#1a7f37"
    bar_acc  = "#00d26a" if dark else "#1a7f37"

    ROW_H   = 24
    START_Y = 100
    MONO    = "font-family=\"'Courier New', Courier, monospace\""
    SANS    = "font-family=\"'Segoe UI', Arial, sans-serif\""

    rows_svg = ""
    for i, (k, v) in enumerate(stats.items()):
        y   = START_Y + i * ROW_H
        val = fmt(v)
        # last stat (account_age) in accent colour
        vc  = accent if k == "account_age" else value
        rows_svg += f"""
  <text x="24"  y="{y}" font-size="12" fill="{label}" {MONO}>{k}</text>
  <text x="456" y="{y}" font-size="12" fill="{vc}" font-weight="600" text-anchor="end" {MONO}>{val}</text>"""

    h = START_Y + len(stats) * ROW_H + 40   # dynamic height

    return f"""<svg width="480" height="{h}" viewBox="0 0 480 {h}"
     xmlns="http://www.w3.org/2000/svg">

  <!-- card -->
  <rect width="480" height="{h}" rx="10" fill="{bg}" stroke="{border}" stroke-width="1"/>

  <!-- header -->
  <rect width="480" height="44" rx="10" fill="{surface}"/>
  <rect y="34" width="480" height="10" fill="{surface}"/>
  <rect x="16" y="13" width="3" height="18" rx="1.5" fill="{bar_acc}"/>
  <text x="28" y="27" font-size="13" font-weight="600" fill="{text_pri}" {SANS}>chmosama</text>
  <text x="98" y="27" font-size="13" fill="{label}" {SANS}>/</text>
  <text x="107" y="27" font-size="13" fill="{accent}" {SANS}>stats.sh</text>
  <text x="456" y="27" font-size="10" fill="{label}" text-anchor="end" {SANS}>{updated}</text>

  <!-- prompt -->
  <text x="24" y="66" font-size="11" fill="{prompt}" {MONO}>$ ./stats --user chmosama --year {year}</text>
  <line x1="24" y1="78" x2="456" y2="78" stroke="{divider}" stroke-width="1"/>

  {rows_svg}

  <!-- footer -->
  <line x1="24" y1="{h - 22}" x2="456" y2="{h - 22}" stroke="{divider}" stroke-width="1"/>
  <text x="24" y="{h - 8}" font-size="10" fill="{prompt}" {MONO}>exit 0  # auto-updated every 6h via github actions</text>
</svg>"""


with open("dark_mode.svg",  "w") as f:
    f.write(make_svg(dark=True))
with open("light_mode.svg", "w") as f:
    f.write(make_svg(dark=False))

print("dark_mode.svg and light_mode.svg written")
