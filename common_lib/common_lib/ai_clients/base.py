"""AI API 클라이언트 인터페이스 정의(Interface definition for AI API clients)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IAIClient(ABC):
    """AI 클라이언트 공통 인터페이스(Common interface for AI clients)."""

    @abstractmethod
    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """프롬프트로부터 응답 생성(Generate response from prompt)."""

    @abstractmethod
    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """구조화된 출력 생성(Generate structured output)."""

    async def batch_chat(self, prompts: List[str]) -> List[str]:
        """다중 프롬프트 처리(Batch prompt processing)."""

        responses: List[str] = []
        for prompt in prompts:
            responses.append(await self.chat(prompt))
        return responses

