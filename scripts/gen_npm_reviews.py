#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 npm（na57）包年度回顾：每年一篇（仿 GitHub / Gitee / 豆瓣 按年回顾）。
读取 /tmp/npm_data.json（maintainer:na57 全部公开包元数据，含每个版本的发布时间线）。
产出：
  public/npm-reviews/YYYY.html  （该年独立图表页：月度分布 + 当年发布明细）
  src/content/blog/npm-YYYY.md  （标签 npm，iframe 内嵌当年图表）
缺失或 --refresh 时从 npm registry 重新拉取。
"""
import json, html, os, urllib.request, urllib.parse, sys

ROOT = "/Users/na57/workshop/na57.github.io"
DATA = "/tmp/npm_data.json"
HTML_DIR = os.path.join(ROOT, "public/npm-reviews")
MD_DIR = os.path.join(ROOT, "src/content/blog")

NPM_RED = "#cb3837"
NPM_TEAL = "#0d9488"
UA = {"User-Agent": "Mozilla/5.0 (na57-blog-importer)"}

STYLE = """
* { box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif; margin:0; background:#f6f8fa; color:#1e293b; line-height:1.6; }
.wrap { max-width:1000px; margin:0 auto; padding:32px 24px 80px; }
h1 { font-size:26px; margin:0 0 4px; }
.sub { color:#64748b; margin-bottom:24px; font-size:14px; }
.cards { display:flex; flex-wrap:wrap; gap:12px; margin:20px 0 28px; }
.card { background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:14px 18px; min-width:120px; flex:1; }
.card .n { font-size:24px; font-weight:700; }
.card .l { font-size:12px; color:#64748b; }
section { background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:20px 22px; margin:18px 0; }
h2 { font-size:19px; margin:0 0 14px; border-left:4px solid #cb3837; padding-left:10px; }
.items { font-size:13px; }
.items li { margin:6px 0; break-inside:avoid; }
.pkgs { font-size:13.5px; list-style:none; padding:0; margin:0; }
.pkgs li { padding:9px 0; border-bottom:1px dashed #eef2f7; }
.pkgs li:last-child { border-bottom:none; }
.bdwrap { margin-right:6px; }
.bd { display:inline-block; font-size:12px; padding:2px 8px; border-radius:999px; border:1px solid; }
.dt { color:#94a3b8; font-size:12px; font-family:ui-monospace,monospace; margin-right:4px; }
.pd { color:#475569; font-size:12.5px; margin:2px 0 1px; }
.pm { color:#94a3b8; font-size:11.5px; font-family:ui-monospace,monospace; }
a { color:#0f172a; text-decoration:none; }
a:hover { text-decoration:underline; color:#cb3837; }
.note { font-size:12.5px; color:#64748b; }
""".strip()


def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def series(name):
    n = name.lower()
    if n.startswith("nagu"):
        return ("纳古/家谱系", NPM_RED)
    if n.startswith("ynu"):
        return ("云大/校园系", "#2563eb")
    if n.startswith("wx") or "wechat" in n or "wxe" in n or "wxoauth" in n or "access-token" in n:
        return ("微信/认证系", "#d97706")
    if "mongo" in n or "redis" in n:
        return ("存储中间件", "#7c3aed")
    return ("其他工具", "#475569")


def load_or_fetch(refresh=False):
    if (not refresh) and os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            return json.load(f)
    s = fetch_json("https://registry.npmjs.org/-/v1/search?text=maintainer:na57&size=250")
    names = [o["package"]["name"] for o in s.get("objects", [])]
    pkgs = []
    for name in names:
        enc = name.replace("/", "%2f")
        try:
            doc = fetch_json(f"https://registry.npmjs.org/{enc}")
        except Exception as e:
            print("  skip", name, e, file=sys.stderr)
            continue
        time = doc.get("time", {})
        created = time.get("created", "")[:10]
        dist = doc.get("dist-tags", {})
        latest = dist.get("latest", "")
        last_release = time.get(latest, created)[:10]
        versions = doc.get("versions", {})
        ver_count = len(versions)
        latest_doc = versions.get(latest, {}) if latest else {}
        desc = (latest_doc.get("description") or doc.get("description") or "").strip()
        repo = ""
        r = latest_doc.get("repository") or doc.get("repository") or {}
        if isinstance(r, dict):
            repo = r.get("url", "")
        if repo.startswith("git+"):
            repo = repo[4:]
        if repo.endswith(".git"):
            repo = repo[:-4]
        lic = latest_doc.get("license") or doc.get("license") or ""
        if isinstance(lic, dict):
            lic = lic.get("type", "")
        deps = latest_doc.get("dependencies") or {}
        home = latest_doc.get("homepage") or doc.get("homepage") or ""
        # 每个真实版本的发布时间线（排除 created/modified 元数据键）
        releases = []
        for v in versions:
            if v in time:
                releases.append({"v": v, "date": time[v][:10]})
        releases.sort(key=lambda x: x["date"])
        pkgs.append({
            "name": name, "desc": desc, "latest": latest, "created": created,
            "last_release": last_release, "ver_count": ver_count, "license": lic,
            "deps": len(deps), "repo": repo, "home": home, "releases": releases,
        })
    pkgs.sort(key=lambda p: p["created"])
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(pkgs, f, ensure_ascii=False, indent=1)
    return pkgs


def month_chart(y, monthly):
    """单系列 12 个月柱图：当年版本发布数。"""
    maxv = max(monthly + [1])
    W, H, padL, padB = 940, 300, 36, 28
    plotW = W - padL - 10
    plotH = H - padB - 10
    groupW = plotW / 12
    barW = min(46, groupW * 0.6)
    svg = [f"<svg viewBox='0 0 {W} {H}' width='100%' style='max-width:{W}px'>"]
    svg.append(f"<line x1='{padL}' y1='{H-padB}' x2='{W-6}' y2='{H-padB}' stroke='#cbd5e1'></line>")
    for g in range(5):
        val = maxv * g / 4
        yy = (H - padB) - plotH * g / 4
        svg.append(f"<line x1='{padL}' y1='{yy:.1f}' x2='{W-6}' y2='{yy:.1f}' stroke='#eef2f7'></line>")
        svg.append(f"<text x='{padL-4}' y='{yy+4:.1f}' text-anchor='end' font-size='10' fill='#94a3b8'>{int(round(val))}</text>")
    for i in range(12):
        gx = padL + i * groupW + groupW / 2
        v = monthly[i]
        bh = plotH * v / maxv
        bx = gx - barW / 2
        by = (H - padB) - bh
        svg.append(f"<rect x='{bx:.1f}' y='{by:.1f}' width='{barW:.1f}' height='{bh:.1f}' rx='3' fill='{NPM_RED}'></rect>")
        if v > 0:
            svg.append(f"<text x='{gx:.1f}' y='{by-4:.1f}' text-anchor='middle' font-size='10' fill='#1e293b'>{v}</text>")
        svg.append(f"<text x='{gx:.1f}' y='{H-padB+16}' text-anchor='middle' font-size='10.5' fill='#475569'>{i+1}</text>")
    svg.append("</svg>")
    return f"<section><h2>{y} 年月度发布分布</h2>{''.join(svg)}<p class='note'>柱高为当月发布的版本数（含各包的 patch/minor/major 发布），按月归并。</p></section>"


def gen_year(y, pkgs, cumulative_upto):
    # 当年首次发布的包
    first_pub = [p for p in pkgs if p["created"][:4] == y]
    first_pub.sort(key=lambda p: p["created"], reverse=True)
    # 当年版本发布记录
    rel_in_year = [(p, r) for p in pkgs for r in p["releases"] if r["date"][:4] == y]
    rel_in_year.sort(key=lambda x: x[1]["date"], reverse=True)
    active_pkgs = len({p["name"] for p, _ in rel_in_year})
    monthly = [0] * 12
    for _, r in rel_in_year:
        try:
            m = int(r["date"][5:7])
            if 1 <= m <= 12:
                monthly[m - 1] += 1
        except ValueError:
            pass
    last_date = (rel_in_year[0][1]["date"] if rel_in_year else (first_pub[0]["created"] if first_pub else f"{y}-12-31"))

    cards = (
        f"<div class='cards'>"
        f"<div class='card'><div class='n' style='color:{NPM_RED}'>{len(first_pub)}</div><div class='l'>当年首次发布</div></div>"
        f"<div class='card'><div class='n'>{len(rel_in_year)}</div><div class='l'>当年版本发布</div></div>"
        f"<div class='card'><div class='n'>{active_pkgs}</div><div class='l'>活跃包数</div></div>"
        f"<div class='card'><div class='n'>{cumulative_upto}</div><div class='l'>累计包数（至年底）</div></div>"
        f"</div>"
    )
    chart = month_chart(y, monthly)

    # 首次发布的包清单
    first_lis = []
    for p in first_pub:
        link = f"https://www.npmjs.com/package/{urllib.parse.quote(p['name'], safe='@/')}"
        s, sc = series(p["name"])
        badge = f"<span class='bd' style='background:{sc}22;color:{sc};border-color:{sc}55'>{html.escape(s)}</span>"
        meta = f"v{p['latest']} · {p['ver_count']} 版本 · 首发 {p['created']} · 最后发布 {p['last_release']}"
        if p["license"]:
            meta += f" · {html.escape(str(p['license']))}"
        if p["deps"]:
            meta += f" · {p['deps']} 依赖"
        first_lis.append(
            f"<li><span class='bdwrap'>{badge}</span> "
            f"<a href='{link}' target='_blank' rel='noopener'><b>{html.escape(p['name'])}</b></a> "
            f"<div class='pd'>{html.escape(p['desc'])}</div>"
            f"<div class='pm'>{meta}</div></li>"
        )
    first_section = (
        f"<section><h2>当年首次发布的包（{len(first_pub)}）</h2><ul class='pkgs'>{''.join(first_lis)}</ul></section>"
        if first_lis else ""
    )

    # 版本发布记录清单
    rel_lis = []
    for p, r in rel_in_year:
        vlink = f"https://www.npmjs.com/package/{urllib.parse.quote(p['name'], safe='@/')}/v/{urllib.parse.quote(r['v'], safe='@/')}"
        s, sc = series(p["name"])
        rel_lis.append(
            f"<li><span class='dt'>{html.escape(r['date'])}</span> "
            f"<a href='{vlink}' target='_blank' rel='noopener'><b>{html.escape(p['name'])}@{html.escape(r['v'])}</b></a> "
            f"<span class='bd' style='background:{sc}22;color:{sc};border-color:{sc}55'>{html.escape(s)}</span></li>"
        )
    rel_section = (
        f"<section><h2>当年版本发布记录（{len(rel_in_year)}）</h2>"
        f"<p class='note'>按发布日期倒序，链接到对应版本的 npm 页面。</p>"
        f"<ul class='items'>{''.join(rel_lis)}</ul></section>"
    )

    out = f"""<!DOCTYPE html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{y} 年 npm 包回顾（na57）</title>
<style>{STYLE}</style>
</head>
<body><div class='wrap'>
<h1>{y} 年 npm 包回顾</h1>
<div class='sub'>维护者：na57 · 数据来源：npm registry（maintainer:na57）· 当年首次发布 {len(first_pub)} 个、版本发布 {len(rel_in_year)} 次</div>
{cards}
{chart}
{first_section}
{rel_section}
</div></body></html>"""
    os.makedirs(HTML_DIR, exist_ok=True)
    with open(os.path.join(HTML_DIR, f"{y}.html"), "w", encoding="utf-8") as f:
        f.write(out)

    md = f"""---
title: "{y} 年 npm 包回顾"
description: "{y} 年以 na57 身份在 npm 发布：首次发布 {len(first_pub)} 个包、累计 {len(rel_in_year)} 次版本发布。"
date: {last_date}
tags: ["npm"]
---

{y} 年，我在 npm 上以 **na57** 身份**首次发布 {len(first_pub)} 个包、累计 {len(rel_in_year)} 次版本发布**（截至该年底累计 {cumulative_upto} 个包）。

下面是这一年的完整回顾（月度发布分布 + 首次发布清单 + 版本发布记录）：

[▶ 打开 {y} 年 npm 包回顾（独立页面）](/npm-reviews/{y}.html)

<iframe src="/npm-reviews/{y}.html" width="100%" height="900" onload="try{{this.style.height=(this.contentWindow.document.body.scrollHeight+40)+'px'}}catch(e){{}}" style="border:1px solid #e2e8f0;border-radius:12px;" loading="lazy"></iframe>

> 这份回顾由 npm registry 公开发布元数据自动汇总生成；包名链接至 npm 页面，版本发布记录链接至对应版本。
"""
    with open(os.path.join(MD_DIR, f"npm-{y}.md"), "w", encoding="utf-8") as f:
        f.write(md)


def build(refresh=False):
    pkgs = load_or_fetch(refresh)
    # 首次发布年份分布（用于累计）
    created_years = {}
    for p in pkgs:
        y = p["created"][:4]
        created_years[y] = created_years.get(y, 0) + 1
    yset = set(created_years.keys())
    for p in pkgs:
        for r in p["releases"]:
            yset.add(r["date"][:4])
    ylist = sorted(yset)
    cum = 0
    cum_map = {}
    for y in sorted(created_years.keys()):
        cum += created_years[y]
        cum_map[y] = cum
    for y in ylist:
        # 累计到该年底：含该年及之前所有首次发布
        cu = sum(created_years.get(yy, 0) for yy in ylist if yy <= y)
        gen_year(y, pkgs, cu)
    print(f"generated {len(ylist)} npm year pages: {ylist[0]}..{ylist[-1]}")


if __name__ == "__main__":
    build(refresh="--refresh" in sys.argv)
