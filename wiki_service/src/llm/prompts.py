"""LLM prompts for wiki operations"""
from datetime import datetime


def build_ingest_prompt(doc_path: str, content: str, category: str, page_type: str) -> str:
    """Build prompt for document ingestion"""
    return f"""你是一个知识库管理员。请仔细阅读以下文档，然后按照规则创建或更新 wiki 页面。

原始文档路径: {doc_path}
文档类型: {category}
建议页面类型: {page_type}

## 原始文档内容
{content[:8000]}

## 你的任务
1. 提取文档中的关键实体（人名、产品名、公司名、术语）
2. 提取核心概念和流程
3. 判断该文档属于哪个类别（entities / concepts / overviews）
4. 生成 wiki 页面内容（使用 [[双向链接]] 引用相关页面）
5. 给出你将创建/更新的页面列表

请以 JSON 格式返回，字段说明：
- "pages": [
    {{
      "title": "页面标题",
      "type": "entity / concept / overview",
      "access": "public / dept-sales / admin",
      "content": "# 页面标题\\n\\n正文内容...",
      "path": "entities/xxx.md 或 concepts/xxx.md 或 overviews/xxx.md"
    }}
  ]
- "index_updates": 建议添加到 index.md 的条目列表
- "related_existing": 建议链接到的已有页面标题列表

只返回 JSON，不要有其他文字。"""


def build_query_prompt(index_content: str, question: str) -> str:
    """Build prompt for finding relevant pages from index"""
    return f"""你是知识库助手。用户提问时，先从索引中找相关页面。

当前索引内容:
{index_content[:5000]}

用户问题: {question}

请从索引中找出与问题最相关的 3~5 个页面，只返回页面标题列表，用逗号分隔。

只返回页面标题列表，其他什么都不要。"""


def build_answer_prompt(wiki_context: str, question: str) -> str:
    """Build prompt for synthesizing answer from wiki pages"""
    return f"""基于以下 wiki 页面内容，回答用户问题。

## Wiki 页面内容
{wiki_context}

## 用户问题
{question}

请综合以上内容给出回答。回答格式要求：
- 给出清晰、结构化的答案
- 引用相关页面（用 [[页面标题]] 格式）
- 标注答案的可信度 (high/medium/low)
- 如果发现知识空白，在回答末尾注明"待补充"

最后以 JSON 格式返回：
{{
  "answer": "综合回答...",
  "confidence": "high/medium/low",
  "cited_pages": ["页面标题1", "页面标题2"]
}}

只返回 JSON。"""


def build_lint_prompt(all_content: str, orphaned: list, broken_links: list) -> str:
    """Build prompt for lint checking"""
    return f"""你是知识库健康检查员。请分析以下 wiki 内容，发现问题。

## Wiki 内容摘要
{all_content[:8000]}

## 已发现的问题
- 孤立页面（未被引用）: {orphaned}
- 断链: {broken_links}

请深入检查以下问题：
1. 矛盾陈述（两个页面说法冲突）
2. 过时内容（明显失效的信息）
3. 页面类型错误（entity 放在 concepts 或反之）
4. 访问级别错误（敏感内容标记为 public）

请以 JSON 格式返回：
{{
  "contradictions": ["矛盾描述1", "矛盾描述2"],
  "stale_pages": ["过时页面标题1"],
  "suggestions": ["优化建议1", "优化建议2"]
}}

如果某项为空，返回空列表。只返回 JSON。"""


def build_sync_report_prompt(stats: dict, failed_docs: list) -> str:
    """Build prompt for sync report generation"""
    return f"""你是飞书同步管理员。请生成同步报告。

## 同步统计
{stats}

## 失败文档
{failed_docs}

请以 JSON 格式返回：
{{
  "report": "同步报告摘要...",
  "success_count": 0,
  "failed_count": 0,
  "tokens_used": 0,
  "cost_estimate_yuan": 0.0
}}

只返回 JSON。"""