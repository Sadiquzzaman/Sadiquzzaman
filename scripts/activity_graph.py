"""Draw a pixel-style contribution graph (last 31 days) as assets/activity.svg.

Runs daily from .github/workflows/activity-graph.yml. Needs GITHUB_TOKEN and USERNAME.
Pass --demo to render sample data without calling GitHub.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

DAYS = 31
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "activity.svg")

BG, FG, MUTED, GRID, ACCENT = "#0d1117", "#e6edf3", "#7d8590", "#21262d", "#e6edf3"


def fetch(username, token):
    to = dt.datetime.now(dt.timezone.utc)
    frm = to - dt.timedelta(days=DAYS - 1)
    query = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){
      contributionsCollection(from:$f,to:$t){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": query, "variables": {
        "u": username, "f": frm.strftime("%Y-%m-%dT00:00:00Z"), "t": to.strftime("%Y-%m-%dT%H:%M:%SZ")}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    return [(d["date"], d["contributionCount"]) for d in days][-DAYS:]


def render(days, username):
    W, H = 1200, 340
    L, R, T, B = 70, 30, 70, 60
    pw, ph = W - L - R, H - T - B
    counts = [c for _, c in days]
    top = max(4, max(counts))
    step = max(1, -(-top // 4))
    top = step * 4

    def x(i): return L + pw * i / (len(days) - 1)
    def y(v): return T + ph - ph * v / top

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" shape-rendering="crispEdges">',
         '<defs><pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse">'
         f'<rect width="2" height="2" fill="{FG}" opacity=".55"/><rect x="3" y="3" width="2" height="2" fill="{FG}" opacity=".25"/></pattern></defs>',
         f'<rect width="{W}" height="{H}" rx="12" fill="{BG}"/>',
         '<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
         f'<text x="{L}" y="38" font-size="18" font-weight="700" fill="{FG}">$ git log --since=30.days</text>',
         f'<text x="{W - R}" y="38" font-size="15" fill="{MUTED}" text-anchor="end">{sum(counts)} contributions</text>']
    for k in range(5):
        v = step * k
        yy = round(y(v))
        o.append(f'<line x1="{L}" y1="{yy}" x2="{W - R}" y2="{yy}" stroke="{GRID}" stroke-dasharray="4 4"/>')
        o.append(f'<text x="{L - 12}" y="{yy + 4}" font-size="12" fill="{MUTED}" text-anchor="end">{v}</text>')
    for i, (d, _) in enumerate(days):
        if i % 5 == 0 or i == len(days) - 1:
            label = dt.date.fromisoformat(d).strftime("%d %b").lower()
            o.append(f'<text x="{x(i):.0f}" y="{H - B + 26}" font-size="12" fill="{MUTED}" text-anchor="middle">{label}</text>')
    # stepped line, pixel style
    pts = []
    for i, c in enumerate(counts):
        pts.append((x(i), y(c)))
    path = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        mid = (x0 + x1) / 2
        path += f" H{mid:.1f} V{y1:.1f} H{x1:.1f}"
    area = path + f" V{T + ph} H{L} Z"
    o.append(f'<path d="{area}" fill="url(#dots)"/>')
    o.append(f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="3"/>')
    for (px, py), c in zip(pts, counts):
        if c:
            o.append(f'<rect x="{px - 4:.1f}" y="{py - 4:.1f}" width="8" height="8" fill="{BG}" stroke="{ACCENT}" stroke-width="2"/>')
    o.append(f'<text x="{L}" y="{H - 14}" font-size="11" fill="{MUTED}">@{username} · updated {dt.date.today().isoformat()}</text>')
    o.append('</g></svg>')
    return "\n".join(o)


if __name__ == "__main__":
    user = os.environ.get("USERNAME", "Sadiquzzaman")
    if "--demo" in sys.argv:
        import random
        random.seed(4)
        today = dt.date.today()
        days = [((today - dt.timedelta(days=DAYS - 1 - i)).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8, 4])) for i in range(DAYS)]
    else:
        days = fetch(user, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(render(days, user))
    print(f"wrote {OUT} ({sum(c for _, c in days)} contributions)")
