"""定时任务定义"""
import uuid
from datetime import datetime
from rag_service.scheduler.sender import get_sender
from rag_service.config import settings
from rag_service.rag.embedder import embed_query
from rag_service.rag.vector_store import get_client as get_qdrant
from rag_service.agent.llm import chat_with_history


def build_daily_digest() -> str:
    """
    构建每日行业动态摘要

    基于最新的文档检索生成摘要内容
    """
    try:
        qdrant = get_qdrant()
        sender = get_sender()

        # 1. 检索最新文档内容
        query_embedding = embed_query("行业动态 市场资讯 最新消息")
        results = qdrant.query_points(
            collection_name=settings.qdrant_collection,
            query=query_embedding,
            limit=5,
            with_payload=True,
        ).points

        if not results:
            return "今日暂无最新行业资讯推送。"

        # 2. 构建上下文
        context_parts = []
        for i, point in enumerate(results[:3]):
            payload = point.payload or {}
            content = payload.get("content", "")[:500]  # 限制长度
            title = payload.get("title", "未知文档")
            context_parts.append(f"【{title}】\n{content}")

        context = "\n---\n".join(context_parts)

        # 3. 生成摘要
        system_prompt = """你是一个专业的行业资讯助手，根据检索到的文档内容，生成简洁的行业动态摘要。

要求：
1. 总结 2-3 个最重要的行业动态
2. 每个动态用一句话概括
3. 重点关注：政策变化、市场动态、产品信息
4. 结尾加上风险提示："本摘要仅供参考，不构成投资建议"
5. 总字数控制在 300 字以内
"""
        user_prompt = f"请根据以下文档内容，生成今日行业动态摘要：\n\n{context}"

        summary = chat_with_history(
            system_prompt=system_prompt,
            user_question=user_prompt,
            temperature=0.3,
        )

        return summary

    except Exception as e:
        print(f"[ERROR] Failed to build daily digest: {e}")
        return f"行业动态摘要生成失败，请稍后查看。"


def daily_report_job():
    """每日定时推送任务"""
    sender = get_sender()

    # 构建消息内容
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日 %A")
    greeting = f"【每日行业动态】{date_str}\n\n"

    # 获取摘要内容
    digest = build_daily_digest()

    message = f"{greeting}{digest}"

    # 发送到飞书
    target_open_id = getattr(settings, "scheduler_target_open_id", None)

    if not target_open_id:
        # 如果没有配置，使用默认方式获取（需要先配置）
        print("[WARN] scheduler_target_open_id not configured")
        return

    success = sender.send_message(target_open_id, message)

    if success:
        print(f"[INFO] Daily report sent successfully at {now}")
    else:
        print(f"[ERROR] Failed to send daily report at {now}")


def test_job():
    """测试任务 - 发送测试消息"""
    sender = get_sender()
    target_open_id = getattr(settings, "scheduler_target_open_id", None)

    if not target_open_id:
        print("[ERROR] scheduler_target_open_id not configured")
        return

    test_message = f"【定时推送测试】\n这是一条测试消息，当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    success = sender.send_message(target_open_id, test_message)

    if success:
        print("[INFO] Test message sent successfully")
    else:
        print("[ERROR] Failed to send test message")
