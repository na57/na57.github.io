---
title: "Roles类的小修改"
description: "Roles类中有一个GetRole(Guid roleID, bool cacheable)方法，此处在找不到角色的时候抛出了一个异常 throw new CSException(CSExceptionType.ResourceNotFound, \"Role not found: \" + roleID.ToString());此处异常类型为ResourceNotFound，应该改成RoleNotF..."
date: 2006-04-11
redirect: "https://www.cnblogs.com/na57/archive/2006/04/11/372030.html"
tags: ["博客园"]
archive: true
---

> 本文发布于博客园，正在跳转到原文…
