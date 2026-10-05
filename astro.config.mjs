import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

// 站点正式上线域名（用于 RSS / sitemap / canonical 的绝对路径）
export default defineConfig({
  site: 'https://nagu.cc',
  integrations: [sitemap()],
  markdown: {
    remarkPlugins: [remarkGfm, remarkMath],
    rehypePlugins: [rehypeKatex],
    shikiConfig: {
      theme: 'github-light',
    },
  },
});
