#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 npm（na57）包年度回顾：public/npm-reviews/index.html + src/content/blog/npm-年度回顾.md
直接从 npm registry 拉取 maintainer:na57 的全部包元数据，按首次发布年份归档。
缓存于 /tmp/npm_data.json（缺失或 --refresh 时重新拉取）。
"""
import json, html, datetime, os, urllib.request, urllib.parse, sys

ROOT = "/Users/na57/workshop/na57.github.io"
DATA = "/tmp/npm_data.json"
HTML_OUT = os.path.join(ROOT, "public/npm-reviews/index.html")
MD_OUT = os.path.join(ROOT, "src/content/blog/npm-年度回顾.md")

NPM_RED = "#cb3837"
NPM_TEAL = "#0d9488"
UA = {"User-Agent": "Mozilla/5.0 (na57-blog-importer)"}

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
    # 1) 搜索 maintainer
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
        modified = time.get("modified", "")[:10]
        dist = doc.get("dist-tags", {})
        latest = dist.get("latest", "")
        last_release = time.get(latest, created)[:10]  # 最后一个版本的实际发布日期
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
        pkgs.append({
            "name": name,
            "desc": desc,
            "latest": latest,
            "created": created,
            "modified": modified,
            "last_release": last_release,
            "ver_count": ver_count,
            "license": lic,
            "deps": len(deps),
            "repo": repo,
            "home": home,
        })
    pkgs.sort(key=lambda p: p["created"])
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(pkgs, f, ensure_ascii=False, indent=1)
    return pkgs

def bar_chart(ylist, counts, color, title, note):
    maxv = max(counts + [1])
    W, H, padL, padB = 940, 300, 36, 28
    plotW = W - padL - 10
    plotH = H - padB - 10
    n = len(ylist)
    groupW = plotW / n
    barW = min(46, groupW * 0.6)
    svg = [f"<svg viewBox='0 0 {W} {H}' width='100%' style='max-width:{W}px'>"]
    svg.append(f"<line x1='{padL}' y1='{H-padB}' x2='{W-6}' y2='{H-padB}' stroke='#cbd5e1'></line>")
    for g in range(5):
        val = maxv * g / 4
        yy = (H - padB) - plotH * g / 4
        svg.append(f"<line x1='{padL}' y1='{yy:.1f}' x2='{W-6}' y2='{yy:.1f}' stroke='#eef2f7'></line>")
        svg.append(f"<text x='{padL-4}' y='{yy+4:.1f}' text-anchor='end' font-size='10' fill='#94a3b8'>{int(round(val))}</text>")
    for i, y in enumerate(ylist):
        gx = padL + i * groupW + groupW / 2
        v = counts[i]
        bh = plotH * v / maxv
        bx = gx - barW / 2
        by = (H - padB) - bh
        svg.append(f"<rect x='{bx:.1f}' y='{by:.1f}' width='{barW:.1f}' height='{bh:.1f}' rx='3' fill='{color}'></rect>")
        if v > 0:
            svg.append(f"<text x='{gx:.1f}' y='{by-4:.1f}' text-anchor='middle' font-size='10' fill='#1e293b'>{v}</text>")
        svg.append(f"<text x='{gx:.1f}' y='{H-padB+16}' text-anchor='middle' font-size='10.5' fill='#475569'>{y[2:]}</text>")
    svg.append("</svg>")
    return f"<section><h2>{title}</h2>{''.join(svg)}<p class='note'>{note}</p></section>"

def build(refresh=False):
    pkgs = load_or_fetch(refresh)
    years = {}
    for p in pkgs:
        y = p["created"][:4]
        years.setdefault(y, []).append(p)
    ylist = sorted(years.keys())
    created_counts = [len(years[y]) for y in ylist]
    # 按最后发布年份（真实发布活跃度；time.modified 多为 2022 批量元数据触碰，不可信）
    myears = {}
    for p in pkgs:
        my = p["last_release"][:4]
        myears.setdefault(my, []).append(p)
    mylist = sorted(myears.keys())
    modified_counts = [len(myears[y]) for y in mylist]

    total_versions = sum(p["ver_count"] for p in pkgs)
    first_year, last_year = ylist[0], ylist[-1]
    busiest_created = max(ylist, key=lambda y: len(years[y]))
    last_release_year = mylist[-1]
    series_count = {}
    for p in pkgs:
        s, _ = series(p["name"])
        series_count[s] = series_count.get(s, 0) + 1

    # 逐年包清单（按首次发布年）
    year_sections = []
    for y in ylist:
        items = sorted(years[y], key=lambda p: p["created"])
        lis = []
        for p in items:
            link = f"https://www.npmjs.com/package/{urllib.parse.quote(p['name'], safe='@/')}"
            s, sc = series(p["name"])
            badge = f"<span class='bd' style='background:{sc}22;color:{sc};border-color:{sc}55'>{html.escape(s)}</span>"
            meta = f"v{p['latest']} · {p['ver_count']} 版本 · 首发 {p['created']} · 最后发布 {p['last_release']}"
            if p["license"]:
                meta += f" · {html.escape(str(p['license']))}"
            if p["deps"]:
                meta += f" · {p['deps']} 依赖"
            lis.append(
                f"<li><span class='bdwrap'>{badge}</span> "
                f"<a href='{link}' target='_blank' rel='noopener'><b>{html.escape(p['name'])}</b></a> "
                f"<div class='pd'>{html.escape(p['desc'])}</div>"
                f"<div class='pm'>{meta}</div></li>"
            )
        year_sections.append(
            f"<details class='yr'><summary><b>{y}</b> 年 · 首次发布 {len(items)} 个包</summary>"
            f"<ul class='pkgs'>{''.join(lis)}</ul></details>"
        )

    series_badges = " ".join(
        f"<span class='bd' style='background:{c}22;color:{c};border-color:{c}55'>{html.escape(s)} {n}</span>"
        for s, n in sorted(series_count.items(), key=lambda x: -x[1])
        for c in [series(s)[1]]
    ) if False else " ".join(
        f"<span class='bd' style='background:{series(s)[1]}22;color:{series(s)[1]};border-color:{series(s)[1]}55'>{html.escape(s)} {n}</span>"
        for s, n in sorted(series_count.items(), key=lambda x: -x[1])
    )

    cards = (
        f"<div class='cards'>"
        f"<div class='card'><div class='n' style='color:{NPM_RED}'>{len(pkgs)}</div><div class='l'>发布包总数</div></div>"
        f"<div class='card'><div class='n'>{total_versions}</div><div class='l'>累计版本发布</div></div>"
        f"<div class='card'><div class='n'>{first_year}–{last_year}</div><div class='l'>首次发布年份</div></div>"
        f"<div class='card'><div class='n'>{busiest_created}</div><div class='l'>首发最多年份</div></div>"
        f"<div class='card'><div class='n'>{last_release_year}</div><div class='l'>最后发布年份</div></div>"
        f"</div>"
        f"<div class='series'>{series_badges}</div>"
    )

    chart_created = bar_chart(ylist, created_counts, NPM_RED, "逐年「首次发布」包数",
                              "柱高为当年首次发布（npm time.created）的包数量。")
    chart_modified = bar_chart(mylist, modified_counts, NPM_TEAL, "逐年「最后发布」包数",
                               "柱高为当年仍有新版本发布（npm 最新版本 time[latest]）的包数量，反映真实发布活跃度。")

    today = datetime.date.today().isoformat()
    out = f"""<!DOCTYPE html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>npm 包年度回顾（na57）</title>
<style>* {{ box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
  margin:0; background:#f6f8fa; color:#1e293b; line-height:1.6; }}
.wrap {{ max-width:1000px; margin:0 auto; padding:32px 24px 80px; }}
h1 {{ font-size:26px; margin:0 0 4px; }}
.sub {{ color:#64748b; margin-bottom:24px; font-size:14px; }}
.cards {{ display:flex; flex-wrap:wrap; gap:12px; margin:20px 0 12px; }}
.card {{ background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:14px 18px; min-width:120px; flex:1; }}
.card .n {{ font-size:24px; font-weight:700; }}
.card .l {{ font-size:12px; color:#64748b; }}
.series {{ margin:0 0 22px; display:flex; flex-wrap:wrap; gap:8px; }}
.bd {{ display:inline-block; font-size:12px; padding:2px 8px; border-radius:999px; border:1px solid; }}
section {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:20px 22px; margin:18px 0; }}
h2 {{ font-size:19px; margin:0 0 14px; border-left:4px solid {NPM_RED}; padding-left:10px; }}
.pkgs {{ font-size:13.5px; list-style:none; padding:0; margin:0; }}
.pkgs li {{ padding:9px 0; border-bottom:1px dashed #eef2f7; }}
.pkgs li:last-child {{ border-bottom:none; }}
.bdwrap {{ margin-right:6px; }}
.pd {{ color:#475569; font-size:12.5px; margin:2px 0 1px; }}
.pm {{ color:#94a3b8; font-size:11.5px; font-family:ui-monospace,monospace; }}
a {{ color:#0f172a; text-decoration:none; }}
a:hover {{ text-decoration:underline; color:{NPM_RED}; }}
.details.yr {{ border:1px solid #eef2f7; border-radius:8px; padding:10px 14px; margin:8px 0; background:#fafafa; }}
summary {{ cursor:pointer; font-size:14px; }}
.note {{ font-size:12.5px; color:#64748b; }}
</style>
</head>
<body><div class='wrap'>
<h1>npm 包年度回顾</h1>
<div class='sub'>维护者：na57 · 数据来源：npm registry（maintainer:na57）· 生成于 {today}</div>
{cards}
{chart_created}
{chart_modified}
<section><h2>按首次发布年份浏览全部包</h2>
<p class='note'>点击年份展开当年发布的包（包名链接至 npm 页面）。主要聚类：纳古/家谱系（nagu-*）、云大/校园系（ynu-*）、微信/认证系（wx*/access-token-*）。</p>
{''.join(year_sections)}
</section>
<section><h2>说明与口径</h2>
<ul class='note'>
  <li><b>收录范围</b>：npm 上 <code>maintainer:na57</code> 的全部公开包，共 <b>{len(pkgs)}</b> 个（通过 registry 搜索确认）。</li>
  <li><b>年份口径</b>：「首次发布年份」取包的 <code>time.created</code>；「最后发布年份」取<strong>最新版本</strong>的发布时间 <code>time[latest]</code>（注意：npm 的 <code>time.modified</code> 多为 2022 年的批量元数据触碰，不代表真实发布，故未采用）。</li>
  <li><b>主题归类</b>：依包名前缀做的粗分（nagu=纳古家谱、ynu=云大校园、wx*/access-token=微信/认证、*-mongo/redis=存储），仅供速览。</li>
  <li><b>数据抓取</b>：直接读取 npm registry（公开 JSON，无需鉴权），脚本化汇总生成本页。</li>
</ul></section>
</div></body></html>"""

    os.makedirs(os.path.dirname(HTML_OUT), exist_ok=True)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(out)

    md = f"""---
title: "npm 包年度回顾（na57）"
description: "npm 包年度回顾：na57 共发布 {len(pkgs)} 个公开包、累计 {total_versions} 次版本发布，首次发布横跨 {first_year}–{last_year}（{busiest_created} 年最密集）。"
date: {today}
tags: ["npm"]
---

这是我在 npm 上以 **na57** 身份发布的开源包汇总（共 **{len(pkgs)}** 个，累计 **{total_versions}** 次版本发布），按首次发布年份梳理。

主要聚类：
- **纳古/家谱系**（`nagu-concepts` / `nagu-pedigree` / `nagu-validates` / `nagu-profile` / `nagu-react-components` 等）
- **云大/校园系**（`ynu-*`：模型、客户端、通知等）
- **微信/认证系**（`wx*` / `access-token-*` / `wechat-message-handlers` 等）

下面是完整年度回顾（逐年柱状图 + 可展开包清单）：

[▶ 打开 npm 包年度回顾（独立页面）](/npm-reviews/index.html)

<iframe src="/npm-reviews/index.html" width="100%" height="3200" style="border:1px solid #e2e8f0;border-radius:12px;" loading="lazy"></iframe>

> 这份回顾由 npm registry 公开发布元数据自动汇总生成；逐年清单默认折叠，点击年份可展开查看每个包的版本、依赖与链接。
"""
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"HTML -> {HTML_OUT}")
    print(f"MD   -> {MD_OUT}")
    print(f"total={len(pkgs)} versions={total_versions} years={first_year}-{last_year} busiest={busiest_created} last_release={last_release_year}")

if __name__ == "__main__":
    build(refresh="--refresh" in sys.argv)
