"""RAG Agent for PE knowledge base Q&A"""
import os
import sys
import time
import uuid
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rag_service.rag.embedder import embed_query, embed_texts
from rag_service.rag.vector_store import get_client as get_qdrant, DEFAULT_COLLECTION
from rag_service.agent.llm import chat, chat_with_history, get_client
from rag_service.models.db import insert_chat_log, get_accessible_doc_ids

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION)

DEFAULT_TOP_K = 5
MAX_CONTEXT_CHUNKS = 10
MAX_CONTEXT_LEN = 8000  # Approximate max chars for context


@dataclass
class RetrievedChunk:
    document_id: str
    title: str
    content: str
    score: float
    path: str


@dataclass
class Citation:
    title: str
    chunk_content: str
    document_id: str
    score: float = 0.0


class RAGAgent:
    """RAG Agent for knowledge base Q&A"""

    def __init__(
        self,
        collection: str = QDRANT_COLLECTION,
        top_k: int = DEFAULT_TOP_K,
        qdrant_url: str = None,
    ):
        self.qdrant = get_qdrant(qdrant_url)
        self.collection = collection
        self.top_k = top_k

    def retrieve(self, query: str, filters: dict = None, doc_ids: List[str] = None) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks from vector store.

        Args:
            query: User question
            filters: Optional Qdrant filter conditions
            doc_ids: Optional list of document_ids to restrict search

        Returns:
            List of RetrievedChunk
        """
        # Embed the query
        query_embedding = embed_query(query)

        # Build filter using qdrant models
        from qdrant_client.http.models import Filter, FieldCondition, MatchAny

        must_conditions = []
        if filters:
            must_conditions.append(filters)
        if doc_ids:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=doc_ids)
                )
            )

        filter_condition = Filter(must=must_conditions) if must_conditions else None

        # Search Qdrant (using query_points API)
        results = self.qdrant.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=self.top_k,
            query_filter=filter_condition,
            with_payload=True,
        ).points

        chunks = []
        for result in results:
            payload = result.payload or {}
            chunks.append(RetrievedChunk(
                document_id=payload.get("document_id", ""),
                title=payload.get("title", "Unknown"),
                content=payload.get("content", ""),
                score=result.score,
                path=payload.get("path", ""),
            ))

        return chunks

    def build_context(self, chunks: List[RetrievedChunk], max_chunks: int = MAX_CONTEXT_CHUNKS) -> Tuple[str, List[Citation]]:
        """
        Build context string from retrieved chunks.

        Returns:
            (context_string, citations)
        """
        citations = []
        context_parts = []
        total_len = 0

        for i, chunk in enumerate(chunks[:max_chunks]):
            # Truncate very long chunks
            content = chunk.content
            if len(content) > 1500:
                content = content[:1500] + "..."

            citations.append(Citation(
                title=chunk.title,
                chunk_content=content,
                document_id=chunk.document_id,
                score=chunk.score,
            ))

            part = f"【文档 {i+1}】{chunk.title}\n{content}\n"
            if total_len + len(part) <= MAX_CONTEXT_LEN:
                context_parts.append(part)
                total_len += len(part)

        context = "\n---\n".join(context_parts)
        return context, citations

    def answer(
        self,
        question: str,
        user_open_id: str = None,
        doc_ids: List[str] = None,
        session_id: str = None,
        user_name: str = None,
    ) -> dict:
        """
        Answer a user question using RAG.

        Args:
            question: User question
            user_open_id: Optional user ID for permission filtering
            doc_ids: Optional explicit document IDs to search
            session_id: Optional session ID for chat logging
            user_name: Optional user name for chat logging

        Returns:
            dict with keys: answer, chunks, citations, latency_ms
        """
        start_time = time.time()

        # 1. Retrieve relevant chunks
        # If no doc_ids provided, get accessible docs for user
        if not doc_ids and user_open_id:
            doc_ids = get_accessible_doc_ids(user_open_id)
            if not doc_ids:
                return {
                    "answer": "抱歉，您没有权限访问任何知识库文档。",
                    "chunks": [],
                    "citations": [],
                    "latency_ms": int((time.time() - start_time) * 1000),
                }

        chunks = self.retrieve(question, doc_ids=doc_ids if doc_ids else None)

        if not chunks:
            return {
                "answer": "抱歉，没有找到与您问题相关的知识库内容。",
                "chunks": [],
                "citations": [],
                "latency_ms": int((time.time() - start_time) * 1000),
            }

        # 2. Build context
        context, citations = self.build_context(chunks)

        # 3. Build prompt
        system_prompt = """你是一个专业的私募基金知识助手，基于提供的上下文知识回答用户问题。

回答格式规范：
1. 用户问数字/结果时，第一句直接给出答案，不要先说"根据..."或"从上下文中..."
2. 结构化数据用Markdown表格呈现，减少纯文本罗列
3. 使用## 标题分隔不同主题，最多不超过3个section
4. 风险提示融入正文末尾一句话，不单独加emoji标签
5. 引用文档信息放在回答最下方，不显眼的位置，用"（来源: 文档名)"格式
6. 严格基于上下文回答，不添加外部信息

请根据以下上下文回答用户问题：
"""
        user_prompt = f"上下文知识：\n{context}\n\n用户问题：{question}"

        # 4. Generate answer
        answer = chat_with_history(
            system_prompt=system_prompt,
            user_question=user_prompt,
            temperature=0.3,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # 5. Log chat
        if session_id and user_open_id:
            try:
                insert_chat_log(
                    session_id=session_id,
                    user_open_id=user_open_id,
                    user_name=user_name or "Unknown",
                    question=question,
                    answer=answer,
                    retrieved_chunks=[c.content for c in chunks[:3]],
                    citations=[{"title": c.title, "document_id": c.document_id} for c in citations[:3]],
                    latency_ms=latency_ms,
                    llm_model="MiniMax-M2.7",
                )
            except Exception as e:
                print(f"[WARN] Failed to log chat: {e}")

        return {
            "answer": answer,
            "chunks": [c.content for c in chunks],
            "citations": [{"title": c.title, "document_id": c.document_id, "score": c.score} for c in citations],
            "latency_ms": latency_ms,
        }


# === CLI Interface ===

def main():
    """Simple CLI for testing RAG agent"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG Agent CLI")
    parser.add_argument("question", type=str, help="Your question")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    parser.add_argument("--session-id", type=str, default=None, help="Session ID for chat logging")
    parser.add_argument("--user-id", type=str, default=None, help="User open ID for permission filtering")
    parser.add_argument("--doc-ids", type=str, default=None, help="Comma-separated document IDs to search")

    args = parser.parse_args()

    doc_ids = None
    if args.doc_ids:
        doc_ids = [d.strip() for d in args.doc_ids.split(",")]

    session_id = args.session_id or str(uuid.uuid4())

    agent = RAGAgent(top_k=args.top_k)

    print(f"\n问题: {args.question}\n")
    print("-" * 60)

    result = agent.answer(
        question=args.question,
        user_open_id=args.user_id,
        doc_ids=doc_ids,
        session_id=session_id,
        user_name="cli_user",
    )

    print(f"答案: {result['answer']}\n")
    print(f"检索到 {len(result['chunks'])} 个相关片段")
    print(f"引用文档:")
    for i, cite in enumerate(result['citations'], 1):
        print(f"  [{i}] {cite['title']} (相关度: {cite['score']:.3f})")
    print(f"\n耗时: {result['latency_ms']}ms")


if __name__ == "__main__":
    main()
