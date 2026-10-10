---
title: "PIOC 项目 72 个 Trivy 告警清零实录"
description: "PIOC 生产镜像的 Trivy 扫描报了 72 个告警（含 4 个 Next.js RCE 级别 CRITICAL），通过依赖升级、Next 16.3 兼容修复、standalone 镜像精简三步全部清零。"
date: 2026-10-10
tags: ["安全", "Docker", "Next.js", "GitHub Actions"]
---

> 项目：[PIOC（Personal Intelligence Operations Center，个人智慧运行中心）](https://github.com/na57/pioc) — 基于 Next.js 16 + Ant Design v6 的个人数字化管理平台
> 技术栈：Next.js 16 / Node 22 Alpine / Docker / GitHub Actions + Trivy

## 背景

PIOC 的生产镜像推送到 DockerHub 后由 GitHub Actions 触发 Trivy 扫描，Code Scanning 报了 72 个 open 告警，其中 4 个 CRITICAL 都是 Next.js 的 RCE。

| 类别 | 数量 | 位置 |
|---|---|---|
| 项目 npm 依赖 | 52（4 critical / 26 high / 22 medium） | `/app/node_modules` |
| 镜像自带 npm 内部依赖 | 19（10 high / 9 medium） | `/usr/local/lib/node_modules/npm` |
| 基础镜像系统包 | 1（zlib 堆溢出） | alpine 系统库 |

## 修复

**1. 升级运行时依赖**（`package.json`）

- `next` 16.2.6 → 16.3.8（消除全部 4 个 critical）
- `next-auth` → 4.24.15、`mysql2` → 3.24.5、`echarts` → 6.1.0、`js-yaml` → 4.3.2
- `overrides` 提升间接依赖：sharp 0.35.5、nanoid、postcss、browserslist、source-map-js、brace-expansion 等

两个坑：嵌套 override 要用对象写法（`a>b>c` 语法报 EINVALIDTAGNAME）；brace-expansion 有 1.x/5.x 两个实例，须分别定向。

**2. 修 Next 16.3 的类型收紧**

新版要求路由 handler 的 `context.params` 为必填 Promise，导致 18 个路由 35 个 TS 报错。所有路由都经过统一鉴权包装器 `createAppProtectedHandler`，只改这一处签名即全部消除。

```ts
// 修复后：context.params 声明为必填 Promise
return async (request: NextRequest, context: { params: Promise<{ [key: string]: string }> }) => {
  return handler(request, session, context?.params);
}
```

**3. Docker 镜像瘦身（收益最大）**

原问题：生产镜像含完整 node_modules（eslint 等开发依赖也在里面），基础镜像自带 npm 又贡献 19 个告警；原 Dockerfile 手工 `npm pack` 替换 5 个包的 hack 已全部过时。

- `next.config.ts` 启用 `output: "standalone"`，运行时包从 600+ 降到 23 个
- runner 阶段删除自带 npm（`node server.js` 启动，本就不需要）→ 19 个告警归零
- `apk upgrade` 修 zlib；移除旧 hack；沿用非 root 用户

```dockerfile
RUN apk upgrade --no-cache \
    && apk add --no-cache libstdc++ \
    && rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx
COPY --from=builder /app/.next/standalone ./
CMD ["node", "server.js"]
```

**4. 无上游修复的漏洞**

`npm audit` 剩 5 个 high 全在 eslint 开发链的 `braces@3.0.3`（上游无修复，降级 eslint 才是唯一"方案"，不可接受）。它只在开发期运行、不处理用户输入，standalone 后不进入生产镜像，攻击面不存在，告警随之消失。

## 验证

- `npm run build`、`tsc --noEmit` 通过；lint 无新增
- 容器实跑：首页/登录页 200、未登录 API 返回 401 JSON、静态资源 200；删除 npm 后启动正常
- 本地 Docker VM 网络过慢无法完整构建，改用「本地 build standalone + 挂载进官方镜像离线启动」验证运行时，完整构建交给 CI

## 结果

| 指标 | 修复前 | 修复后 |
|---|---|---|
| CRITICAL | 4 | 0 |
| 生产镜像依赖包 | 600+（含开发依赖） | 23（仅运行时） |
| 镜像内 npm | 有（19 个漏洞依赖） | 无 |
| npm audit 运行时漏洞 | 52 项 | 0 |

## 复盘

1. 先分类统计再动手——72 个告警归为三条主线，按「依赖升级 → 镜像精简 → 系统包」推进
2. 间接依赖用 `overrides` 统一治理，不要手工进 node_modules 替换
3. 「无修复版本」先问它是否在攻击路径上：开发期工具不进生产镜像，比强行降级安全
4. 生产镜像最小化：只含运行时、不含包管理器、非 root 运行
5. 框架升级优先找公共根因：35 个报错只改了一个包装器
