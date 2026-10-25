import time
import logging
from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI
from ..config import settings

logger = logging.getLogger("ada.llm")

class DualLLMClient:
    """
    Resilient Dual-LLM client with automatic failover:
    Primary: NVIDIA Nemotron 3.5 Lightning 30B
    Fallback: Groq GPT-OSS 20B
    """

    def __init__(self):
        # Clients are only created when a key is configured. The OpenAI SDK raises
        # at construction time for empty keys, which would otherwise crash app startup.
        self.nvidia_client = self._build_client(
            settings.NVIDIA_BASE_URL, settings.NVIDIA_API_KEY, "NVIDIA"
        )
        self.nvidia_model = settings.NVIDIA_MODEL
        self.groq_client = self._build_client(
            settings.GROQ_BASE_URL, settings.GROQ_API_KEY, "Groq"
        )
        self.groq_model = settings.GROQ_MODEL

    @staticmethod
    def _build_client(base_url: str, api_key: str, provider: str) -> Optional[OpenAI]:
        if not api_key:
            logger.warning("%s API key not configured; provider disabled.", provider)
            return None
        try:
            return OpenAI(base_url=base_url, api_key=api_key, timeout=35.0)
        except Exception as e:
            logger.error("Failed to initialize %s client: %s", provider, e)
            return None

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, Any]] = None,
        on_failover: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a chat completion with automatic failover.
        Returns: {
            "content": str,
            "model_used": str,
            "provider": str,
            "duration_ms": int,
            "fallback_triggered": bool
        }
        """
        start_time = time.time()

        if self.nvidia_client is None and self.groq_client is None:
            raise RuntimeError(
                "No LLM provider is configured. Set NVIDIA_API_KEY and/or GROQ_API_KEY."
            )

        # 1. Attempt Primary (NVIDIA) if configured
        if self.nvidia_client is not None:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.nvidia_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                resp = self.nvidia_client.chat.completions.create(**kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                content = resp.choices[0].message.content or ""
                return {
                    "content": content,
                    "model_used": self.nvidia_model,
                    "provider": "NVIDIA",
                    "duration_ms": duration_ms,
                    "fallback_triggered": False,
                }
            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    "Primary NVIDIA LLM failed: %s. Switching to Groq fallback...", error_msg
                )
                if on_failover:
                    on_failover(self.nvidia_model, self.groq_model)

        # 2. Attempt Fallback (Groq) if configured
        if self.groq_client is not None:
            try:
                kwargs_fallback: Dict[str, Any] = {
                    "model": self.groq_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs_fallback["response_format"] = response_format

                resp = self.groq_client.chat.completions.create(**kwargs_fallback)
                duration_ms = int((time.time() - start_time) * 1000)
                content = resp.choices[0].message.content or ""
                return {
                    "content": content,
                    "model_used": self.groq_model,
                    "provider": "Groq",
                    "duration_ms": duration_ms,
                    "fallback_triggered": True,
                }
            except Exception as groq_err:
                logger.error("Fallback Groq LLM also failed: %s", groq_err)
                raise RuntimeError(
                    f"Both Primary (NVIDIA) and Fallback (Groq) LLMs failed: {groq_err}"
                )

        raise RuntimeError("No LLM provider is configured. Set NVIDIA_API_KEY and/or GROQ_API_KEY.")

llm_client = DualLLMClient()
