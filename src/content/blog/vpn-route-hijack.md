---
title: "同 WiFi 手机能开、Mac 打不开：route get 查出的 VPN 路由劫持"
description: "校内站 dp.ynu.edu.cn 在 Mac 打不开、同 WiFi 手机却正常，最终定位到学校 VPN 客户端用 PINNED 主机路由劫持了域名流量。"
date: 2026-10-12
tags: ["网络排障", "macOS", "VPN", "路由", "TLS"]
---

学校内部门户 `dp.ynu.edu.cn` 在 Mac 上打不开。同事能开，我手机连同一个 WiFi 也能开，只有这台 Mac 不行。

## 先排除本机常见病

DNS 正常、系统代理全关、无全局 IPv6、`nc -vz dp.ynu.edu.cn 443` 也通。一个前提：**校园网内访问校内服务走内网路由，不过公网出口**，所以公网出口 IP 跟这事无关。

## 同 WiFi 手机能开，问题就在本机

手机和 Mac 同一个网段，一个能一个不能，直接排除服务端宕机、WiFi 层 ACL、网段白名单。锁定 Mac 本机。

## TCP 通，但 TLS 断

`openssl s_client -connect dp.ynu.edu.cn:443`：TCP 连上了，TLS 握手阶段被对端 EOF 断开、不返回证书。换个设备访问同一站返回 401（要登录）——说明服务端活着，而且我这台 Mac 的 TLS 客户端没问题（否则外部也会失败）。同一服务器对不同来源 TLS 行为不同，意味着对端按来源做了拦截，且发生在 TLS 层。

## route get 一锤定音

```bash
route get dp.ynu.edu.cn
# interface: utun8
# flags: <...PINNED...>
```

流量没走 Wi‑Fi(`en0`)，被 `utun8` 接管。`PINNED` 是被钉死的主机路由。再看接口：

```bash
ifconfig utun8
# inet6 fd53:414e:4746:4f52:...   隧道地址 10.10.184.5 -> 2.0.0.1
```

那个 IPv6 前缀 `fd53:414e:4746:4f52` 逐字节解码 `41 4e 47 46 4f 52` = `ANGFOR`，正是深信服（Sangfor）的标识。基本锁定：本机常驻着学校的深信服 SSL VPN 客户端，它给这个域名钉了一条 `/32` 路由，把流量塞进隧道。

顺带解释为什么 `scutil --nc list` 是空的、进程里也抓不到常见 VPN 名：它不走 macOS 系统 VPN 框架，用的是自有 tun 驱动加常驻守护，路由是私有的。

## 根因

默认路由还是 `en0`，但这条更具体的 `/32` 优先级更高，只有 `dp.ynu.edu.cn` 的包进了隧道；隧道出口 IP 不在该服务白名单里，于是 TCP 通、TLS 被掐。手机没装这个 VPN，直连，正常。

## 修法

临时（立刻能开）：

```bash
sudo route delete -host 113.55.13.95
route get dp.ynu.edu.cn   # 应回到 interface: en0
```

根治（不再需要这个 VPN 访问别的内网时）：光退出 GUI 或在活动监视器 kill 进程没用，launchd 常驻守护会重建路由。得卸守护：

```bash
launchctl list | grep -i sangfor
sudo launchctl unload /Library/LaunchDaemons/<xxx>.plist
```

如果还得靠它访问别的内网，就配 split tunnel，把 `*.ynu.edu.cn` 排除在隧道外。
