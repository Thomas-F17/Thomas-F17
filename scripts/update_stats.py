"""Builds the GitHub stats cards for the README from the GitHub API:
  assets/stats.svg   stars, commits, pull requests, issues, repos
  assets/langs.svg   top languages across your own (non-fork) repositories

Replaces the public github-readme-stats service, which is often paused or rate-limited.

Usage:  GITHUB_TOKEN=... python scripts/update_stats.py [username]
        (in GitHub Actions the token is provided automatically)
        python scripts/update_stats.py --demo   (made-up numbers, for offline previews)
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER = next((a for a in sys.argv[1:] if not a.startswith("--")), "Thomas-F17")
HIDE = {"php", "scss", "css", "html", "batchfile", "gherkin", "freemarker", "xslt", "tsql", "ruby"}
TOP_N = 6
NAVY, NAVY2, LINE, AMBER, INK, MUTED = "#0B1F3A", "#13294A", "#1C365A", "#F2A900", "#E6EDF5", "#7F98B3"
MONO = "IBM Plex Mono,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "IBM Plex Sans,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    pullRequests { totalCount }
    issues { totalCount }
    followers { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
  }
}"""

def gql(token, variables):
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": QUERY, "variables": variables}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                                          "User-Agent": "readme-stats-updater"})
    out = json.load(urllib.request.urlopen(req, timeout=30))
    if out.get("errors"):
        raise RuntimeError(out["errors"][0].get("message"))
    return out["data"]["user"]

def fetch(token):
    first, nodes, after = None, [], None
    while True:
        u = gql(token, {"login": USER, "after": after})
        first = first or u
        nodes += u["repositories"]["nodes"]
        page = u["repositories"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        after = page["endCursor"]
    langs = {}
    for n in nodes:
        for e in n["languages"]["edges"]:
            name = e["node"]["name"]
            if name.lower() in HIDE:
                continue
            size, color = langs.get(name, (0, e["node"]["color"]))
            langs[name] = (size + e["size"], color or "#7F98B3")
    c = first["contributionsCollection"]
    return {
        "stars": sum(n["stargazerCount"] for n in nodes),
        "commits": c["totalCommitContributions"] + c["restrictedContributionsCount"],
        "prs": first["pullRequests"]["totalCount"],
        "issues": first["issues"]["totalCount"],
        "repos": first["repositories"]["totalCount"],
        "contributed": first["repositoriesContributedTo"]["totalCount"],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1][0]),
    }

def demo():
    return {"stars": 12, "commits": 214, "prs": 9, "issues": 4, "repos": 11, "contributed": 3,
            "langs": [("Jupyter Notebook", (900000, "#DA5B0B")), ("Python", (420000, "#3572A5")), ("R", (90000, "#198CE7")),
                      ("MATLAB", (60000, "#e16737")), ("JavaScript", (30000, "#f1e05a")), ("VBA", (12000, "#867db1"))]}

def esc(t): return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def panel(W, H, title, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">'
            f'<rect width="{W}" height="{H}" rx="12" fill="{NAVY}"/>'
            f'<text x="24" y="36" fill="{AMBER}" style="font-family:{SANS};font-size:16px;font-weight:600">{title}</text>{body}</svg>')

def fade(i):
    return (f'opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{0.15 + i*0.12:.2f}s" dur="0.5s" fill="freeze"/>')

def stats_svg(s):
    rows = [("Total stars", s["stars"]), ("Commits (last 12 months)", s["commits"]), ("Pull requests", s["prs"]),
            ("Issues", s["issues"]), ("Public repositories", s["repos"]), ("Contributed to", s["contributed"])]
    W, H = 420, 210; body = []
    for i, (k, v) in enumerate(rows):
        y = 70 + i * 23
        body.append(f'<g {fade(i)}<text x="24" y="{y}" fill="{MUTED}" style="font-family:{MONO};font-size:13px">{k}</text>'
                    f'<text x="{W-24}" y="{y}" text-anchor="end" fill="{INK}" style="font-family:{MONO};font-size:13px;font-weight:600">{v:,}</text></g>')
    label = ", ".join(f"{k}: {v}" for k, v in rows)
    return panel(W, H, "GitHub stats", "".join(body), f"GitHub stats. {label}")

def langs_svg(s):
    W, H = 420, 210
    top = s["langs"][:TOP_N]; total = sum(v[0] for _, v in top) or 1
    x, segs, legend = 24.0, [], []
    bw = W - 48
    for i, (name, (size, color)) in enumerate(top):
        w = bw * size / total
        segs.append(f'<rect x="{x:.1f}" y="54" width="0" height="10" fill="{color}">'
                    f'<animate attributeName="width" from="0" to="{max(w-2,1):.1f}" begin="{0.2+i*0.12:.2f}s" dur="0.5s" fill="freeze"/></rect>')
        x += w
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 196, 96 + row * 30
        pct = 100 * size / total
        legend.append(f'<g {fade(i)}<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{color}"/>'
                      f'<text x="{lx+16}" y="{ly}" fill="{INK}" style="font-family:{MONO};font-size:12px">{esc(name)}</text>'
                      f'<text x="{lx+186}" y="{ly}" text-anchor="end" fill="{MUTED}" style="font-family:{MONO};font-size:12px">{pct:.1f}%</text></g>')
    clip = f'<clipPath id="bar"><rect x="24" y="54" width="{bw}" height="10" rx="5"/></clipPath>'
    body = f'<defs>{clip}</defs><g clip-path="url(#bar)">{"".join(segs)}</g>{"".join(legend)}'
    label = ", ".join(f"{n} {100*v[0]/total:.1f}%" for n, v in top)
    return panel(W, H, "Top languages", body, f"Top languages: {label}")

def main():
    if "--demo" in sys.argv:
        s = demo()
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            sys.exit("Set GITHUB_TOKEN (GitHub Actions does this automatically); leaving the existing cards unchanged.")
        try:
            s = fetch(token)
        except Exception as e:
            sys.exit(f"Couldn't read stats from the GitHub API ({e}); leaving the existing cards unchanged.")
    os.makedirs(f"{ROOT}/assets", exist_ok=True)
    open(f"{ROOT}/assets/stats.svg", "w", encoding="utf-8").write(stats_svg(s))
    open(f"{ROOT}/assets/langs.svg", "w", encoding="utf-8").write(langs_svg(s))
    print(f"Stats cards built: {s['repos']} repos, {len(s['langs'])} languages")

if __name__ == "__main__":
    main()
