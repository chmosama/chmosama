"""
generate.py — builds dark_mode.svg and light_mode.svg for chmosama's profile.
Alternating row stripes, tight 22px row height, no emojis, system fonts only.
Requires: GH_TOKEN env var (classic PAT, read:user + repo scopes).
"""

import os, datetime, requests

TOKEN    = os.environ["GH_TOKEN"]
USERNAME = "chmosama"
HEADERS  = {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}

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
      includeUserRepositories: true privacy: PUBLIC
    ) { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    pullRequests(states: MERGED) { totalCount }
    issues(states: OPEN) { totalCount }
  }
}
"""

now  = datetime.datetime.utcnow()
year = now.year
data = gql(QUERY, {
    "login": USERNAME,
    "from":  f"{year}-01-01T00:00:00Z",
    "to":    now.strftime("%Y-%m-%dT%H:%M:%SZ"),
})["user"]

created   = datetime.datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
age_years = (datetime.datetime.now(datetime.timezone.utc) - created).days / 365.25
cc        = data["contributionsCollection"]

ROWS = [
    ("repos",                     data["repositories"]["totalCount"]),
    ("followers",                 data["followers"]["totalCount"]),
    ("following",                 data["following"]["totalCount"]),
    (f"commits_{year}",           cc["totalCommitContributions"]),
    ("prs_merged",                data["pullRequests"]["totalCount"]),
    (f"contributions_{year}",     cc["contributionCalendar"]["totalContributions"]),
    ("repos_contributed_to",      data["repositoriesContributedTo"]["totalCount"]),
    ("open_issues",               data["issues"]["totalCount"]),
    ("account_age",               f"{age_years:.1f} years"),
]

updated = now.strftime("%d %b %Y, %H:%M UTC")

ROW_H    = 22   # height of each data row
ROW_PAD  = 15   # baseline offset within row
FIRST_Y  = 76   # y of first row rect
HEADER_H = 48
PROMPT_Y = 68
FOOTER_MARGIN = 28

def make_svg(dark: bool) -> str:
    bg      = "#0d1117" if dark else "#ffffff"
    stripe  = "#161b22" if dark else "#f6f8fa"
    border  = "#30363d" if dark else "#d0d7de"
    label   = "#8b949e" if dark else "#57606a"
    val_col = "#3fb950" if dark else "#1a7f37"
    accent  = "#58a6ff" if dark else "#0969da"
    hdr_bg  = "#161b22" if dark else "#f6f8fa"
    bar     = "#3fb950" if dark else "#1a7f37"
    pri     = "#e6edf3" if dark else "#1f2328"
    muted   = "#484f58" if dark else "#8c959f"
    div     = "#21262d" if dark else "#d0d7de"
    prompt  = "#3fb950" if dark else "#1a7f37"

    total_h = FIRST_Y + len(ROWS) * ROW_H + FOOTER_MARGIN + 18

    # alternating row stripes (even indices = stripe)
    stripes = ""
    for i in range(len(ROWS)):
        if i % 2 == 0:
            ry = FIRST_Y + i * ROW_H
            stripes += f'  <rect x="1" y="{ry}" width="478" height="{ROW_H}" fill="{stripe}"/>\n'

    # data rows
    rows_svg = ""
    for i, (key, val) in enumerate(ROWS):
        y  = FIRST_Y + i * ROW_H + ROW_PAD
        vc = accent if key == "account_age" else val_col
        fmtval = f"{val:,}" if isinstance(val, int) else val
        rows_svg += f'  <text x="22"  y="{y}" font-size="12" fill="{label}" font-family="\'Courier New\', monospace">{key}</text>\n'
        rows_svg += f'  <text x="458" y="{y}" font-size="12" fill="{vc}" font-weight="700" text-anchor="end" font-family="\'Courier New\', monospace">{fmtval}</text>\n'

    footer_line_y = FIRST_Y + len(ROWS) * ROW_H + 9
    footer_text_y = footer_line_y + 16

    return f"""<svg width="480" height="{total_h}" viewBox="0 0 480 {total_h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="480" height="{total_h}" rx="10" fill="{bg}" stroke="{border}" stroke-width="1"/>
  <rect width="480" height="{HEADER_H}" rx="10" fill="{hdr_bg}"/>
  <rect y="{HEADER_H - 10}" width="480" height="10" fill="{hdr_bg}"/>
  <rect x="18" y="14" width="3" height="20" rx="1.5" fill="{bar}"/>
  <text x="30" y="29" font-size="13" font-weight="600" fill="{pri}" font-family="Arial, sans-serif">chmosama</text>
  <text x="103" y="29" font-size="13" fill="{muted}" font-family="Arial, sans-serif">/</text>
  <text x="113" y="29" font-size="13" fill="{accent}" font-family="Arial, sans-serif">stats.sh</text>
  <text x="462" y="29" font-size="10" fill="{muted}" text-anchor="end" font-family="Arial, sans-serif">{updated}</text>
  <text x="22" y="{PROMPT_Y}" font-size="11" fill="{prompt}" font-family="'Courier New', monospace">$ ./stats --user chmosama --year {year}</text>
{stripes}{rows_svg}  <line x1="18" y1="{footer_line_y}" x2="462" y2="{footer_line_y}" stroke="{div}" stroke-width="0.8"/>
  <text x="22" y="{footer_text_y}" font-size="10" fill="{muted}" font-family="'Courier New', monospace">exit 0  # auto-updated every 6h via github actions</text>
</svg>"""

for fname, dark in [("dark_mode.svg", True), ("light_mode.svg", False)]:
    with open(fname, "w") as f:
        f.write(make_svg(dark))
    print(f"wrote {fname}")
