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
  }),
});

export const collections = { blog };
