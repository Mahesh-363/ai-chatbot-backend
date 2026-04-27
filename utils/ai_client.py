"""
AI client wrapper with retry, token estimation, and error handling.
Supports OpenAI. Can be swapped for any other provider.
"""
import logging
import time
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    pass


class RateLimitError(AIClientError):
    pass


class AIClient:
    """
    Thin wrapper around OpenAI's chat completions API.
    Handles retries, token tracking, and error mapping.
    """

    MAX_RETRIES = 3
    RETRY_BACKOFF = [1, 3, 7]

    def __init__(self):
        try:
            from openai import OpenAI, RateLimitError as OpenAIRateLimitError
            self._client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.OPENAI_TIMEOUT,
            )
            self._RateLimitError = OpenAIRateLimitError
        except ImportError:
            raise AIClientError("openai package not installed")

    def chat(
        self,
        history: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> dict:
        """
        Call the AI with conversation history.

        Returns:
            {
                "content": str,
                "model": str,
                "finish_reason": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
            }
        """
        model = model or settings.OPENAI_MODEL
        max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        system_prompt = system_prompt or settings.AI_SYSTEM_PROMPT

        messages = [{"role": "system", "content": system_prompt}] + history

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start = time.time()
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                elapsed_ms = int((time.time() - start) * 1000)

                choice = response.choices[0]
                result = {
                    "content": choice.message.content or "",
                    "model": response.model,
                    "finish_reason": choice.finish_reason or "stop",
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                    "elapsed_ms": elapsed_ms,
                }

                logger.debug(
                    "AI call succeeded | model=%s tokens=%d elapsed=%dms",
                    model, response.usage.total_tokens, elapsed_ms,
                )
                return result

            except self._RateLimitError as e:
                logger.warning("OpenAI rate limit hit (attempt %d)", attempt + 1)
                last_error = RateLimitError(str(e))
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_BACKOFF[attempt])

            except Exception as e:
                logger.error("OpenAI API error (attempt %d): %s", attempt + 1, str(e))
                last_error = AIClientError(str(e))
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_BACKOFF[attempt])

        raise last_error or AIClientError("All retries exhausted")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate: ~4 chars per token."""
        return max(1, len(text) // 4)
