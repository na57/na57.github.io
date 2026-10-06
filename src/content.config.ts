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
  }),
});

export const collections = { blog };
