#!/usr/bin/env node
// 把 B站（哔哩哔哩）UP 主「尽量三分钟CS」(UID 199758514) 的视频生成为本地跳转型博客文章（.md，访问即跳原视频）。
//
// 数据源：scripts/bili-articles.json
//   手动维护，结构：
//   [{ "title":"...", "url":"https://www.bilibili.com/video/BVxxxx", "date":"YYYY-MM-DD", "description":"...", "tags":["内容标签"] }]
//
// 用法：
//   node scripts/gen-bili-links.mjs
//   node scripts/gen-bili-links.mjs --from other.json
//   WX_DRY_RUN=1 node scripts/gen-bili-links.mjs   # 只打印不写
//
// 生成的文章统一打标签 "B站"（外加内容标签），并实现幂等：
//   - 同一 redirect URL 已存在则跳过
//   - 同一 slug 已存在则跳过

import { writeFile, mkdir, readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..');
const OUT_DIR = process.env.WX_OUT_DIR
  ? join(REPO_ROOT, process.env.WX_OUT_DIR)
  : join(REPO_ROOT, 'src/content/blog');
const BILI_TAG = process.env.BILI_TAG || 'B站';
const DRY_RUN = process.env.WX_DRY_RUN === '1';

let fromFile = join(REPO_ROOT, 'scripts/bili-articles.json');
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === '--from') fromFile = process.argv[++i];
}

const NAMED = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
function decode(s) {
  return (s || '').replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (m, e) => {
    if (e[0] === '#') {
      const code =
        e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return isNaN(code) ? m : String.fromCodePoint(code);
    }
    return NAMED[e.toLowerCase()] ?? m;
  });
}

function slugify(title, used) {
  let s = decode(title || 'post')
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

function getRedirectFromMd(raw) {
  const m = raw.match(/^redirect:\s*(.+)$/m);
  if (!m) return null;
  try {
    return JSON.parse(m[1].trim());
  } catch {
    return m[1].trim().replace(/^["']|["']$/g, '');
  }
}

async function main() {
  const raw = await readFile(fromFile, 'utf8');
  const articles = JSON.parse(raw)
    .map((o) => ({
      title: decode(o.title),
      url: o.url,
      date: /^\d{4}-\d{2}-\d{2}$/.test(o.date) ? o.date : '2026-01-01',
      description: decode(o.description || ''),
      extraTags: Array.isArray(o.tags) ? o.tags : [],
    }))
    .filter((a) => a.title && a.url);

  console.log(`数据源 ${fromFile} 共 ${articles.length} 篇。`);

  await mkdir(OUT_DIR, { recursive: true });

  const files = (await readdir(OUT_DIR)).filter((f) => f.endsWith('.md'));
  const existingSlugs = new Set(files.map((f) => f.replace(/\.md$/, '')));
  const existingUrls = new Set();
  for (const f of files) {
    const u = getRedirectFromMd(await readFile(join(OUT_DIR, f), 'utf8'));
    if (u) existingUrls.add(u);
  }
  const used = new Set(existingSlugs);

  let written = 0;
  let skipped = 0;
  for (const a of articles) {
    if (existingUrls.has(a.url)) {
      skipped++;
      continue;
    }
    const slug = slugify(a.title, used);
    if (existingSlugs.has(slug)) {
      skipped++;
      continue;
    }
    const allTags = [BILI_TAG, ...a.extraTags];
    const front = [
      '---',
      `title: ${JSON.stringify(a.title)}`,
      `description: ${JSON.stringify(a.description)}`,
      `date: ${a.date}`,
      `redirect: ${JSON.stringify(a.url)}`,
      `tags: [${allTags.map((t) => JSON.stringify(t)).join(', ')}]`,
      '---',
      '',
      '> 本视频发布于哔哩哔哩（B站），正在跳转到原文…',
      '',
    ].join('\n');
    if (DRY_RUN) {
      console.log(`[dry-run] 将写入 ${slug}.md → ${a.url}  tags=${allTags.join(',')}`);
      written++;
      continue;
    }
    await writeFile(join(OUT_DIR, `${slug}.md`), front, 'utf8');
    written++;
  }
  console.log(
    `\n完成：新增 ${written} 篇（固定标签「${BILI_TAG}」+ 内容标签），跳过已存在/重复 ${skipped} 篇。输出目录：${OUT_DIR}`
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
