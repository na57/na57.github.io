#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成豆瓣（na57）年度回顾：public/douban-reviews/index.html + src/content/blog/douban-年度回顾.md
读取 /tmp/douban_data.json（book/movie/music 数组：{id,title,date}）。
"""
import json, html, datetime, os, subprocess, sys

ROOT = "/Users/na57/workshop/na57.github.io"
DATA = "/tmp/douban_data.json"
HTML_OUT = os.path.join(ROOT, "public/douban-reviews/index.html")
MD_OUT = os.path.join(ROOT, "src/content/blog/douban-年度回顾.md")

KIND_LABEL = {"movie": "看过", "book": "读过", "music": "听过"}
KIND_COLOR = {"movie": "#007722", "book": "#c2410c", "music": "#2563eb"}
KIND_DOMAIN = {"movie": "movie", "book": "book", "music": "music"}

def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)

def build():
    data = load()
    # 按年聚合
    years = {}
    for kind, items in data.items():
        for it in items:
            y = it["date"][:4]
            years.setdefault(y, {"movie": [], "book": [], "music": []})[kind].append(it)
    ylist = sorted(years.keys())
    total = {k: len(data.get(k, [])) for k in ("book", "movie", "music")}
    first_year, last_year = ylist[0], ylist[-1]
    busiest = max(ylist, key=lambda y: sum(len(years[y][k]) for k in ("book", "movie", "music")))

    def bar_chart(series_kinds, title, note):
        # series_kinds: list of (kind, maxscale)  — 这里每图用统一 scale
        counts = {k: [len(years[y][k]) for y in ylist] for k in series_kinds}
        maxv = max([max(counts[k]) if counts[k] else 0 for k in series_kinds] + [1])
        W, H, padL, padB = 940, 300, 36, 28
        plotW = W - padL - 10
        plotH = H - padB - 10
        n = len(ylist)
        groupW = plotW / n
        barW = min(22, groupW / (len(series_kinds) + 1))
        svg = [f"<svg viewBox='0 0 {W} {H}' width='100%' style='max-width:{W}px'>"]
        svg.append(f"<line x1='{padL}' y1='{H-padB}' x2='{W-6}' y2='{H-padB}' stroke='#cbd5e1'></line>")
        # y gridlines (4)
        for g in range(5):
            val = maxv * g / 4
            yy = (H - padB) - plotH * g / 4
            svg.append(f"<line x1='{padL}' y1='{yy:.1f}' x2='{W-6}' y2='{yy:.1f}' stroke='#eef2f7'></line>")
            svg.append(f"<text x='{padL-4}' y='{yy+4:.1f}' text-anchor='end' font-size='10' fill='#94a3b8'>{int(round(val))}</text>")
        for i, y in enumerate(ylist):
            gx = padL + i * groupW + groupW / 2
            for si, k in enumerate(series_kinds):
                v = counts[k][i]
                bh = plotH * v / maxv
                bx = gx - (len(series_kinds) * barW) / 2 + si * barW
                by = (H - padB) - bh
                svg.append(f"<rect x='{bx:.1f}' y='{by:.1f}' width='{barW-2:.1f}' height='{bh:.1f}' rx='3' fill='{KIND_COLOR[k]}'></rect>")
                if v > 0:
                    svg.append(f"<text x='{bx + (barW-2)/2:.1f}' y='{by-4:.1f}' text-anchor='middle' font-size='10' fill='#1e293b'>{v}</text>")
            svg.append(f"<text x='{gx:.1f}' y='{H-padB+16}' text-anchor='middle' font-size='10.5' fill='#475569'>{y[2:]}</text>")
        # legend
        lx = padL + 4
        for k in series_kinds:
            svg.append(f"<rect x='{lx}' y='{10}' width='11' height='11' rx='2' fill='{KIND_COLOR[k]}'></rect>")
            svg.append(f"<text x='{lx+16}' y='20' font-size='11' fill='#475569'>{KIND_LABEL[k]}</text>")
            lx += 70
        svg.append("</svg>")
        return f"<section><h2>{title}</h2>{''.join(svg)}<p class='note'>{note}</p></section>"

    # 逐年清单
    year_sections = []
    for y in ylist:
        parts = []
        for k in ("movie", "book", "music"):
            items = sorted(years[y][k], key=lambda x: x["date"], reverse=True)
            if not items:
                continue
            lis = []
            for it in items:
                link = f"https://{KIND_DOMAIN[k]}.douban.com/subject/{it['id']}/"
                lis.append(f"<li><span class='dt'>{html.escape(it['date'])}</span> <a href='{link}' target='_blank' rel='noopener'>{html.escape(it['title'])}</a></li>")
            parts.append(
                f"<h4 style='color:{KIND_COLOR[k]}'>{KIND_LABEL[k]} {len(items)} 条</h4><ul class='items'>{''.join(lis)}</ul>"
            )
        tot = sum(len(years[y][k]) for k in ("movie", "book", "music"))
        year_sections.append(
            f"<details class='yr'><summary><b>{y}</b> 年 · 共 {tot} 条"
            f"（看过 {len(years[y]['movie'])} / 读过 {len(years[y]['book'])} / 听过 {len(years[y]['music'])}）</summary>"
            f"{''.join(parts)}</details>"
        )

    cards = (
        f"<div class='cards'>"
        f"<div class='card'><div class='n' style='color:{KIND_COLOR['book']}'>{total['book']}</div><div class='l'>读过（书）</div></div>"
        f"<div class='card'><div class='n' style='color:{KIND_COLOR['movie']}'>{total['movie']}</div><div class='l'>看过（影视）</div></div>"
        f"<div class='card'><div class='n' style='color:{KIND_COLOR['music']}'>{total['music']}</div><div class='l'>听过（音乐）</div></div>"
        f"<div class='card'><div class='n'>{first_year}–{last_year}</div><div class='l'>覆盖年份</div></div>"
        f"<div class='card'><div class='n'>{busiest}</div><div class='l'>最活跃年份</div></div>"
        f"</div>"
    )

    chart_movie = bar_chart(["movie"], "逐年「看过」影视数",
                            "柱高为当年标记「看过」的影视条目数（含电影/剧集）。")
    chart_bm = bar_chart(["book", "music"], "逐年「读过」与「听过」",
                         "读书与听唱片数量级相近，共用纵轴。")

    today = datetime.date.today().isoformat()
    out = f"""<!DOCTYPE html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>豆瓣年度回顾（na57）</title>
<style>* {{ box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
  margin:0; background:#f6f8fa; color:#1e293b; line-height:1.6; }}
.wrap {{ max-width:1000px; margin:0 auto; padding:32px 24px 80px; }}
h1 {{ font-size:26px; margin:0 0 4px; }}
.sub {{ color:#64748b; margin-bottom:24px; font-size:14px; }}
.cards {{ display:flex; flex-wrap:wrap; gap:12px; margin:20px 0 28px; }}
.card {{ background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:14px 18px; min-width:120px; flex:1; }}
.card .n {{ font-size:24px; font-weight:700; }}
.card .l {{ font-size:12px; color:#64748b; }}
section {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:20px 22px; margin:18px 0; }}
h2 {{ font-size:19px; margin:0 0 14px; border-left:4px solid #2e963f; padding-left:10px; }}
.items {{ font-size:13px; columns:2; column-gap:24px; }}
.items li {{ margin:3px 0; break-inside:avoid; }}
.dt {{ color:#94a3b8; font-size:12px; font-family:ui-monospace,monospace; margin-right:4px; }}
a {{ color:#0f172a; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.details.yr {{ border:1px solid #eef2f7; border-radius:8px; padding:10px 14px; margin:8px 0; background:#fafdfb; }}
summary {{ cursor:pointer; font-size:14px; }}
.note {{ font-size:12.5px; color:#64748b; }}
</style>
</head>
<body><div class='wrap'>
<h1>豆瓣年度回顾</h1>
<div class='sub'>用户：na57（头可乱发型不可断男）· 数据来源：豆瓣收藏列表（看过/读过/听过）· 生成于 {today}</div>
{cards}
{chart_movie}
{chart_bm}
<section><h2>逐年明细</h2>
<p class='note'>点击年份展开当年清单（标题链接至豆瓣条目）。影视条目较多，默认折叠。</p>
{''.join(year_sections)}
</section>
<section><h2>说明与口径</h2>
<ul class='note'>
  <li><b>读过/看过/听过</b>：分别取自豆瓣「读书·读过」「电影·看过」「音乐·听过」收藏列表，按标记日期（date）归入对应年份。</li>
  <li><b>数量差异</b>：豆瓣主页显示读过 137 / 看过 1663 / 听过 85；本页统计的是其中<b>带标记日期</b>的条目（书 {total['book']} / 影视 {total['movie']} / 音乐 {total['music']}），少量无日期或条目类型特殊的未计入。</li>
  <li><b>数据抓取</b>：通过豆瓣收藏列表页（每页 15 条）分页采集标题、条目 ID 与日期，脚本化汇总。</li>
</ul></section>
</div></body></html>"""

    os.makedirs(os.path.dirname(HTML_OUT), exist_ok=True)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(out)

    md = f"""---
title: "豆瓣年度回顾（na57）"
description: "豆瓣足迹年度回顾：读过 {total['book']} 本书、看过 {total['movie']} 部影视、听过 {total['music']} 张唱片，覆盖 {first_year}–{last_year}。"
date: {today}
tags: ["豆瓣"]
---

这是我在豆瓣（na57 / 头可乱发型不可断男）上的阅读、观影与听歌足迹汇总，按年份梳理。

- **读过**：{total['book']} 本
- **看过**：{total['movie']} 部影视
- **听过**：{total['music']} 张唱片
- 覆盖年份：**{first_year}–{last_year}**，最活跃年份 **{busiest}**

下面是完整年度回顾（逐年柱状图 + 可展开明细）：

[▶ 打开豆瓣年度回顾（独立页面）](/douban-reviews/index.html)

<iframe src="/douban-reviews/index.html" width="100%" height="2600" style="border:1px solid #e2e8f0;border-radius:12px;" loading="lazy"></iframe>

> 这份回顾由豆瓣收藏列表自动汇总生成；逐年清单默认折叠，点击年份可展开查看答案与条目链接。
"""
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"HTML -> {HTML_OUT}")
    print(f"MD   -> {MD_OUT}")
    print(f"totals: book={total['book']} movie={total['movie']} music={total['music']} years={first_year}-{last_year} busiest={busiest}")

if __name__ == "__main__":
    build()
