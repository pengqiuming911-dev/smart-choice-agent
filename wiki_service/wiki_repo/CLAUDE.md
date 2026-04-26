# 知识库维护规则

## 目录结构
- raw/ : 原始文档，只读，LLM 不得直接修改
- wiki/ : LLM 生成内容，LLM 全权管理
  - entities/ : 实体页（产品、客户、人员、供应商）
  - concepts/ : 概念页（术语、流程、政策、制度）
  - overviews/ : 综合页（月报、季度总结、主题汇总）
  - index.md : 全局目录，所有页面的入口索引
  - log.md : 操作时间日志

## Ingest 流程
1. 阅读 raw/ 下的新文档或更新文档
2. 提取实体（人名、产品名、公司名）
3. 提取关键概念（术语定义、流程步骤）
4. 判断访问级别（public / dept-xxx / admin）
5. 在 wiki/ 创建或更新对应页面
6. 维护反向链接 [[...]]
7. 更新 index.md（新增页面必须加入索引）
8. 在 log.md 追加一行 ingest 记录

## 页面格式约定
每个 wiki 页面以 frontmatter 开头:

```markdown
---
title: 页面标题
type: entity / concept / overview
access: public / dept-sales / dept-tech / admin
sources: [原始文档路径, 飞书文档链接]
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

正文用 markdown，内部引用用 [[页面名]]。

## 访问级别
- public: 全员可见
- dept-sales: 销售部可见
- dept-tech: 技术部可见
- admin: 仅管理员可见

## Query 流程
1. 阅读 index.md，找到与问题最相关的 3~5 个页面
2. 深读这些页面
3. 综合答案，标注引用来源
4. 如果答案有价值且有普遍性，归档为新的 overview 页面
5. 如果发现知识空白，在 log.md 记录"待补充"

## Lint 检查项
- 孤立页面（没有被任何页面引用）
- 断链（[[xxx]] 指向不存在的目标）
- 矛盾陈述（两个页面说法冲突）
- 长期未更新（超过 3 个月无变化）
- 访问级别错误（敏感内容未标注 admin）

## 输出格式约定
query 回答统一返回:

```json
{
  "answer": "综合回答...",
  "wiki_pages": [
    {"title": "页面名", "path": "wiki/entities/xxx.md"}
  ],
  "raw_sources": [
    {"title": "原始文档", "path": "raw/articles/xxx.md"}
  ],
  "confidence": "high / medium / low"
}
```

## 注意事项
- 禁止在 wiki 页面直接引用 raw/ 外部链接，统一用飞书文档链接格式 feishu://docs/xxx
- 禁止在回答中出现"保本"、"稳赚"、"零风险"等违规表述
- 涉及净值、收益率等敏感数据，只引用不解读
- 每次修改 wiki/ 内容后自动 git commit
