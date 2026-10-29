"""Fetches the VIX and S&P 500 from FRED and builds assets/vix.svg, the VIX snapshot shown in the README.

Implied one-standard-deviation moves:  daily = VIX / sqrt(252),  weekly = VIX / sqrt(52)  (in %)

Usage:  python scripts/update_vix.py          (live data, standard library only)
        python scripts/update_vix.py --demo   (synthetic data, for offline previews)
"""
import csv, datetime as dt, io, math, os, random, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
YEARS_JSON, DAYS_SVG = 1.2, 260
NAVY, NAVY2, LINE, STEEL, AMBER, INK, MUTED = "#0B1F3A", "#13294A", "#1C365A", "#4A79A8", "#F2A900", "#E6EDF5", "#7F98B3"
MONO = "IBM Plex Mono,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "IBM Plex Sans,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

def fred(series):
    req = urllib.request.Request(FRED.format(series), headers={"User-Agent": "Mozilla/5.0 (readme-vix-updater)"})
    text = urllib.request.urlopen(req, timeout=30).read().decode()
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) == 2 and row[1] not in (".", "") and row[0][:1].isdigit():
            out[row[0]] = float(row[1])
    return out

def demo():
    rnd = random.Random(5); d = dt.date.today() - dt.timedelta(days=int(365 * YEARS_JSON))
    v, s, vix, spx = 17.0, 4200.0, {}, {}
    while d <= dt.date.today():
        if d.weekday() < 5:
            shock = rnd.gauss(0, 1)
            v = max(9.5, v + 0.06 * (17 - v) + 1.1 * shock + (14 if rnd.random() < 0.004 else 0))
            s *= math.exp(0.0003 - 0.004 * shock + rnd.gauss(0, 0.004))
            vix[d.isoformat()], spx[d.isoformat()] = round(v, 2), round(s, 2)
        d += dt.timedelta(days=1)
    return vix, spx

def build_rows(vix, spx):
    start = (dt.date.today() - dt.timedelta(days=int(365.25 * YEARS_JSON))).isoformat()
    rows, last_spx = [], None
    for d in sorted(set(vix) | set(spx)):
        last_spx = spx.get(d, last_spx)
        if d < start or d not in vix or last_spx is None:
            continue
        v = vix[d]; dp, wp = v / math.sqrt(252), v / math.sqrt(52)
        rows.append({"date": d, "vix": v, "spx": last_spx, "daily_pct": round(dp, 3), "weekly_pct": round(wp, 3),
                     "daily_pts": round(last_spx * dp / 100, 1), "weekly_pts": round(last_spx * wp / 100, 1)})
    return rows

def svg(rows):
    W, H = 880, 345
    L, R, T, B = 56, 820, 144, 292
    data = rows[-DAYS_SVG:]; last = data[-1]
    lo = math.floor(min(r["vix"] for r in data) / 5) * 5; hi = math.ceil(max(r["vix"] for r in data) / 5) * 5
    X = lambda i: L + (R - L) * i / (len(data) - 1)
    Y = lambda v: B - (B - T) * (v - lo) / (hi - lo)
    pts = " ".join(f"{X(i):.1f},{Y(r['vix']):.1f}" for i, r in enumerate(data))
    g = []
    step = 5 if hi - lo <= 30 else 10
    for v in range(lo, hi + 1, step):
        y = Y(v)
        g.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="{LINE}"/>'
                 f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" fill="{MUTED}">{v}</text>'
                 f'<text x="{R+10}" y="{y+4:.1f}" fill="{MUTED}">{v/math.sqrt(252):.1f}%</text>')
    seen = set()
    for i, r in enumerate(data):  # month labels
        m = r["date"][:7]
        if m not in seen and i > 5 and i < len(data) - 8:
            seen.add(m); mon = dt.date.fromisoformat(r["date"]).strftime("%b")
            g.append(f'<text x="{X(i):.1f}" y="{B+20}" text-anchor="middle" fill="{MUTED}">{mon}</text>')
    asof = dt.date.fromisoformat(last["date"]).strftime("%d %b %Y")
    def stat(x, label, big, small):
        return (f'<text x="{x}" y="50" fill="{MUTED}" style="font-family:{MONO};font-size:12px">{label}</text>'
                f'<text x="{x}" y="84" fill="{INK}" style="font-family:{SANS};font-size:28px;font-weight:600">{big}</text>'
                f'<text x="{x}" y="104" fill="{MUTED}" style="font-family:{MONO};font-size:12px">{small}</text>')
    stats = (stat(L, "VIX", f'{last["vix"]:.2f}', f"as of {asof}")
             + stat(L + 230, "Implied daily move", f'±{last["daily_pct"]:.2f}%', f'±{last["daily_pts"]:.0f} pts on the S&amp;P 500')
             + stat(L + 490, "Implied weekly move", f'±{last["weekly_pct"]:.2f}%', f'±{last["weekly_pts"]:.0f} pts on the S&amp;P 500'))
    lx, ly = X(len(data) - 1), Y(last["vix"])
    line = (f'<polyline points="{pts}" fill="none" stroke="{AMBER}" stroke-width="2" stroke-linejoin="round" '
            f'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'
            f'<animate attributeName="stroke-dashoffset" from="1" to="0" begin="0.3s" dur="2.2s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" keySplines="0.35 0 0.2 1"/></polyline>'
            f'<g opacity="0"><set attributeName="opacity" to="1" begin="2.5s" fill="freeze"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.5" fill="{AMBER}"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.5" fill="none" stroke="{AMBER}" stroke-width="1.5">'
            f'<animate attributeName="r" values="3.5;11" dur="2s" begin="2.5s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.8;0" dur="2s" begin="2.5s" repeatCount="indefinite"/></circle></g>')
    axes = (f'<text x="{L-10}" y="{T-12}" text-anchor="end" fill="{MUTED}">VIX</text>'
            f'<text x="{R+10}" y="{T-12}" fill="{MUTED}">Daily</text>')
    foot = (f'<text x="{L}" y="{H-14}" fill="{MUTED}" style="font-family:{MONO};font-size:10.5px">'
            f'Last 12 months. One-standard-deviation moves: VIX/√252 daily, VIX/√52 weekly. Source: FRED, updated each weekday.</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">'
            f'<title id="t">VIX {last["vix"]:.2f} as of {asof}: implied S&amp;P 500 move ±{last["daily_pct"]:.2f}% daily, ±{last["weekly_pct"]:.2f}% weekly</title>'
            f'<rect width="{W}" height="{H}" rx="12" fill="{NAVY}"/>{stats}'
            f'<g style="font-family:{MONO};font-size:11px">{"".join(g)}{axes}</g>{line}{foot}</svg>')

def main():
    if "--demo" in sys.argv:
        vix, spx = demo()
    else:
        try:
            vix, spx = fred("VIXCLS"), fred("SP500")
        except Exception as e:
            sys.exit(f"Couldn't download data from FRED ({e}); leaving the existing files unchanged.")
    rows = build_rows(vix, spx)
    if len(rows) < 30:
        sys.exit("Not enough data returned from FRED; leaving the existing files unchanged.")
    os.makedirs(f"{ROOT}/assets", exist_ok=True)
    open(f"{ROOT}/assets/vix.svg", "w", encoding="utf-8").write(svg(rows))
    print(f'{len(rows)} rows, latest {rows[-1]["date"]}: VIX {rows[-1]["vix"]}')

if __name__ == "__main__":
    main()
