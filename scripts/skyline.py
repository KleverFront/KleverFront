"""Render the contribution calendar as an animated rainy isometric city.

Usage: python3 scripts/skyline.py <user> <output.svg>

Reads the public contributions page, which includes private contributions when
the profile setting allows it (the Actions GITHUB_TOKEN cannot see those via GraphQL).
"""
import datetime
import os
import random
import re
import sys
import urllib.request


def fetch(user):
    url = f"https://github.com/users/{user}/contributions"
    html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "skyline"}), timeout=30).read().decode()
    dates = dict(re.findall(r'data-date="([\d-]+)" id="(contribution-day-component-[\d-]+)"', html))
    dates = {cid: d for d, cid in dates.items()}
    counts = {}
    for cid, text in re.findall(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)</tool-tip>', html):
        m = re.match(r"(\d+) contribution", text)
        counts[dates[cid]] = int(m.group(1)) if m else 0
    if not counts:
        sys.exit(f"No contribution data found at {url}")
    days = sorted(datetime.date.fromisoformat(d) for d in counts)
    start = days[0] - datetime.timedelta(days=(days[0].weekday() + 1) % 7)  # Sunday-based weeks
    weeks = [[0] * 7 for _ in range((days[-1] - start).days // 7 + 1)]
    for d in days:
        weeks[(d - start).days // 7][(d.weekday() + 1) % 7] = counts[d.isoformat()]
    return weeks

SX, SY, MAXH = 9, 4.5, 70


def lvl(c, mx):
    return 0 if c == 0 else min(4, 1 + int(3 * c / mx + .5))


def city(weeks, t, seed=1):
    rnd = random.Random(seed)
    W = len(weeks)
    mx = max(max(w) for w in weeks) or 1
    ox, oy = 7 * SX + 40, MAXH + 90
    w = int(ox + W * SX + 40)
    h = int(oy + (W + 7) * SY + 30)
    out = []
    defs = [f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">' +
            "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in t["sky"]) + "</linearGradient>",
            '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>']
    out.append(f'<rect width="100%" height="100%" fill="url(#sky)"/>')
    if t.get("stars"):
        out += [f'<circle class="s" cx="{rnd.uniform(0, w):.0f}" cy="{rnd.uniform(0, h * .45):.0f}" r="{rnd.uniform(.5, 1.2):.1f}" '
                f'fill="#fff" style="animation-delay:{rnd.uniform(0, 3):.1f}s"/>' for _ in range(70)]
    if t.get("moon"):
        mx_, my_, mc = t["moon"]
        out.append(f'<circle cx="{mx_}" cy="{my_}" r="16" fill="{mc}" filter="url(#glow)" opacity=".95"/>')
    if t.get("sun"):
        out.append(f'<circle cx="{w * .72:.0f}" cy="{oy * .7:.0f}" r="34" fill="{t["sun"]}" opacity=".9" filter="url(#glow)"/>')
    tiles = []
    for x in range(W):
        for y in range(7):
            c = weeks[x][y]
            lv = lvl(c, mx)
            hg = 3 + (MAXH * c / mx if c else 0)
            bx, by = ox + (x - y) * SX, oy + (x + y) * SY
            top = f"{bx},{by - hg} {bx + SX},{by - hg + SY} {bx},{by - hg + 2 * SY} {bx - SX},{by - hg + SY}"
            left = f"{bx - SX},{by - hg + SY} {bx},{by - hg + 2 * SY} {bx},{by + 2 * SY} {bx - SX},{by + SY}"
            right = f"{bx + SX},{by - hg + SY} {bx},{by - hg + 2 * SY} {bx},{by + 2 * SY} {bx + SX},{by + SY}"
            ft, fl, fr = t["levels"][lv]
            stroke = f' stroke="{t["edge"]}" stroke-width=".6"' if t.get("edge") and lv else ""
            fo = ' fill-opacity="0"' if t.get("wire") and lv else ""
            g = (f'<g style="animation:r .9s {(x + y) * .025:.2f}s both cubic-bezier(.2,.9,.3,1.25)">'
                 f'<polygon points="{left}" fill="{fl}"{stroke}{fo}/><polygon points="{right}" fill="{fr}"{stroke}{fo}/>'
                 f'<polygon points="{top}" fill="{ft}"{stroke}/>')
            if c and t.get("windows"):
                for k in range(int(hg // 7)):
                    for side, sxo in (("l", -SX + 2.5), ("r", 3)):
                        if rnd.random() < .55:
                            wy = by - hg + SY + 4 + k * 7 + (1.5 if side == "r" else 0)
                            g += (f'<rect class="w" x="{bx + sxo:.1f}" y="{wy:.1f}" width="2.2" height="2.6" fill="{t["windows"]}" '
                                  f'style="animation-delay:{rnd.uniform(0, 6):.1f}s"/>')
            if lv == 4 and t.get("beacon"):
                g += f'<circle class="bk" cx="{bx}" cy="{by - hg + SY - 3}" r="1.4" fill="{t["beacon"]}" filter="url(#glow)"/>'
            tiles.append((x + y, g + "</g>"))
    tiles.sort(key=lambda p: p[0])
    out += [g for _, g in tiles]
    if t.get("rain"):
        out += [f'<line class="rn" x1="{(rx := rnd.uniform(0, w * 1.1)):.0f}" y1="-20" x2="{rx - 3:.0f}" y2="-8" '
                f'style="animation-delay:-{rnd.uniform(0, 1):.2f}s;animation-duration:{rnd.uniform(.6, 1):.2f}s"/>' for _ in range(110)]
    if t.get("fog"):
        out.append(f'<rect class="fg" x="-{w}" y="{h - 70}" width="{w * 3}" height="70" fill="url(#fog)"/>')
        defs.append('<linearGradient id="fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fb4d8" stop-opacity="0"/>'
                    '<stop offset="1" stop-color="#9fb4d8" stop-opacity=".18"/></linearGradient>')
    if t.get("caption"):
        out.append(f'<text x="24" y="{h - 14}" fill="{t["caption"]}" font-family="JetBrains Mono,monospace" font-size="11" opacity=".7">'
                   f'{sum(map(sum, weeks))} contributions in the last year</text>')
    css = ("@keyframes r{0%{transform:translateY(50px);opacity:0}100%{transform:none;opacity:1}}"
           ".w{animation:b 6s steps(1) infinite}@keyframes b{0%,80%{opacity:.9}81%,92%{opacity:.08}93%{opacity:.9}}"
           ".s{animation:tw 3s ease-in-out infinite alternate}@keyframes tw{from{opacity:.15}to{opacity:.9}}"
           ".bk{animation:bk 1.4s steps(1) infinite}@keyframes bk{0%,50%{opacity:1}51%{opacity:.1}}"
           ".rn{stroke:#9fb4d8;stroke-width:.8;opacity:.35;animation:rn .8s linear infinite}"
           f"@keyframes rn{{to{{transform:translate(-30px,{h + 40}px)}}}}"
           f".fg{{animation:fg 18s linear infinite}}@keyframes fg{{to{{transform:translateX({w}px)}}}}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<defs>{"".join(defs)}</defs><style>{css}</style>{"".join(out)}</svg>')


THEME = dict(sky=[(0, "#0b0e14"), (1, "#1b2230")], windows="#ffcf70", rain=1, fog=1, beacon="#ff5f5f",
                       levels=[("#22262e", "#1a1d24", "#14161b"), ("#4a5568", "#2d3440", "#232831"), ("#5f6b80", "#3a4352", "#2d3440"),
                               ("#7a879c", "#4a5568", "#3a4352"), ("#a3b1c6", "#5f6b80", "#4a5568")], caption="#a3b1c6")


if __name__ == "__main__":
    user, path = sys.argv[1], sys.argv[2]
    svg = city(fetch(user), THEME)  # render before touching the file so a failed fetch keeps the old one
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(svg)
