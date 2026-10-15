
"""Generates generated/activity-graph.svg: an animated chart of the last year of GitHub contributions.
Runs inside GitHub Actions using the built-in GITHUB_TOKEN. No third-party servers needed."""
import json, os, sys, math, urllib.request
from datetime import datetime

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{firstDay contributionDays{date contributionCount}}}}}}"""

def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "activity-graph"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [(w["firstDay"], sum(d["contributionCount"] for d in w["contributionDays"])) for w in cal["weeks"]]
    return cal["totalContributions"], weeks

def render(login, total, weeks):
    W, H = 960, 320
    L, R, T, B = 56, 30, 92, 52
    cw, ch = W - L - R, H - T - B
    counts = [c for _, c in weeks]
    ymax = max(max(counts), 5)
    n = len(weeks)
    pts = [(L + cw * i / max(n - 1, 1), T + ch - ch * c / ymax) for i, (_, c) in enumerate(weeks)]
    # smooth line (Catmull-Rom -> cubic bezier)
    def smooth(p):
        d = f"M{p[0][0]:.1f} {p[0][1]:.1f}"
        for i in range(len(p) - 1):
            p0 = p[i - 1] if i > 0 else p[i]
            p1, p2 = p[i], p[i + 1]
            p3 = p[i + 2] if i + 2 < len(p) else p2
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            c1y = min(max(c1[1], T), T + ch); c2y = min(max(c2[1], T), T + ch)
            d += f"C{c1[0]:.1f} {c1y:.1f} {c2[0]:.1f} {c2y:.1f} {p2[0]:.1f} {p2[1]:.1f}"
        return d
    line = smooth(pts)
    area = line + f"L{pts[-1][0]:.1f} {T+ch}L{pts[0][0]:.1f} {T+ch}Z"
    # gridlines + month labels
    grid = ""
    for k in range(5):
        y = T + ch * k / 4
        val = round(ymax * (1 - k / 4))
        grid += f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#12304d" stroke-width="1"/>'
        grid += f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" class="ax">{val}</text>'
    months = ""
    last = None
    for i, (day, _) in enumerate(weeks):
        m = datetime.strptime(day, "%Y-%m-%d").strftime("%b")
        if m != last and i % 1 == 0:
            if last is not None or i == 0:
                months += f'<text x="{pts[i][0]:.1f}" y="{H-24}" text-anchor="middle" class="ax">{m}</text>'
            last = m
    peak_i = counts.index(max(counts))
    best = max(counts)
    avg = total / max(n, 1)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Contribution activity graph for {login}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#050B1A"/><stop offset="1" stop-color="#081A30"/></linearGradient>
<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00E5C0" stop-opacity=".45"/><stop offset="1" stop-color="#00E5C0" stop-opacity="0"/></linearGradient>
<linearGradient id="ln" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#38BDF8"/><stop offset=".5" stop-color="#00E5C0"/><stop offset="1" stop-color="#A78BFA"/></linearGradient>
<clipPath id="rc"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<clipPath id="reveal"><rect x="0" y="0" width="0" height="{H}"><animate attributeName="width" from="0" to="{W}" dur="2.4s" fill="freeze"/></rect></clipPath>
</defs>
<style>.t{{font:700 22px 'Segoe UI',Arial,sans-serif;fill:#CFFAF2}}.s{{font:500 13px 'Courier New',monospace;fill:#7aa7c7}}.ax{{font:500 11px 'Courier New',monospace;fill:#5f8fb0}}.k{{font:800 24px 'Segoe UI',Arial,sans-serif;fill:#00E5C0}}.kl{{font:500 11px 'Courier New',monospace;fill:#7aa7c7}}</style>
<g clip-path="url(#rc)">
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<text x="{L}" y="40" class="t">Contribution Activity</text>
<text x="{L}" y="62" class="s">last 12 months | weekly commits, PRs, issues | @{login}</text>
<text x="{W-R-230}" y="44" class="k">{total}</text><text x="{W-R-230}" y="62" class="kl">TOTAL</text>
<text x="{W-R-140}" y="44" class="k">{best}</text><text x="{W-R-140}" y="62" class="kl">BEST WEEK</text>
<text x="{W-R-50}" y="44" class="k" text-anchor="start">{avg:.1f}</text><text x="{W-R-50}" y="62" class="kl">AVG/WK</text>
{grid}{months}
<g clip-path="url(#reveal)">
<path d="{area}" fill="url(#ar)"/>
<path d="{line}" fill="none" stroke="url(#ln)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
</g>
<path id="trace" d="{line}" fill="none" stroke="none"/>
<circle r="5" fill="#fff" opacity="0"><set attributeName="opacity" to="1" begin="2.4s"/><animateMotion dur="9s" begin="2.4s" repeatCount="indefinite"><mpath href="#trace"/></animateMotion></circle>
<circle r="11" fill="#00E5C0" opacity="0"><set attributeName="opacity" to=".25" begin="2.4s"/><animateMotion dur="9s" begin="2.4s" repeatCount="indefinite"><mpath href="#trace"/></animateMotion><animate attributeName="r" values="7;13;7" dur="1.8s" repeatCount="indefinite"/></circle>
<circle cx="{pts[peak_i][0]:.1f}" cy="{pts[peak_i][1]:.1f}" r="4" fill="#F9A8D4"><animate attributeName="r" values="3;6;3" dur="2s" repeatCount="indefinite"/></circle>
</g>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="#1f4a6e"/>
</svg>'''
    return svg

def main():
    login = os.environ.get("USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER")
    token = os.environ.get("GITHUB_TOKEN")
    if not (login and token):
        sys.exit("USERNAME and GITHUB_TOKEN are required")
    total, weeks = fetch(login, token)
    os.makedirs("generated", exist_ok=True)
    with open("generated/activity-graph.svg", "w") as f:
        f.write(render(login, total, weeks))
    print(f"wrote generated/activity-graph.svg ({total} contributions, {len(weeks)} weeks)")

if __name__ == "__main__":
    main()
