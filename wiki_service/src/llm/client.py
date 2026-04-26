"""LLM client - abstraction over multiple LLM providers"""
import os
from abc import ABC, abstractmethod
from typing import Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    def generate(self, system: str, user_message: str, max_tokens: int = 4096, temperature: float = 0.3) -> str:
        pass

    @abstractmethod
    def generate_with_history(self, system: str, messages: list[dict], max_tokens: int = 4096, temperature: float = 0.3) -> str:
        pass


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API client"""

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-6"):
        if not HAS_ANTHROPIC:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(self, system: str = "", user_message: str = "", max_tokens: int = 4096, temperature: float = 0.3) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def generate_with_history(self, system: str = "", messages: list[dict] = None, max_tokens: int = 4096, temperature: float = 0.3) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages or [],
        )
        return response.content[0].text


class MiniMaxClient(BaseLLMClient):
    """MiniMax API client (compatible interface)"""

    def __init__(self, api_key: str = None, model: str = "abab6.5s"):
        import requests
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.model = model
        self.base_url = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1")

    def generate(self, system: str = "", user_message: str = "", max_tokens: int = 4096, temperature: float = 0.3) -> str:
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_message}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = requests.post(f"{self.base_url}/text/chatcompletion_v2", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def generate_with_history(self, system: str = "", messages: list[dict] = None, max_tokens: int = 4096, temperature: float = 0.3) -> str:
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        all_messages = [{"role": "system", "content": system}] if system else []
        all_messages.extend(messages or [])
        payload = {
            "model": self.model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = requests.post(f"{self.base_url}/text/chatcompletion_v2", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def get_llm_client(provider: str = None) -> BaseLLMClient:
    """Factory function to get LLM client based on provider or env"""
    if provider == "minimax":
        return MiniMaxClient()
    if provider == "claude" or os.getenv("CLAUDE_API_KEY"):
        return ClaudeClient()
    if os.getenv("MINIMAX_API_KEY"):
        return MiniMaxClient()
    # Default to Claude
    return ClaudeClient()