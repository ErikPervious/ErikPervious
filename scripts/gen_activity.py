# -*- coding: utf-8 -*-
"""Gera os cards de atividade do README (assets/stats-*.svg, langs-*.svg,
streak-*.svg) no design system do banner, com dados reais do GitHub.

Uso: GITHUB_TOKEN no ambiente (na Action) ou `gh auth token` (local).
Sem dependências externas — apenas stdlib.
"""
import io
import json
import os
import subprocess
import urllib.request

USER = "erikpervious"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

MONO = "ui-monospace,'Cascadia Code','JetBrains Mono',Consolas,'Liberation Mono',Menlo,monospace"

THEMES = {
    "dark": dict(
        panel="#0F172A", panel_op="0.80", border="#FFFFFF", border_op="0.08",
        text="#F8FAFC", muted="#94A3B8", faint="#64748B",
        acc1="#7C3AED", acc2="#22D3EE", acc3="#10B981",
        sheen="#FFFFFF", refl_op="0.05", scan="#FFFFFF", scan_op="0.045",
        top_hi="#FFFFFF", top_hi_op="0.10", shim_op="0.65",
        track="#FFFFFF", track_op="0.07",
    ),
    "light": dict(
        panel="#F8FAFC", panel_op="0.90", border="#0F172A", border_op="0.08",
        text="#0F172A", muted="#475569", faint="#64748B",
        acc1="#1D4ED8", acc2="#0E7490", acc3="#047857",
        sheen="#0F172A", refl_op="0.50", scan="#0F172A", scan_op="0.03",
        top_hi="#0F172A", top_hi_op="0.05", shim_op="0.45",
        track="#0F172A", track_op="0.08",
    ),
}


def ff(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(n):
    return f"{n:,}".replace(",", ".")


# ------------------------------------------------------------------ dados
def token():
    tk = os.environ.get("GITHUB_TOKEN", "").strip()
    if tk:
        return tk
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


QUERY = """
query {
  user(login: "%s") {
    followers { totalCount }
    repositories(privacy: PUBLIC, first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
""" % USER


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": "bearer " + token(),
                 "User-Agent": "erikpervious-profile-gen",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    if "errors" in data:
        raise SystemExit("GraphQL: " + json.dumps(data["errors"]))
    u = data["data"]["user"]
    repos = u["repositories"]
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    counts = [d["contributionCount"] for d in days]

    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)
    current = 0
    idx = len(counts) - 1
    if idx >= 0 and counts[idx] == 0:  # hoje ainda sem contribuição não quebra o streak
        idx -= 1
    while idx >= 0 and counts[idx] > 0:
        current += 1
        idx -= 1

    langs = {}
    for repo in repos["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    total_size = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]

    return dict(
        stars=sum(r["stargazerCount"] for r in repos["nodes"]),
        repos=repos["totalCount"],
        followers=u["followers"]["totalCount"],
        total=cc["contributionCalendar"]["totalContributions"],
        best_day=max(counts, default=0),
        active_days=sum(1 for c in counts if c > 0),
        daily_avg=cc["contributionCalendar"]["totalContributions"] / max(1, len(counts)),
        streak_cur=current,
        streak_max=longest,
        langs=[(name, 100.0 * size / total_size) for name, size in top],
    )


# ------------------------------------------------------------------ svg base
def triad(gid, t, extra=""):
    a1, a2, a3 = t["acc1"], t["acc2"], t["acc3"]
    return (
        f'<linearGradient id="{gid}" {extra}>'
        f'<stop offset="0" stop-color="{a1}"><animate attributeName="stop-color" values="{a1};{a2};{a3};{a1}" dur="8s" repeatCount="indefinite"/></stop>'
        f'<stop offset="0.55" stop-color="{a2}"><animate attributeName="stop-color" values="{a2};{a3};{a1};{a2}" dur="8s" repeatCount="indefinite"/></stop>'
        f'<stop offset="1" stop-color="{a3}"><animate attributeName="stop-color" values="{a3};{a1};{a2};{a3}" dur="8s" repeatCount="indefinite"/></stop>'
        f'</linearGradient>')


def glass(t, w, h, rx=16):
    defs = (
        f'<clipPath id="cp"><rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}"/></clipPath>'
        + triad("tg", t)
        + f'<linearGradient id="sg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{w}" y2="0">'
          f'<stop offset="0" stop-color="{t["acc2"]}" stop-opacity="0"/>'
          f'<stop offset="0.5" stop-color="{t["acc2"]}" stop-opacity="0.9"/>'
          f'<stop offset="1" stop-color="{t["acc2"]}" stop-opacity="0"/>'
          f'<animateTransform attributeName="gradientTransform" type="translate" values="-{w} 0;{w} 0" dur="6s" repeatCount="indefinite"/>'
          f'</linearGradient>'
        + f'<linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{t["sheen"]}" stop-opacity="0.10"/>'
          f'<stop offset="1" stop-color="{t["sheen"]}" stop-opacity="0"/></linearGradient>'
        + f'<linearGradient id="scg" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{t["scan"]}" stop-opacity="0"/>'
          f'<stop offset="0.5" stop-color="{t["scan"]}" stop-opacity="1"/>'
          f'<stop offset="1" stop-color="{t["scan"]}" stop-opacity="0"/></linearGradient>')
    body = (
        f'<g opacity="0"><animate attributeName="opacity" values="0;1" begin="0.05s" dur="0.6s" fill="freeze"/>'
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="{t["panel"]}" fill-opacity="{t["panel_op"]}"/>'
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="none" stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>'
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="none" stroke="url(#sg)" stroke-opacity="{t["shim_op"]}"/>'
        f'<line x1="18" y1="1.5" x2="{w - 18}" y2="1.5" stroke="{t["top_hi"]}" stroke-opacity="{t["top_hi_op"]}"/>'
        f'<g clip-path="url(#cp)"><rect x="0" y="0" width="{w}" height="{min(110, h // 2)}" fill="url(#rg)" opacity="{t["refl_op"]}"/></g></g>'
        f'<g clip-path="url(#cp)"><rect x="0" y="-70" width="{w}" height="70" fill="url(#scg)" opacity="{t["scan_op"]}">'
        f'<animate attributeName="y" values="-70;{h}" dur="6.5s" repeatCount="indefinite"/></rect></g>')
    return defs, body


def reveal(begin, dy=7):
    return (
        f'<animate attributeName="opacity" values="0;1" begin="{ff(begin)}s" dur="0.5s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" values="0 {dy};0 0" begin="{ff(begin)}s" dur="0.5s" '
        f'calcMode="spline" keyTimes="0;1" keySplines="0.16 1 0.3 1" fill="freeze"/>')


def wrap(w, h, title, defs, body):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">\n'
        f'<title>{esc(title)}</title>\n<defs>{defs}</defs>\n{body}\n</svg>\n')


# ------------------------------------------------------------------ cards
def card_stats(theme, d):
    t = THEMES[theme]
    W, H = 578, 232
    defs, body = glass(t, W, H)
    dots = [t["acc1"], t["acc2"], t["acc3"], t["acc2"], t["acc1"], t["acc3"]]
    rows = [
        ("contribuições · 12m", d["total"]),
        ("dias ativos · 12m", d["active_days"]),
        ("melhor dia", d["best_day"]),
        ("stars", d["stars"]),
        ("repositórios públicos", d["repos"]),
        ("seguidores", d["followers"]),
    ]
    b = [body]
    b.append(f'<g opacity="0">{reveal(0.2)}'
             f'<text x="28" y="36" font-family="{MONO}" font-size="12" fill="{t["faint"]}">» resumo · últimos 12 meses</text></g>')
    for i, (label, value) in enumerate(rows):
        y = 68 + i * 26
        b.append(
            f'<g opacity="0">{reveal(0.3 + i * 0.09)}'
            f'<circle cx="32" cy="{y - 4.5}" r="2.4" fill="{dots[i]}"/>'
            f'<text x="44" y="{y}" font-family="{MONO}" font-size="13" fill="{t["muted"]}">{esc(label)}</text>'
            f'<line x1="250" y1="{y - 4}" x2="{470}" y2="{y - 4}" stroke="{t["border"]}" stroke-opacity="{t["border_op"]}" stroke-dasharray="1.5 6"/>'
            f'<text x="550" y="{y}" text-anchor="end" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{t["text"]}">{fmt(value)}</text></g>')
    return wrap(W, H, "Resumo de atividade no GitHub — últimos 12 meses", defs, "".join(b))


def card_langs(theme, d):
    t = THEMES[theme]
    W, H = 578, 232
    defs, body = glass(t, W, H)
    b = [body]
    b.append(f'<g opacity="0">{reveal(0.2)}'
             f'<text x="28" y="36" font-family="{MONO}" font-size="12" fill="{t["faint"]}">» top linguagens</text>'
             f'<text x="550" y="36" text-anchor="end" font-family="{MONO}" font-size="11" fill="{t["faint"]}">por bytes · repos públicos</text></g>')
    langs = d["langs"]
    maxpct = max((p for _, p in langs), default=1.0)
    for i, (name, pct) in enumerate(langs):
        y = 70 + i * 27
        bw = 300.0 * (pct / maxpct)
        pj = f"{pct:.1f}".replace(".", ",") + "%"
        b.append(
            f'<g opacity="0">{reveal(0.3 + i * 0.09)}'
            f'<text x="28" y="{y}" font-family="{MONO}" font-size="12.5" fill="{t["muted"]}">{esc(name)}</text>'
            f'<rect x="180" y="{y - 10}" width="300" height="8" rx="4" fill="{t["track"]}" fill-opacity="{t["track_op"]}"/>'
            f'<rect x="180" y="{y - 10}" width="0" height="8" rx="4" fill="url(#tg)">'
            f'<animate attributeName="width" values="0;{ff(bw)}" begin="{ff(0.45 + i * 0.09)}s" dur="0.8s" '
            f'calcMode="spline" keyTimes="0;1" keySplines="0.16 1 0.3 1" fill="freeze"/></rect>'
            f'<text x="550" y="{y}" text-anchor="end" font-family="{MONO}" font-size="12" font-weight="700" fill="{t["text"]}">{pj}</text></g>')
    return wrap(W, H, "Linguagens mais usadas nos repositórios públicos", defs, "".join(b))


def card_streak(theme, d):
    t = THEMES[theme]
    W, H = 1180, 132
    defs, body = glass(t, W, H, rx=20)
    b = [body]
    avg = f"{d['daily_avg']:.1f}".replace(".", ",")
    tiles = [
        (avg, "média diária · 12m", 197, 28),
        (f'{fmt(d["streak_cur"])} dias', "sequência atual", 590, 34),
        (f'{fmt(d["streak_max"])} dias', "maior sequência", 983, 28),
    ]
    b.append(f'<line x1="393" y1="30" x2="393" y2="102" stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>'
             f'<line x1="787" y1="30" x2="787" y2="102" stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>')
    for i, (value, label, cx, fs) in enumerate(tiles):
        b.append(
            f'<g opacity="0">{reveal(0.25 + i * 0.14)}'
            f'<text x="{cx}" y="{66 if i != 1 else 68}" text-anchor="middle" font-family="{MONO}" font-size="{fs}" '
            f'font-weight="700" fill="url(#tg)">{esc(value)}</text>'
            f'<text x="{cx}" y="98" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{t["muted"]}">{esc(label)}</text></g>')
    return wrap(W, H, "Sequência de contribuições no GitHub", defs, "".join(b))


if __name__ == "__main__":
    d = fetch()
    print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items() if k != "langs"}, ensure_ascii=False))
    print("langs:", [(n, round(p, 1)) for n, p in d["langs"]])
    os.makedirs(OUT, exist_ok=True)
    for theme in ("dark", "light"):
        for name, fn in (("stats", card_stats), ("langs", card_langs), ("streak", card_streak)):
            p = os.path.join(OUT, f"{name}-{theme}.svg")
            with io.open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(fn(theme, d))
            print(os.path.basename(p), os.path.getsize(p))
