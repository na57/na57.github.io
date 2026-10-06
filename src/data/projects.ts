// 首页侧边栏「最近工作」数据源。
// 稍后把你觉得不错的项目填进来即可，每条格式：
//   { name: string; url: string; desc?: string }
// 留空数组时，侧边栏会显示「（敬请期待）」。
export interface Project {
  name: string;
  url: string;
  desc?: string;
}

export const projects: Project[] = [
  {
    name: 'PIOC',
    url: 'https://nagu.cc/pioc',
    desc: '基于 3A（AI Native、AI Powered、All in One）的个人智慧运行中心',
  },
  {
    name: 'Rdb2WeDoc',
    url: 'https://github.com/nagucc/rdb2wedoc',
    desc: '实现关系数据库数据到企业微信文档的同步',
  },
  {
    name: '西拉家谱',
    url: 'http://nagu.cc/blog/假期做了个小东西-把-20-年前的家谱应用重新实现了/',
    desc: '纳氏家谱小程序，用现代技术重新实现 20 年前的家谱应用，方便族人查询与续谱',
  },
  {
    name: '希赛计算器',
    url: 'http://nagu.cc/blog/受够了计算器里的广告-我给大家做了个小程序/',
    desc: '无广告的实用计算器小程序，自己动手解决市面计算器塞广告的痛点',
  },
  {
    name: '高考资料库',
    url: 'https://nagu.cc/gk',
    desc: '面向新高考的备考资料库，按科目系统整理、持续更新的学习资源集合',
  },
  {
    name: '高考知识图谱',
    url: 'https://nagu.cc/os-taxonomy/',
    desc: '用知识图谱梳理高考学科知识体系，把零散考点组织成可导航的结构化地图',
  },
  {
    name: 'CAS RESTful 对接文档',
    url: 'https://nagu.cc/cas-restful-test/',
    desc: '移动端 CAS 认证对接的实战文档与测试样例，沉淀可复用的对接标准与踩坑记录',
  },
];
