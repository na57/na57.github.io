#!/usr/bin/env node
// 把 CSDN（ynnwq / 海纳百川技术站）的博文生成为本地跳转型博客文章（.md，访问即跳原文）。
//
// 数据源：scripts/csdn-articles.json
//   结构：[{ "title":"...", "url":"https://blog.csdn.net/ynnwq/article/details/...", "date":"2004-12-19" }]
//
// 用法：
//   node scripts/gen-csdn-links.mjs
//   WX_DRY_RUN=1 node scripts/gen-csdn-links.mjs   # 只打印不写
//
// 生成的文章统一打标签 CSDN_TAG（默认 "CSDN"），并实现幂等（同 slug / 同 redirect 跳过）。
// 注意：「我的编程之路」系列 2 篇已作为完整文章收录（保留正文 + 原文链接），不在此生成。

import { writeFile, mkdir, readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..');
const OUT_DIR = process.env.WX_OUT_DIR
  ? join(REPO_ROOT, process.env.WX_OUT_DIR)
  : join(REPO_ROOT, 'src/content/blog');
const CSDN_TAG = process.env.CSDN_TAG || 'CSDN';
const DRY_RUN = process.env.WX_DRY_RUN === '1';

let fromFile = join(REPO_ROOT, 'scripts/csdn-articles.json');
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === '--from') fromFile = process.argv[++i];
}

function decode(s) {
  return (s || '').replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (m, e) => {
    if (e[0] === '#') {
      const code = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return isNaN(code) ? m : String.fromCodePoint(code);
    }
    const NAMED = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
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
      date: /^\d{4}-\d{2}-\d{2}$/.test(o.date) ? o.date : '2004-12-19',
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
    const front = [
      '---',
      `title: ${JSON.stringify(a.title)}`,
      `description: ""`,
      `date: ${a.date}`,
      `redirect: ${JSON.stringify(a.url)}`,
      `tags: [${JSON.stringify(CSDN_TAG)}]`,
      '---',
      '',
      '> 本文发布于 CSDN 博客（海纳百川技术站），正在跳转到原文…',
      '',
    ].join('\n');
    if (DRY_RUN) {
      console.log(`[dry-run] 将写入 ${slug}.md → ${a.url}`);
      written++;
      continue;
    }
    await writeFile(join(OUT_DIR, `${slug}.md`), front, 'utf8');
    written++;
  }
  console.log(
    `\n完成：新增 ${written} 篇（标签「${CSDN_TAG}」），跳过已存在/重复 ${skipped} 篇。输出目录：${OUT_DIR}`
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
