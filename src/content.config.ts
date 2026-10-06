import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// 博客文章集合：源文件放在 src/content/blog/ 下，文件名即 URL slug
const blog = defineCollection({
  loader: glob({ pattern: '**/[^_]*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
    // 链接型文章：填写后访问该 URL 会立即跳转到外部原文（用于聚合公众号等已有文章）
    redirect: z.string().optional(),
    // 多链接入口：填写后文章页会渲染成「选择链接」落地页，由用户自行挑选
    // （例如同一篇同时有图文课件 + 视频链接）。与 redirect 互斥：有 redirect 时本字段不生效。
    links: z
      .array(
        z.object({
          label: z.string(), // 按钮文案，如「图文课件」「视频链接」
          url: z.string(), // 外链地址
          desc: z.string().optional(), // 可选的补充说明
        })
      )
      .optional(),
  }),
});

export const collections = { blog };
