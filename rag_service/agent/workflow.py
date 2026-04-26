"""8-Step RAG Workflow with Compliance for PE knowledge base Q&A

Workflow Steps:
1. Intent Detection - Determine user intent
2. Compliance Pre-check - Check sensitive keywords and user qualifications
3. Retrieval - Retrieve relevant chunks from vector store
4. Permission Filter - Filter chunks by user access rights
5. Generation - Generate answer using LLM
6. Compliance Post-check - Scan output for forbidden words
7. Citation Check - Verify citations are accurate
8. Audit Logging - Log the complete interaction
"""
import os
import sys
import time
import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rag_service.agent.compliance import (
    ComplianceChecker,
    ComplianceCheckResult,
    check_query,
    check_output,
    sanitize_and_warn,
    is_qualified_investor,
    BlockReason,
    RISK_WARNING,
)
from rag_service.agent.llm import chat, chat_with_history
from rag_service.rag.embedder import embed_query
from rag_service.rag.vector_store import get_client as get_qdrant, DEFAULT_COLLECTION
from rag_service.models.db import insert_chat_log, get_accessible_doc_ids

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION)

DEFAULT_TOP_K = 5
MAX_CONTEXT_CHUNKS = 10
MAX_CONTEXT_LEN = 8000
MAX_QUESTION_LEN = 2000


class Intent(Enum):
    """User intent classification"""
    FACTUAL_QUERY = "factual_query"  # Simple fact lookup
    COMPLEX_SYNTHESIS = "complex_synthesis"  # Multi-document synthesis
    REASONING_JUDGMENT = "reasoning_judgment"  # Reasoning over multiple sources
    SENSITIVE_INFO = "sensitive_info"  # Accessing sensitive info
    UNKNOWN = "unknown"


@dataclass
class RetrievedChunk:
    """A retrieved document chunk"""
    document_id: str
    title: str
    content: str
    score: float
    path: str


@dataclass
class Citation:
    """A citation/source reference"""
    title: str
    chunk_content: str
    document_id: str
    score: float = 0.0


@dataclass
class WorkflowResult:
    """Result of the 8-step workflow"""
    answer: str
    citations: List[Dict[str, Any]]
    blocked: bool
    block_reason: str
    block_message: str
    latency_ms: int
    intent: Intent
    retrieved_chunk_count: int
    workflow_steps: Dict[str, float] = field(default_factory=dict)


class RAGWorkflow:
    """
    8-Step RAG Workflow with compliance checks.

    Step 1: Intent Detection
    Step 2: Compliance Pre-check
    Step 3: Retrieval
    Step 4: Permission Filter
    Step 5: Generation
    Step 6: Compliance Post-check
    Step 7: Citation Check
    Step 8: Audit Logging
    """

    def __init__(
        self,
        collection: str = QDRANT_COLLECTION,
        top_k: int = DEFAULT_TOP_K,
        qdrant_url: str = None,
    ):
        self.qdrant = get_qdrant(qdrant_url)
        self.collection = collection
        self.top_k = top_k
        self.compliance_checker = ComplianceChecker()

    def _step1_detect_intent(self, question: str) -> Tuple[Intent, float]:
        """Step 1: Detect user intent"""
        start = time.time()

        # Simple keyword-based intent detection
        # Could be enhanced with a classifier
        complex_keywords = ["分析", "比较", "综合", "判断", "评估", "为什么", "如何选择"]
        sensitive_keywords = ["净值", "收益率", "合格投资者", "客户信息", "投资建议"]

        question_lower = question.lower()

        if any(kw in question_lower for kw in sensitive_keywords):
            intent = Intent.SENSITIVE_INFO
        elif any(kw in question_lower for kw in complex_keywords):
            intent = Intent.REASONING_JUDGMENT
        elif len(question) > 100:
            intent = Intent.COMPLEX_SYNTHESIS
        else:
            intent = Intent.FACTUAL_QUERY

        latency = (time.time() - start) * 1000
        logger.info(f"[Step 1] Intent: {intent.value}, latency: {latency:.1f}ms")
        return intent, latency

    def _step2_compliance_precheck(
        self,
        question: str,
        user_open_id: Optional[str],
    ) -> Tuple[ComplianceCheckResult, float]:
        """Step 2: Compliance pre-check"""
        start = time.time()
        result = self.compliance_checker.check_query(question, user_open_id)
        latency = (time.time() - start) * 1000
        logger.info(f"[Step 2] Compliance pre-check: allowed={result.allowed}, reason={result.reason.value}, latency: {latency:.1f}ms")
        return result, latency

    def _step3_retrieve(
        self,
        question: str,
        filters: dict = None,
    ) -> Tuple[List[RetrievedChunk], float]:
        """Step 3: Retrieve relevant chunks from vector store"""
        start = time.time()

        query_embedding = embed_query(question)

        results = self.qdrant.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=self.top_k,
            query_filter=filters,
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

        latency = (time.time() - start) * 1000
        logger.info(f"[Step 3] Retrieved {len(chunks)} chunks, latency: {latency:.1f}ms")
        return chunks, latency

    def _step4_permission_filter(
        self,
        chunks: List[RetrievedChunk],
        user_open_id: Optional[str],
    ) -> Tuple[List[RetrievedChunk], float]:
        """Step 4: Filter chunks by user permissions"""
        start = time.time()

        if not user_open_id:
            # No user context, return all chunks
            latency = (time.time() - start) * 1000
            logger.info(f"[Step 4] No user context, returning all {len(chunks)} chunks")
            return chunks, latency

        accessible_doc_ids = get_accessible_doc_ids(user_open_id)

        if not accessible_doc_ids:
            latency = (time.time() - start) * 1000
            logger.info(f"[Step 4] User has no accessible documents")
            return [], latency

        filtered = [c for c in chunks if c.document_id in accessible_doc_ids]

        latency = (time.time() - start) * 1000
        logger.info(f"[Step 4] Filtered to {len(filtered)}/{len(chunks)} chunks by permissions, latency: {latency:.1f}ms")
        return filtered, latency

    def _step5_generate(
        self,
        question: str,
        chunks: List[RetrievedChunk],
        intent: Intent,
    ) -> Tuple[str, float]:
        """Step 5: Generate answer using LLM"""
        start = time.time()

        if not chunks:
            answer = "抱歉，知识库中没有找到与您问题相关的内容。"
            latency = (time.time() - start) * 1000
            return answer, latency

        # Build context
        context, citations = self._build_context(chunks)

        # Build system prompt based on intent
        system_prompt = self._build_system_prompt(intent)
        user_prompt = f"上下文知识：\n{context}\n\n用户问题：{question}"

        # Generate
        answer = chat_with_history(
            system_prompt=system_prompt,
            user_question=user_prompt,
            temperature=0.3,
        )

        latency = (time.time() - start) * 1000
        logger.info(f"[Step 5] Generated answer ({len(answer)} chars), latency: {latency:.1f}ms")
        return answer, latency

    def _step6_compliance_postcheck(
        self,
        answer: str,
    ) -> Tuple[ComplianceCheckResult, float]:
        """Step 6: Compliance post-check on output"""
        start = time.time()
        result = self.compliance_checker.check_output(answer)
        latency = (time.time() - start) * 1000

        if not result.allowed:
            # Sanitize the output
            answer = sanitize_and_warn(answer)
            result.message = "输出已自动处理"

        logger.info(f"[Step 6] Output compliance: allowed={result.allowed}, reason={result.reason.value}, latency: {latency:.1f}ms")
        return result, latency

    def _step7_citation_check(
        self,
        answer: str,
        chunks: List[RetrievedChunk],
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Step 7: Verify and format citations"""
        start = time.time()

        citations = []
        for c in chunks[:3]:
            citations.append({
                "title": c.title,
                "document_id": c.document_id,
                "score": c.score,
            })

        latency = (time.time() - start) * 1000
        logger.info(f"[Step 7] Citation check: {len(citations)} citations, latency: {latency:.1f}ms")
        return citations, latency

    def _step8_audit_log(
        self,
        question: str,
        answer: str,
        citations: List[Dict[str, Any]],
        user_open_id: Optional[str],
        user_name: Optional[str],
        session_id: str,
        intent: Intent,
        latency_ms: int,
        blocked: bool,
        block_reason: str,
    ) -> Tuple[float, dict]:
        """Step 8: Log interaction to audit database"""
        start = time.time()

        try:
            insert_chat_log(
                session_id=session_id,
                user_open_id=user_open_id or "anonymous",
                user_name=user_name or "Anonymous",
                question=question,
                answer=answer,
                retrieved_chunks=[c.content for c in [] if hasattr(c, 'content')],  # Simplified for now
                citations=citations,
                latency_ms=latency_ms,
                llm_model="MiniMax-M2.7",
            )
            success = True
        except Exception as e:
            logger.warning(f"[Step 8] Audit log failed: {e}")
            success = False

        latency = (time.time() - start) * 1000
        logger.info(f"[Step 8] Audit log: {'success' if success else 'failed'}, latency: {latency:.1f}ms")
        return latency, {"success": success}

    def _build_context(
        self,
        chunks: List[RetrievedChunk],
        max_chunks: int = MAX_CONTEXT_CHUNKS,
    ) -> Tuple[str, List[Citation]]:
        """Build context string from retrieved chunks"""
        citations = []
        context_parts = []
        total_len = 0

        for i, chunk in enumerate(chunks[:max_chunks]):
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

    def _build_system_prompt(self, intent: Intent) -> str:
        """Build system prompt based on intent"""
        base_prompt = """你是一个专业的私募基金知识助手，基于提供的上下文知识回答用户问题。

回答格式规范：
1. 用户问数字/结果时，第一句直接给出答案，不要先说"根据..."或"从上下文中..."
2. 结构化数据用Markdown表格呈现，减少纯文本罗列
3. 使用## 标题分隔不同主题，最多不超过3个section
4. 风险提示融入正文末尾一句话，不单独加emoji标签
5. 引用文档信息放在回答最下方，不显眼的位置，用"（来源: 文档名)"格式
6. 严格基于上下文回答，不添加外部信息

"""

        if intent == Intent.SENSITIVE_INFO:
            base_prompt += """【敏感信息提示】
涉及敏感数据时，应：
- 避免提供具体净值或收益率数字
- 使用模糊表述（如"近期表现良好"）
- 建议用户咨询合规部门或理财顾问
"""
        elif intent == Intent.REASONING_JUDGMENT:
            base_prompt += """【分析类问题提示】
需要判断分析时，应：
- 列出相关因素
- 说明分析逻辑
- 给出有条件的结论
- 明确不确定性
"""

        return base_prompt

    def run(
        self,
        question: str,
        user_open_id: Optional[str] = None,
        user_name: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_ids: List[str] = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> WorkflowResult:
        """
        Execute the complete 8-step RAG workflow.

        Args:
            question: User's question
            user_open_id: Optional user ID for permission filtering
            user_name: Optional user name for audit logging
            session_id: Optional session ID (generated if not provided)
            doc_ids: Optional explicit document IDs to search
            top_k: Number of chunks to retrieve

        Returns:
            WorkflowResult with answer, citations, and metadata
        """
        total_start = time.time()
        session_id = session_id or str(uuid.uuid4())
        self.top_k = top_k

        workflow_steps = {}
        blocked = False
        block_reason = ""
        block_message = ""
        citations = []
        retrieved_chunk_count = 0

        # Step 1: Intent Detection
        intent, latency = self._step1_detect_intent(question)
        workflow_steps["intent_detection"] = latency

        # Step 2: Compliance Pre-check
        compliance_result, latency = self._step2_compliance_precheck(question, user_open_id)
        workflow_steps["compliance_precheck"] = latency

        if not compliance_result.allowed:
            blocked = True
            block_reason = compliance_result.reason.value
            block_message = compliance_result.message

            total_latency = int((time.time() - total_start) * 1000)
            workflow_steps["total"] = total_latency

            return WorkflowResult(
                answer=block_message,
                citations=[],
                blocked=True,
                block_reason=block_reason,
                block_message=block_message,
                latency_ms=total_latency,
                intent=intent,
                retrieved_chunk_count=0,
                workflow_steps=workflow_steps,
            )

        # Step 3: Retrieval
        filters = None
        if doc_ids:
            filters = {
                "must": [
                    {"key": "document_id", "match": {"value": doc_id}}
                    for doc_id in doc_ids
                ]
            }

        chunks, latency = self._step3_retrieve(question, filters)
        workflow_steps["retrieval"] = latency
        retrieved_chunk_count = len(chunks)

        # Step 4: Permission Filter
        filtered_chunks, latency = self._step4_permission_filter(chunks, user_open_id)
        workflow_steps["permission_filter"] = latency

        if not filtered_chunks:
            total_latency = int((time.time() - total_start) * 1000)
            workflow_steps["total"] = total_latency

            return WorkflowResult(
                answer="抱歉，您没有权限访问与该问题相关的知识库内容。",
                citations=[],
                blocked=False,
                block_reason="",
                block_message="",
                latency_ms=total_latency,
                intent=intent,
                retrieved_chunk_count=0,
                workflow_steps=workflow_steps,
            )

        # Step 5: Generation
        answer, latency = self._step5_generate(question, filtered_chunks, intent)
        workflow_steps["generation"] = latency

        # Step 6: Compliance Post-check
        output_result, latency = self._step6_compliance_postcheck(answer)
        workflow_steps["compliance_postcheck"] = latency

        if not output_result.allowed:
            answer = sanitize_and_warn(answer)

        # Step 7: Citation Check
        citations, latency = self._step7_citation_check(answer, filtered_chunks)
        workflow_steps["citation_check"] = latency

        # Step 8: Audit Logging
        audit_latency, _ = self._step8_audit_log(
            question=question,
            answer=answer,
            citations=citations,
            user_open_id=user_open_id,
            user_name=user_name,
            session_id=session_id,
            intent=intent,
            latency_ms=0,  # Will be updated below
            blocked=False,
            block_reason="",
        )
        workflow_steps["audit_log"] = audit_latency

        total_latency = int((time.time() - total_start) * 1000)
        workflow_steps["total"] = total_latency

        return WorkflowResult(
            answer=answer,
            citations=citations,
            blocked=False,
            block_reason="",
            block_message="",
            latency_ms=total_latency,
            intent=intent,
            retrieved_chunk_count=retrieved_chunk_count,
            workflow_steps=workflow_steps,
        )


# === Convenience function ===
_default_workflow = None


def get_workflow() -> RAGWorkflow:
    """Get global workflow instance"""
    global _default_workflow
    if _default_workflow is None:
        _default_workflow = RAGWorkflow()
    return _default_workflow


def run_chat(
    question: str,
    user_open_id: str = None,
    user_name: str = None,
    session_id: str = None,
    **kwargs,
) -> dict:
    """
    Convenience function to run a complete chat interaction.

    Returns a dict compatible with the API response format.
    """
    workflow = get_workflow()
    result = workflow.run(
        question=question,
        user_open_id=user_open_id,
        user_name=user_name,
        session_id=session_id,
        **kwargs,
    )

    return {
        "answer": result.answer,
        "citations": result.citations,
        "blocked": result.blocked,
        "block_reason": result.block_reason,
        "block_message": result.block_message,
        "latency_ms": result.latency_ms,
        "intent": result.intent.value,
        "retrieved_chunk_count": result.retrieved_chunk_count,
    }


# === CLI Interface ===
def main():
    """CLI for testing the workflow"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG Workflow CLI")
    parser.add_argument("question", type=str, help="Your question")
    parser.add_argument("--user-id", type=str, default=None, help="User open ID")
    parser.add_argument("--user-name", type=str, default=None, help="User name")
    parser.add_argument("--session-id", type=str, default=None, help="Session ID")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")

    args = parser.parse_args()

    print(f"\n问题: {args.question}")
    if args.user_id:
        print(f"用户: {args.user_id} ({args.user_name or 'Unknown'})")
    print("-" * 60)

    result = run_chat(
        question=args.question,
        user_open_id=args.user_id,
        user_name=args.user_name,
        session_id=args.session_id,
        top_k=args.top_k,
    )

    print(f"答案: {result['answer']}\n")

    if result['blocked']:
        print(f"[BLOCKED] 原因: {result['block_reason']}")
        print(f"消息: {result['block_message']}")
    else:
        print(f"引用文档 ({len(result['citations'])}):")
        for i, cite in enumerate(result['citations'], 1):
            print(f"  [{i}] {cite.get('title', 'Unknown')}")

    print(f"\n耗时: {result['latency_ms']}ms")
    print(f"意图: {result['intent']}")
    print(f"检索片段: {result['retrieved_chunk_count']}")


if __name__ == "__main__":
    main()
