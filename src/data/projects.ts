// 首页侧边栏「我的项目」数据源。
// 稍后把你觉得不错的项目填进来即可，每条格式：
//   { name: string; url: string; desc?: string }
// 留空数组时，侧边栏会显示「（敬请期待）」。
export interface Project {
  name: string;
  url: string;
  desc?: string;
}

export const projects: Project[] = [];
