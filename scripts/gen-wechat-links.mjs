#!/usr/bin/env node
// 把微信公众号文章生成为本地跳转型博客文章（.md，访问即跳原文）。
//
// 两种数据来源：
//   1) 公众号后台 API（需已认证、且账号有 freepublish 权限）
//      WX_APPID=xxx WX_APPSECRET=yyy node scripts/gen-wechat-links.mjs
//   2) 本地清单文件（推荐：从后台「已群发」复制标题+链接+日期）
//      node scripts/gen-wechat-links.mjs --from list.tsv
//      node scripts/gen-wechat-links.mjs --from list.json
//
// 清单格式：
//   - JSON：[{ "title":"...", "url":"https://mp.weixin.qq.com/s/...", "date":"2024-01-01", "description":"..." }]
//   - TSV ：每行 标题<TAB>链接<TAB>日期(可选)<TAB>摘要(可选)，可用「复制/粘贴」从后台表格直接来
//
// 可选环境变量：WX_TAG（默认标签，默认 "公众号"）、WX_DRY_RUN=1（只打印不写）。

import { writeFile, mkdir, readdir } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..');
const OUT_DIR = process.env.WX_OUT_DIR
  ? join(REPO_ROOT, process.env.WX_OUT_DIR)
  : join(REPO_ROOT, 'src/content/blog');
const DEFAULT_TAG = process.env.WX_TAG || '公众号';
const DRY_RUN = process.env.WX_DRY_RUN === '1';

// 解析参数
let fromFile = null;
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === '--from') fromFile = process.argv[++i];
}
const APPID = process.env.WX_APPID;
const APPSECRET = process.env.WX_APPSECRET;

function slugify(title, used) {
  let s = (title || 'post')
    .trim()
    .toLowerCase()
    .replace(/['"]/g, '')
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  if (!s) s = 'post';
  if (s.length > 80) s = s.slice(0, 80).replace(/-+$/, '');
  let base = s;
  let i = 1;
  while (used.has(s)) s = `${base}-${i++}`;
  used.add(s);
  return s;
}

function fmtDate(ts) {
  const d = new Date(ts * 1000);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function normDate(v) {
  if (!v) return fmtDate(Math.floor(Date.now() / 1000));
  v = String(v).trim();
  if (/^\d{9,13}$/.test(v)) return fmtDate(Number(v));
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return v;
  const d = new Date(v);
  if (!isNaN(d.getTime())) return fmtDate(Math.floor(d.getTime() / 1000));
  return fmtDate(Math.floor(Date.now() / 1000));
}

function readLocalList(path) {
  const raw = readFileSync(path, 'utf8').trim();
  if (raw.startsWith('[')) {
    const arr = JSON.parse(raw);
    return arr
      .map((o) => ({
        title: o.title || o.标题,
        url: o.url || o.链接 || o.link,
        date: normDate(o.date || o.日期 || o.发布日期),
        description: o.description || o.desc || o.摘要 || o.描述 || '',
      }))
      .filter((a) => a.title && a.url);
  }
  // TSV：标题 \t 链接 \t 日期(可选) \t 摘要(可选)
  return raw
    .split(/\r?\n/)
    .map((l) => l.split('\t'))
    .filter((c) => c.length >= 2 && c[0].trim() && c[1].trim())
    .map((c) => ({
      title: c[0].trim(),
      url: c[1].trim(),
      date: normDate(c[2]),
      description: (c[3] || '').trim(),
    }));
}

async function getToken() {
  const url = `https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APPID}&secret=${APPSECRET}`;
  const r = await fetch(url);
  const j = await r.json();
  if (!j.access_token) throw new Error('获取 access_token 失败: ' + JSON.stringify(j));
  return j.access_token;
}

async function batchGet(token, offset, count = 20) {
  const url = `https://api.weixin.qq.com/cgi-bin/freepublish/batchget?access_token=${token}`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ offset, count, no_content: 1 }),
  });
  const j = await r.json();
  if (j.errcode) throw new Error('freepublish/batchget 失败: ' + JSON.stringify(j));
  return j;
}

async function collectViaApi() {
  if (!APPID || !APPSECRET) {
    throw new Error('缺少 WX_APPID / WX_APPSECRET，且未提供 --from 清单');
  }
  const token = await getToken();
  const articles = [];
  let offset = 0;
  while (true) {
    const res = await batchGet(token, offset);
    for (const it of res.item || []) {
      const publishTime = it.publish_time;
      for (const art of it.content?.news_item || []) {
        if (!art.url) continue;
        articles.push({
          title: art.title,
          url: art.url,
          date: fmtDate(publishTime || art.update_time),
          description: art.digest || '',
        });
      }
    }
    const itemCount = res.item_count || 0;
    if (itemCount < 20) break;
    offset += itemCount;
    if (offset >= (res.total_count || 0)) break;
  }
  return articles;
}

async function main() {
  const articles = fromFile ? readLocalList(fromFile) : await collectViaApi();
  console.log(`共获取到 ${articles.length} 篇公众号文章。`);

  await mkdir(OUT_DIR, { recursive: true });
  const existing = new Set(
    (await readdir(OUT_DIR)).filter((f) => f.endsWith('.md')).map((f) => f.replace(/\.md$/, ''))
  );
  const used = new Set(existing);
  let written = 0;
  let skipped = 0;
  for (const a of articles) {
    const slug = slugify(a.title, used);
    if (existing.has(slug)) {
      skipped++;
      console.log(`跳过(已存在): ${slug} — ${a.title}`);
      continue;
    }
    const front = [
      '---',
      `title: ${JSON.stringify(a.title)}`,
      `description: ${JSON.stringify(a.description)}`,
      `date: ${a.date}`,
      `redirect: ${JSON.stringify(a.url)}`,
      `tags: [${JSON.stringify(DEFAULT_TAG)}]`,
      '---',
      '',
      '> 本文发布于微信公众号，正在跳转到原文…',
      '',
    ].join('\n');
    if (DRY_RUN) {
      console.log(`[dry-run] 将写入 ${slug}.md → ${a.url}`);
      written++;
      continue;
    }
    await writeFile(join(OUT_DIR, `${slug}.md`), front, 'utf8');
    written++;
    console.log(`写入 ${slug}.md — ${a.title}`);
  }
  console.log(`\n完成：新增 ${written} 篇，跳过已存在 ${skipped} 篇。输出目录：${OUT_DIR}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
