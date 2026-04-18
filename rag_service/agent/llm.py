"""LLM wrapper for PE knowledge base using MiniMax API"""
import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DEFAULT_MODEL = "MiniMax-M2.7"


def get_client() -> OpenAI:
    """Get MiniMax OpenAI-compatible client"""
    return OpenAI(
        api_key=os.getenv("MINIMAX_API_KEY"),
        base_url="https://api.minimaxi.com/v1",
    )


def chat(
    messages: List[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """
    Generate chat completion using MiniMax API.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: LLM model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text response
    """
    client = get_client()

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


def chat_with_history(
    system_prompt: str,
    user_question: str,
    history: List[dict] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
) -> str:
    """
    Generate chat completion with conversation history.
    """
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_question})

    return chat(messages, model=model, temperature=temperature)


if __name__ == "__main__":
    # Quick test
    messages = [
        {"role": "system", "content": "你是专业的私募基金知识助手，严格基于提供的资料回答。"},
        {"role": "user", "content": "私募基金的投资策略有哪些？"}
    ]
    response = chat(messages)
    print(f"Response: {response}")
