"""
generate.py — builds dark_mode.svg and light_mode.svg for chmosama's profile.
Fetches: repos, stars, commits (current year), PRs, issues, contributions,
         followers, following, account age.
Run via GitHub Actions (see .github/workflows/update.yml).
Requires: GH_TOKEN env var (classic PAT, read:user + repo scopes).
"""

import os
import datetime
import requests

TOKEN = os.environ["GH_TOKEN"]
USERNAME = "chmosama"
HEADERS = {
    "Authorization": f"bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ── GraphQL helpers ───────────────────────────────────────────────────────────

def gql(query: str, variables: dict = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post("https://api.github.com/graphql", json=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]


# ── Fetch stats ───────────────────────────────────────────────────────────────

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    following  { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
    }
    repositoriesContributedTo(
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
      includeUserRepositories: true
      privacy: PUBLIC
    ) { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar { totalContributions }
    }
    starredRepositories { totalCount }
    pullRequests(states: MERGED) { totalCount }
    issues(states: OPEN)  { totalCount }
  }
}
"""

now   = datetime.datetime.utcnow()
year  = now.year
from_ = f"{year}-01-01T00:00:00Z"
to_   = now.strftime("%Y-%m-%dT%H:%M:%SZ")

data  = gql(QUERY, {"login": USERNAME, "from": from_, "to": to_})["user"]

created    = datetime.datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
age_days   = (datetime.datetime.now(datetime.timezone.utc) - created).days
age_years  = age_days / 365.25

repos       = data["repositories"]["totalCount"]
followers   = data["followers"]["totalCount"]
following   = data["following"]["totalCount"]
cc          = data["contributionsCollection"]
commits_yr  = cc["totalCommitContributions"]
prs_merged  = data["pullRequests"]["totalCount"]
issues      = data["issues"]["totalCount"]
contribs    = cc["contributionCalendar"]["totalContributions"]
contrib_to  = data["repositoriesContributedTo"]["totalCount"]

print(f"repos={repos} followers={followers} commits_yr={commits_yr} "
      f"prs={prs_merged} issues={issues} contribs={contribs} age={age_years:.1f}y")


# ── SVG builder ───────────────────────────────────────────────────────────────

def make_svg(dark: bool) -> str:
    bg        = "#0d1117" if dark else "#ffffff"
    border    = "#30363d" if dark else "#d0d7de"
    accent    = "#00FF41" if dark else "#1a7f37"
    text_pri  = "#e6edf3" if dark else "#1f2328"
    text_sec  = "#8b949e" if dark else "#57606a"
    label_col = "#58a6ff" if dark else "#0969da"

    def row(y, icon, label, value, value_color=None):
        vc = value_color or accent
        return f"""
  <text x="52" y="{y}" font-size="13" fill="{text_sec}">{icon}  {label}</text>
  <text x="370" y="{y}" font-size="13" fill="{vc}" text-anchor="end" font-weight="600">{value}</text>
  <line x1="52" y1="{y+6}" x2="370" y2="{y+6}" stroke="{border}" stroke-width="0.4"/>"""

    rows = "".join([
        row(88,  "📁", "Public Repos",          f"{repos}"),
        row(116, "👥", "Followers",              f"{followers}"),
        row(144, "👣", "Following",              f"{following}"),
        row(172, "💻", f"Commits ({year})",      f"{commits_yr:,}"),
        row(200, "🔀", "PRs Merged (all time)",  f"{prs_merged:,}"),
        row(228, "🐛", "Open Issues",            f"{issues:,}"),
        row(256, "🟩", f"Contributions ({year})",f"{contribs:,}"),
        row(284, "🗂️", "Repos Contributed To",  f"{contrib_to:,}"),
        row(312, "🕰️", "GitHub Age",            f"{age_years:.1f} years", label_col),
    ])

    updated = now.strftime("%d %b %Y, %H:%M UTC")

    return f"""<svg width="420" height="360" viewBox="0 0 420 360"
     xmlns="http://www.w3.org/2000/svg" font-family="'Fira Code', 'Courier New', monospace">

  <!-- background -->
  <rect width="420" height="360" rx="12" fill="{bg}" stroke="{border}" stroke-width="1.2"/>

  <!-- header bar -->
  <rect x="0" y="0" width="420" height="52" rx="12" fill="{accent}" opacity="0.08"/>
  <rect x="0" y="40" width="420" height="12" fill="{accent}" opacity="0.08"/>

  <!-- title -->
  <text x="26" y="32" font-size="15" font-weight="700" fill="{accent}" letter-spacing="1">
    ▸ chmosama / stats.sh
  </text>
  <text x="340" y="32" font-size="10" fill="{text_sec}" text-anchor="end">
    {updated}
  </text>

  <!-- prompt line -->
  <text x="26" y="62" font-size="11" fill="{text_sec}">$ ./stats --user chmosama --year {year}</text>

  {rows}

  <!-- footer -->
  <text x="210" y="348" font-size="9" fill="{text_sec}" text-anchor="middle">
    auto-generated · github.com/chmosama
  </text>
</svg>"""


with open("dark_mode.svg",  "w") as f:
    f.write(make_svg(dark=True))

with open("light_mode.svg", "w") as f:
    f.write(make_svg(dark=False))

print("✓ dark_mode.svg and light_mode.svg written")