#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成豆瓣（na57）年度回顾：每年一篇（仿 GitHub / Gitee 按年回顾）。
读取 /tmp/douban_data.json（book/movie/music 数组：{id,title,date}）。
产出：
  public/douban-reviews/YYYY.html  （该年独立图表页：月度分布 + 条目明细）
  src/content/blog/douban-YYYY.md  （标签 豆瓣，iframe 内嵌当年图表）
"""
import json, html, os

ROOT = "/Users/na57/workshop/na57.github.io"
DATA = "/tmp/douban_data.json"
HTML_DIR = os.path.join(ROOT, "public/douban-reviews")
MD_DIR = os.path.join(ROOT, "src/content/blog")

KIND_LABEL = {"movie": "看过", "book": "读过", "music": "听过"}
KIND_COLOR = {"movie": "#007722", "book": "#c2410c", "music": "#2563eb"}
KIND_DOMAIN = {"movie": "movie", "book": "book", "music": "music"}
DOUBAN_GREEN = "#2e963f"

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
h2 { font-size:19px; margin:0 0 14px; border-left:4px solid #2e963f; padding-left:10px; }
.items { font-size:13px; columns:2; column-gap:24px; }
.items li { margin:3px 0; break-inside:avoid; }
.dt { color:#94a3b8; font-size:12px; font-family:ui-monospace,monospace; margin-right:4px; }
a { color:#0f172a; text-decoration:none; }
a:hover { text-decoration:underline; }
.note { font-size:12.5px; color:#64748b; }
""".strip()


def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def month_chart(y, months):
    series = ["movie", "book", "music"]
    maxv = max([max(months[k]) for k in series] + [1])
    W, H, padL, padB = 940, 300, 36, 28
    plotW = W - padL - 10
    plotH = H - padB - 10
    groupW = plotW / 12
    barW = min(20, groupW / (len(series) + 1))
    svg = [f"<svg viewBox='0 0 {W} {H}' width='100%' style='max-width:{W}px'>"]
    svg.append(f"<line x1='{padL}' y1='{H-padB}' x2='{W-6}' y2='{H-padB}' stroke='#cbd5e1'></line>")
    for g in range(5):
        val = maxv * g / 4
        yy = (H - padB) - plotH * g / 4
        svg.append(f"<line x1='{padL}' y1='{yy:.1f}' x2='{W-6}' y2='{yy:.1f}' stroke='#eef2f7'></line>")
        svg.append(f"<text x='{padL-4}' y='{yy+4:.1f}' text-anchor='end' font-size='10' fill='#94a3b8'>{int(round(val))}</text>")
    for i in range(12):
        gx = padL + i * groupW + groupW / 2
        for si, k in enumerate(series):
            v = months[k][i]
            bh = plotH * v / maxv
            bx = gx - (len(series) * barW) / 2 + si * barW
            by = (H - padB) - bh
            svg.append(f"<rect x='{bx:.1f}' y='{by:.1f}' width='{barW-2:.1f}' height='{bh:.1f}' rx='3' fill='{KIND_COLOR[k]}'></rect>")
            if v > 0:
                svg.append(f"<text x='{bx + (barW-2)/2:.1f}' y='{by-4:.1f}' text-anchor='middle' font-size='10' fill='#1e293b'>{v}</text>")
        svg.append(f"<text x='{gx:.1f}' y='{H-padB+16}' text-anchor='middle' font-size='10.5' fill='#475569'>{i+1}</text>")
    lx = padL + 4
    for k in series:
        svg.append(f"<rect x='{lx}' y='{10}' width='11' height='11' rx='2' fill='{KIND_COLOR[k]}'></rect>")
        svg.append(f"<text x='{lx+16}' y='20' font-size='11' fill='#475569'>{KIND_LABEL[k]}</text>")
        lx += 70
    svg.append("</svg>")
    return f"<section><h2>{y} 年月度分布</h2>{''.join(svg)}<p class='note'>柱高为当月标记「看过 / 读过 / 听过」的条目数，按月归并。</p></section>"


def gen_year(y, yd):
    all_dates = [it["date"] for k in yd for it in yd[k] if it.get("date")]
    last_date = max(all_dates) if all_dates else f"{y}-12-31"
    cnt = {k: len(yd[k]) for k in ("book", "movie", "music")}
    tot = sum(cnt.values())

    months = {k: [0] * 12 for k in ("book", "movie", "music")}
    for k in ("book", "movie", "music"):
        for it in yd[k]:
            if it.get("date"):
                try:
                    m = int(it["date"][5:7])
                    if 1 <= m <= 12:
                        months[k][m - 1] += 1
                except ValueError:
                    pass

    cards = (
        f"<div class='cards'>"
        f"<div class='card'><div class='n' style='color:{KIND_COLOR['book']}'>{cnt['book']}</div><div class='l'>读过（书）</div></div>"
        f"<div class='card'><div class='n' style='color:{KIND_COLOR['movie']}'>{cnt['movie']}</div><div class='l'>看过（影视）</div></div>"
        f"<div class='card'><div class='n' style='color:{KIND_COLOR['music']}'>{cnt['music']}</div><div class='l'>听过（音乐）</div></div>"
        f"<div class='card'><div class='n'>{tot}</div><div class='l'>当年合计</div></div>"
        f"</div>"
    )

    chart = month_chart(y, months)

    parts = []
    for k in ("movie", "book", "music"):
        items = sorted(yd[k], key=lambda x: x["date"], reverse=True)
        if not items:
            continue
        lis = []
        for it in items:
            link = f"https://{KIND_DOMAIN[k]}.douban.com/subject/{it['id']}/"
            lis.append(f"<li><span class='dt'>{html.escape(it['date'])}</span> <a href='{link}' target='_blank' rel='noopener'>{html.escape(it['title'])}</a></li>")
        parts.append(f"<h4 style='color:{KIND_COLOR[k]}'>{KIND_LABEL[k]} {len(items)} 条</h4><ul class='items'>{''.join(lis)}</ul>")
    lists = "".join(parts)

    out = f"""<!DOCTYPE html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{y} 年豆瓣回顾（na57）</title>
<style>{STYLE}</style>
</head>
<body><div class='wrap'>
<h1>{y} 年豆瓣回顾</h1>
<div class='sub'>用户：na57（头可乱发型不可断男）· 数据来源：豆瓣收藏列表（看过/读过/听过）· 当年共 {tot} 条</div>
{cards}
{chart}
<section><h2>当年条目明细</h2>
<p class='note'>按类型列出当年标记的记录（标题链接至豆瓣条目），最新在前。</p>
{lists}
</section>
</div></body></html>"""
    os.makedirs(HTML_DIR, exist_ok=True)
    with open(os.path.join(HTML_DIR, f"{y}.html"), "w", encoding="utf-8") as f:
        f.write(out)

    md = f"""---
title: "{y} 年豆瓣回顾"
description: "{y} 年豆瓣足迹：读过 {cnt['book']} 本、看过 {cnt['movie']} 部影视、听过 {cnt['music']} 张唱片。"
date: {last_date}
tags: ["豆瓣"]
---

{y} 年，我在豆瓣（na57 / 头可乱发型不可断男）上**读过 {cnt['book']} 本书、看过 {cnt['movie']} 部影视、听过 {cnt['music']} 张唱片**，合计 {tot} 条。

下面是这一年的完整回顾（月度分布图 + 条目明细）：

[▶ 打开 {y} 年豆瓣回顾（独立页面）](/douban-reviews/{y}.html)

<iframe src="/douban-reviews/{y}.html" width="100%" height="900" onload="try{{this.style.height=(this.contentWindow.document.body.scrollHeight+40)+'px'}}catch(e){{}}" style="border:1px solid #e2e8f0;border-radius:12px;" loading="lazy"></iframe>

> 这份回顾由豆瓣收藏列表自动汇总生成。
"""
    with open(os.path.join(MD_DIR, f"douban-{y}.md"), "w", encoding="utf-8") as f:
        f.write(md)


def build():
    data = load()
    years = {}
    for kind, items in data.items():
        for it in items:
            y = it["date"][:4]
            years.setdefault(y, {"movie": [], "book": [], "music": []})[kind].append(it)
    ylist = sorted(years.keys())
    for y in ylist:
        gen_year(y, years[y])
    print(f"generated {len(ylist)} year pages: {ylist[0]}..{ylist[-1]}")


if __name__ == "__main__":
    build()
