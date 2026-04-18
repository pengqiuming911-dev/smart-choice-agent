"""窄路 Demo: 飞书文档直接问答,不做分块不做检索

验证核心链路: 飞书文档 -> LLM 问答
代码目标: < 100 行

依赖:
- pip install dashscope httpx python-dotenv
- .env 中配置 FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_DOC_ID, DASHSCOPE_API_KEY
"""
import os
import sys
import httpx
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
DOC_ID = os.getenv("FEISHU_DOC_ID")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")  # 测试文档的 document_id


def get_tenant_token() -> str:
    """获取飞书 tenant access token"""
    resp = httpx.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=30,
    ).json()
    assert resp.get("code") == 0, f"获取token失败: {resp}"
    return resp["tenant_access_token"]


def fetch_doc_raw(doc_id: str, token: str) -> str:
    """获取飞书文档原始内容"""
    resp = httpx.get(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/raw_content",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ).json()
    if resp.get("code") != 0:
        raise RuntimeError(f"获取文档失败: {resp}")
    return resp["data"]["content"]


def ask(doc_content: str, question: str) -> str:
    """调用 MiniMax 进行问答"""
    client = OpenAI(
        api_key=MINIMAX_API_KEY,
        base_url="https://api.minimaxi.com/v1",
    )
    resp = client.chat.completions.create(
        model="MiniMax-M2.7",
        messages=[
            {
                "role": "system",
                "content": "你是基于文档回答问题的助手。严格基于提供的文档内容回答，不要编造。回答使用中文。",
            },
            {
                "role": "user",
                "content": f"文档内容:\n{doc_content}\n\n问题:{question}",
            },
        ],
        temperature=0.1,
    )
    if not resp.choices:
        raise RuntimeError(f"LLM调用失败: 无返回结果")
    return resp.choices[0].message.content


def main():
    if len(sys.argv) < 2:
        print("用法: python demo.py '<问题>'")
        print("默认问题: 这份文档在讲什么?")
        question = "这份文档在讲什么?"
    else:
        question = sys.argv[1]

    print(f"文档ID: {DOC_ID}")
    print(f"问题: {question}\n")

    token = get_tenant_token()
    print("✓ 飞书token获取成功")

    doc = fetch_doc_raw(DOC_ID, token)
    print(f"✓ 文档获取成功 (长度: {len(doc)} 字)")

    answer = ask(doc, question)
    print(f"回答:\n{answer}")


if __name__ == "__main__":
    main()
