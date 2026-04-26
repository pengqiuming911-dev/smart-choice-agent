"""Claude API client for wiki_agent"""
import os
from typing import Optional
from pathlib import Path

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class ClaudeClient:
    """Anthropic Claude API client"""

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-7"):
        if not HAS_ANTHROPIC:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY", "")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(
        self,
        system: str = "",
        user_message: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate a response from Claude.

        Args:
            system: System prompt (typically CLAUDE.md content)
            user_message: User message
            max_tokens: Max output tokens
            temperature: Sampling temperature

        Returns:
            The text response from Claude
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def generate_with_history(
        self,
        system: str = "",
        messages: list[dict] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate with conversation history.

        Args:
            system: System prompt
            messages: List of {"role": "user/assistant", "content": "..."}
            max_tokens: Max output tokens
            temperature: Sampling temperature

        Returns:
            The text response from Claude
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages or [],
        )
        return response.content[0].text

    def read_file(self, file_path: Path) -> str:
        """Read a file and return its content"""
        return file_path.read_text(encoding="utf-8")


# Singleton
_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client
