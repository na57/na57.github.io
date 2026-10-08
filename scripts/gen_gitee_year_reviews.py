#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Gitee 年度工作回顾（与 GitHub 版同构，使用 Gitee 橙色主题）。

数据来源：Gitee Open API（commits / pulls），优先读 /tmp/gitee_commits.jsonl（由
`bash scripts/fetch_gitee_data.sh` 预取），缺失时自动用 curl 实时拉取。
输出：public/gitee-reviews/YYYY.html + src/content/blog/gitee-YYYY.md
用法：python3 scripts/gen_gitee_year_reviews.py
"""
import json, html, datetime, collections, subprocess, os

WS = '/Users/na57/workshop/na57.github.io'
OUT_HTML_DIR = os.path.join(WS, 'public', 'gitee-reviews')
OUT_MD_DIR = os.path.join(WS, 'src', 'content', 'blog')
os.makedirs(OUT_HTML_DIR, exist_ok=True)

API = 'https://gitee.com/api/v5'

def curl(url):
    try:
        r = subprocess.run(['curl', '-sS', '--max-time', '30', '-A', 'Mozilla/5.0', url],
                          capture_output=True, text=True)
        return r.stdout
    except Exception:
        return ''

def load_tolerant(fn):
    out = []
    if not os.path.exists(fn):
        return out
    with open(fn) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                i = line.rfind('{"date"')
                if i == -1:
                    continue
                try:
                    d = json.loads(line[i:])
                except Exception:
                    continue
            if 'date' not in d or 'repo' not in d:
                continue
            out.append(d)
    return out

def fetch_entries():
    """返回 (entries, repos)。优先用预取的 JSONL，否则实时拉取。"""
    commits = [dict(d, type='commit') for d in load_tolerant('/tmp/gitee_commits.jsonl')]
    prs = [dict(d, type='pr') for d in load_tolerant('/tmp/gitee_prs.jsonl')]
    if commits or prs:
        return commits + prs, None

    repos_raw = curl(f'{API}/users/na57/repos?per_page=100&page=1')
    try:
        repos = json.loads(repos_raw, strict=False)
    except Exception:
        repos = []
    entries = []
    for r in repos:
        full = r['full_name']
        page = 1
        while True:
            raw = curl(f'{API}/repos/{full}/commits?author=na57&per_page=100&page={page}')
            if not raw.strip():
                break
            try:
                data = json.loads(raw, strict=False)
            except Exception:
                break
            if not isinstance(data, list) or not data:
                break
            for c in data:
                com = c.get('commit', {})
                au = com.get('author', {})
                msg = (com.get('message', '') or '').splitlines()[0]
                entries.append({
                    'date': (au.get('date') or '')[:10],
                    'repo': full, 'type': 'commit',
                    'msg': msg, 'sha': (c.get('sha') or '')[:8],
                    'url': c.get('html_url', ''),
                })
            if len(data) < 100:
                break
            page += 1
        praw = curl(f'{API}/repos/{full}/pulls?state=all&author=na57&per_page=100')
        try:
            pdata = json.loads(praw, strict=False)
        except Exception:
            pdata = []
        if isinstance(pdata, list):
            for p in pdata:
                entries.append({
                    'date': (p.get('created_at') or '')[:10],
                    'repo': full, 'type': 'pr',
                    'msg': p.get('title', ''), 'sha': '',
                    'url': p.get('html_url', ''),
                })
    return entries, repos

entries, _repos = fetch_entries()

# ---- 仓库元信息：静态兜底 + 实时 API 取描述 ----
REPO_FALLBACK = {
    'ynu-itc/ris-wxapp': {'description': '堡垒机小屏小程序（ynu-itc 组织仓库）', 'isFork': False},
}
repoinfo = dict(REPO_FALLBACK)
for full in sorted({e['repo'] for e in entries}):
    live = None
    try:
        live = json.loads(curl(f'{API}/repos/{full}'), strict=False)
    except Exception:
        live = None
    if isinstance(live, dict):
        desc = live.get('description') or live.get('human_name') or live.get('name') or ''
        repoinfo.setdefault(full, {'description': desc, 'isFork': bool(live.get('fork'))})

def yr(d): return d['date'][:4]
def ym(d): return d['date'][:7]
def esc(s): return html.escape(str(s))

def fork_label(r):
    info = repoinfo.get(r)
    if info is None:
        return '外部'
    return '是' if info.get('isFork') else '否'

all_years = sorted({yr(e) for e in entries})
years = [y for y in all_years if y != '2026']
print('目标年份:', years)

CSS = """* { box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
  margin:0; background:#f6f8fa; color:#1e293b; line-height:1.6; }
.wrap { max-width:1000px; margin:0 auto; padding:32px 24px 80px; }
h1 { font-size:26px; margin:0 0 4px; }
.sub { color:#64748b; margin-bottom:24px; font-size:14px; }
.cards { display:flex; flex-wrap:wrap; gap:12px; margin:20px 0 28px; }
.card { background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:14px 18px; min-width:120px; flex:1; }
.card .n { font-size:24px; font-weight:700; color:#ea580c; }
.card .l { font-size:12px; color:#64748b; }
section { background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:20px 22px; margin:18px 0; }
h2 { font-size:19px; margin:0 0 14px; border-left:4px solid #f97316; padding-left:10px; }
table { width:100%; border-collapse:collapse; font-size:13.5px; }
th,td { text-align:left; padding:7px 10px; border-bottom:1px solid #eef2f7; vertical-align:top; }
th { background:#fff7ed; font-weight:600; color:#9a3412; }
td.c, th.c { text-align:center; white-space:nowrap; }
.rname { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px; color:#0f172a; }
.desc { color:#64748b; font-size:13px; margin:6px 0 12px; }
details.proj { border:1px solid #eef2f7; border-radius:8px; padding:10px 14px; margin:8px 0; background:#fffaf5; }
summary { cursor:pointer; font-size:14px; }
.mini { width:auto; }
.mini th, .mini td { padding:4px 12px; }
.items { font-size:13px; }
.items li { margin:3px 0; }
.cm { background:#ffedd5; color:#c2410c; padding:1px 6px; border-radius:4px; font-size:11px; }
.pr { background:#dcfce7; color:#15803d; padding:1px 6px; border-radius:4px; font-size:11px; }
.dt { color:#94a3b8; font-size:12px; font-family:ui-monospace,monospace; }
.note { font-size:12.5px; color:#64748b; }
code { background:#f1f5f9; padding:1px 5px; border-radius:4px; font-size:12px; }
ul.empty { font-size:13px; color:#64748b; }"""

def build_year_html(year):
    ye = [e for e in entries if yr(e) == year]
    by_repo = collections.defaultdict(lambda: {'commit': 0, 'pr': 0, 'months': collections.Counter(), 'items': []})
    month_counts = {f'{year}-{m:02d}': 0 for m in range(1, 13)}
    for e in ye:
        r = e['repo']; m = ym(e)
        rec = by_repo[r]
        if e['type'] == 'commit':
            rec['commit'] += 1
        else:
            rec['pr'] += 1
        rec['months'][m] += 1
        rec['items'].append((e['date'], e['type'], e['msg'], e.get('url', '')))
        if m in month_counts:
            month_counts[m] += 1

    n_commit = sum(1 for e in ye if e['type'] == 'commit')
    n_pr = sum(1 for e in ye if e['type'] == 'pr')
    repos_active = sorted(by_repo.keys())
    months_active = sum(1 for c in month_counts.values() if c > 0)
    all_d = [e['date'] for e in ye]
    first, last = min(all_d), max(all_d)

    maxm = max(month_counts.values()) or 1
    chart_w, chart_h = 920, 240
    bw = chart_w / 12 * 0.62
    gap = chart_w / 12 * 0.38
    bars = []
    for i, m in enumerate(sorted(month_counts)):
        v = month_counts[m]
        h = (v / maxm) * (chart_h - 40) if v else 0
        x = i * (bw + gap) + 8
        lbl = m[5:]
        bars.append(
            f"<g><rect x='{x:.1f}' y='{chart_h-h-20:.1f}' width='{bw:.1f}' height='{h:.1f}' rx='3' fill='#f97316'></rect>"
            f"<text x='{x+bw/2:.1f}' y='{chart_h-6:.1f}' text-anchor='middle' font-size='11' fill='#475569'>{lbl}</text>"
            + (f"<text x='{x+bw/2:.1f}' y='{chart_h-h-25:.1f}' text-anchor='middle' font-size='11' fill='#1e293b'>{v}</text>" if v else "")
            + "</g>")
    chart_svg = (f"<svg viewBox='0 0 {chart_w} {chart_h}' width='100%' style='max-width:920px'>"
                 f"<line x1='8' y1='{chart_h-20}' x2='{chart_w}' y2='{chart_h-20}' stroke='#cbd5e1'></line>"
                 + ''.join(bars) + "</svg>")

    repo_rows = []
    for r in sorted(repos_active, key=lambda x: -(by_repo[x]['commit'] + by_repo[x]['pr'])):
        rec = by_repo[r]
        info = repoinfo.get(r, {})
        repo_rows.append(
            f"<tr><td class='rname'>{esc(r)}</td><td>{esc(info.get('description') or '—')}</td>"
            f"<td class='c'>{rec['commit']}</td><td class='c'>{rec['pr']}</td>"
            f"<td class='c'>{len(rec['months'])}</td><td class='c'>{fork_label(r)}</td></tr>")

    def proj_detail(r):
        rec = by_repo[r]
        if r not in repoinfo:
            fl = '（他人仓库，通过 PR 贡献）'
        elif repoinfo[r].get('isFork'):
            fl = '（fork，仅统计本人提交）'
        else:
            fl = ''
        ms = sorted(rec['months'])
        md = ''.join(f"<tr><td class='c'>{m}</td><td class='c'>{rec['months'][m]}</td></tr>" for m in ms)
        items = sorted(rec['items'], key=lambda x: x[0], reverse=True)
        lis = []
        for dt, typ, msg, url in items:
            tag = "<span class='pr'>PR</span>" if typ == 'pr' else "<span class='cm'>提交</span>"
            link = ''
            if url:
                short = url.split('/')[-1][:8]
                link = f" <a href='{esc(url)}' target='_blank' rel='noopener'>#{esc(short)}</a>"
            lis.append(f"<li>{tag} <span class='dt'>{esc(dt)}</span> {esc(msg)}{link}</li>")
        return (f"<details class='proj'><summary><b>{esc(r)}</b> {fl} — 提交 {rec['commit']} · PR {rec['pr']} · 活跃 {len(ms)} 个月</summary>"
                f"<p class='desc'>{esc(repoinfo.get(r, {}).get('description') or '—')}</p>"
                f"<h4>月度分布</h4><table class='mini'><tr><th>月份</th><th>次数</th></tr>{md}</table>"
                f"<h4>明细（{len(items)} 条，时间倒序）</h4><ul class='items'>{''.join(lis)}</ul></details>")

    proj_details = ''.join(proj_detail(r) for r in sorted(repos_active, key=lambda x: -(by_repo[x]['commit'] + by_repo[x]['pr'])))

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    top3 = [r for r in sorted(repos_active, key=lambda x: -(by_repo[x]['commit'] + by_repo[x]['pr']))][:3]
    top3_s = '、'.join(f"<code>{esc(r)}</code>" for r in top3)

    body = f"""<div class='wrap'>
<h1>{year} 年 Gitee 工作回顾</h1>
<div class='sub'>数据来源：Gitee Open API（提交 + 本人发起的 PR）· 生成于 {now}</div>
<div class='cards'>
  <div class='card'><div class='n'>{n_commit}</div><div class='l'>提交数</div></div>
  <div class='card'><div class='n'>{n_pr}</div><div class='l'>PR 数</div></div>
  <div class='card'><div class='n'>{len(repos_active)}</div><div class='l'>活跃仓库</div></div>
  <div class='card'><div class='n'>{months_active}</div><div class='l'>活跃月份</div></div>
  <div class='card'><div class='n'>{first} ~ {last}</div><div class='l'>起止日期</div></div>
</div>
<section><h2>月度活跃度</h2>{chart_svg}
<p class='note'>柱高为当月「提交数 + PR 数」合计。</p></section>
<section><h2>按项目总结</h2>
<table><tr><th>项目</th><th>描述</th><th>提交</th><th>PR</th><th>活跃月</th><th>fork</th></tr>{''.join(repo_rows)}</table>
<p class='note'>各项目可展开明细：</p>{proj_details}</section>
<section><h2>说明与口径</h2>
<ul class='empty'>
  <li><b>提交</b>：统计 na57 在该仓库的全部提交（Gitee 组织仓库 ynu-itc/ris-wxapp）。</li>
  <li><b>PR/MR</b>：<code>author=na57</code> 发起的 Pull Request（本仓库 {n_pr} 个）。</li>
  <li><b>数据来源</b>：Gitee Open API（<code>/repos/{{owner}}/{{repo}}/commits</code> 与 <code>/pulls</code>）。</li>
</ul></section>
</div>"""

    doc = (f"<!DOCTYPE html>\n<html lang='zh-CN'>\n<head>\n<meta charset='utf-8'>\n"
           f"<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
           f"<title>{year} 年 Gitee 工作回顾</title>\n<style>{CSS}</style>\n</head>\n<body>"
           + body + "\n</body>\n</html>")
    return doc, {
        'n_commit': n_commit, 'n_pr': n_pr, 'repos': len(repos_active),
        'months': months_active, 'top3': top3, 'items': len(ye),
        'projects': len(repos_active), 'first': first, 'last': last,
    }

def build_year_md(year, s, height):
    top3_s = '、'.join(f"`{r}`" for r in s['top3']) or '（该年公开活动较少）'
    intro = (f"这一年（{year}）在 Gitee 上共有 **{s['n_commit']} 次提交**、**{s['n_pr']} 个 PR**，"
             f"涉及 **{s['repos']} 个仓库**，活跃 **{s['months']} 个月**（{s['first']} ~ {s['last']}）。"
             f"主要投入在 {top3_s} 等仓库。")
    desc = f"{year} 年 Gitee 工作回顾：{s['n_commit']} 次提交、{s['n_pr']} 个 PR，涉及 {s['repos']} 个仓库。"
    md = f"""---
title: "{year} 年 Gitee 工作回顾"
description: "{desc}"
date: {year}-12-31
tags: ["Gitee"]
---

{intro}

下面是这一年的完整工作回顾（按项目、按月整理的提交与 PR 明细，含图表）：

[▶ 打开 {year} 年 Gitee 工作回顾（独立页面）](/gitee-reviews/{year}.html)

<iframe src="/gitee-reviews/{year}.html" width="100%" height="{height}" style="border:1px solid #e2e8f0;border-radius:12px;" loading="lazy"></iframe>

> 这份回顾由 Gitee 提交记录与 PR 自动汇总生成；组织仓库统计 na57 的全部提交。
"""
    return md

for year in years:
    doc, s = build_year_html(year)
    html_path = os.path.join(OUT_HTML_DIR, f'{year}.html')
    with open(html_path, 'w') as f:
        f.write(doc)
    height = max(900, 520 + s['items'] * 26 + s['projects'] * 170)
    md = build_year_md(year, s, height)
    md_path = os.path.join(OUT_MD_DIR, f'gitee-{year}.md')
    with open(md_path, 'w') as f:
        f.write(md)
    print(f'{year}: html {len(doc)}B | md -> {os.path.basename(md_path)} | C={s["n_commit"]} P={s["n_pr"]} repos={s["repos"]}')

print('DONE')
