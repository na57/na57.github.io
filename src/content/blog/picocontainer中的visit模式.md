---
title: "PicoContainer中的Visit模式"
description: "在PicoContainer中使用了Visit模式，但他只提供了Visitor接口，没有使用Visitable接口。那么，它怎么提供accept方法呢？ PicoContainer是通过一种“横切”的办法来实现Visitable的在PicoVisitor接口中，有这样一个方法：Object traverse(Object node); 我们来看AbstractPicoVisitor中实现的tr..."
date: 2005-03-16
redirect: "https://www.cnblogs.com/na57/archive/2005/03/16/119483.html"
tags: ["博客园"]
archive: true
---

> 本文发布于博客园，正在跳转到原文…
