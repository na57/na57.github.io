---
title: 折腾了一天半：GitHub Pages 自定义域名的 HTTPS 到底是谁给的
description: 一次 nagu.cc 域名「DNS 检查失败、证书迟迟不签发」的完整排查记录，以及最后那个容易搞混的证书归属问题。
date: 2026-10-07
tags: ["GitHub Pages", "域名", "HTTPS", "踩坑"]
---

## 现象

给博客绑了自己的域名 `nagu.cc`。A 记录按官方文档老老实实指向 GitHub Pages 的四条 IP，`www` 也 CNAME 到了 `na57.github.io`，站点能打开，但仓库的 Settings → Pages 一直挂着一行红字：

> DNS check unsuccessful — Domain's DNS record could not be retrieved (InvalidDNSError)

点 "Check again"，还是这句。证书一直没签发，浏览器访问提示"不安全"。

## 排查：DNS 从头到尾都是对的

我把能怀疑的地方全查了一遍：

- 本地、`8.8.8.8`、`9.9.9.9`（Quad9，会做 DNSSEC 校验）、两个 DoH 解析器、两个权威 NS —— 六路查询结果完全一致，都是那四条 GitHub IP；
- `www` 的 CNAME 是 `na57.github.io.`，没有被域名商拼成 `na57.github.io.nagu.cc.` 那种坑；
- 没有 CAA 记录，没开 DNSSEC，没有通配符记录；
- 名下所有开了 Pages 的仓库都查了，没有别人占用这个域名；
- whois 状态 ACTIVE，没有 hold。

结论很清楚：**DNS 没有任何问题。**

## 我试过的，都没用

按网上能找到的办法，挨个试：

1. **删掉 apex 的 AAAA 记录**，只留 A（官方文档里 AAAA 本来就是可选项）—— 没用；
2. **反复点 Check again** —— 没用；
3. **摘掉自定义域名再重新挂上** —— 没用（社区说中间要隔 5～10 分钟让缓存清掉，当时只隔了 40 秒，等于白做）；
4. **提工单** —— 秒关。回信说该账号可用的支持资源只有 Community、Docs、Skills 三样自助资源。**Free 账号没有人工工单支持，这条路是死的**；
5. **把 DNS 从 GoDaddy 整个迁到 Cloudflare**（灰云，纯做解析）—— 记录一模一样，报错一模一样。换 DNS 服务商也没用。

期间还有个很讽刺的插曲：GitHub 官方的 "Run a Pages domain health check" 诊断代理跑完告诉我 **"Everything looks good on nagu.cc!"**，而它自家的 Settings 页面坚持说 DNS 检查失败。两个都是 GitHub，结论相反。

## 转折：开了橙色云，证书立刻就有了

最后我把 Cloudflare 的代理打开（橙色云），再访问就是绿锁了。抓下来的证书长这样：

```
Subject: CN = nagu.cc
Issuer:  C = US, O = Let's Encrypt, CN = YE1
SAN:     DNS:*.nagu.cc, DNS:nagu.cc
有效期:  至 2027-01-05
```

注意 SAN 那一行里有 **`*.nagu.cc`**。这就是破案的关键：

- **GitHub Pages 给自定义域签的证书，只覆盖你配置的那个确切主机名**（nagu.cc），不会有通配符；
- **Cloudflare 的 Universal SSL 固定是「apex + 通配」成对出现**。

所以这张证书是 **Cloudflare 签的，不是 GitHub 的**。真实情况是：**GitHub 的证书从头到尾就没签发过**。HTTPS 能用，是因为 Cloudflare 挡在前面，替我签了证、做了 TLS 终结。

三条旁证也对得上：Pages API 里 `https_available` 至今仍是 `null`；`na57.github.io` 的 301 目标仍是 `http://nagu.cc`（它要是真有证书，这里会跳 https）；官方 health check 和 Settings 页面的矛盾至今没消。

## 最后的方案，和一个必须提醒的坑

域名继续放在 Cloudflare，开橙色云代理：

- apex 的 A / AAAA 和 `www` 的 CNAME 全部 Proxied；
- SSL/TLS 加密模式设 **Full**；
- 打开 Always Use HTTPS。

⚠️ **千万别把加密模式切成 Full (strict)。** 源站 GitHub 现在手上只有 `*.github.io` 的通用证书，跟 `nagu.cc` 主机名不匹配，strict 模式下 Cloudflare 校验源站证书会失败，直接给你 **526**。只有等 GitHub 真给你签了域名证书，strict 才成立 —— 而在代理开着的情况下，它永远不会签。

**必须接受的副作用：** GitHub 的 DNS 检查会永久显示失败，Enforce HTTPS 也永远勾不上。因为开了代理之后，GitHub 查 DNS 看到的是 Cloudflare 的 IP 而不是它自己的，这个检查永远不可能通过。这是架构决定的，不是故障，访客侧一切正常。

换个角度看还有个好处：**证书续期从此由 Cloudflare 负责**，不再依赖 GitHub 那条异步流水线的心情。

## 给后来人的几条经验

**一、别信 Settings 的报错文案，也别信 API。** 我的 HTTPS 早就通了，Pages API 里 `https_available` 还是 `null`。直接看证书最准：

```bash
curl -sS -o /dev/null -w '%{certs}' https://你的域名/ | grep -E 'Subject:|DNS:'
```

**二、怎么判断证书是谁签的：** SAN 里有 `*.你的域名` 就是 Cloudflare 的；只有确切主机名才是 GitHub 的。这一眼能省掉一整天的瞎猜。

**三、想要 GitHub 原生发证书，就别开代理**（用灰云），并且要有耐心 —— 它那条流水线是异步的，慢，还可能一直卡住。

**四、等不及就用 Cloudflare 橙色云**，SSL 模式记得是 Full，不是 strict。

**五、Free 账号别浪费时间提工单**，会被自动关闭。

**六、官方那个 health check 值得跑。** 它给的是 GitHub 自己看到的域名状态，虽然这次它和 Settings 页结论相反，但正是这种自相矛盾，反证了问题不在 DNS 上。

**七、别把时间上的先后当成因果关系。** 这次的坑在于：开代理和证书出现几乎同时发生，很容易顺理成章地以为"终于等到了，GitHub 只是慢"。但实际上是 Cloudflare 在发证书。**判断归属要看证据（SAN），不要靠感觉。**
