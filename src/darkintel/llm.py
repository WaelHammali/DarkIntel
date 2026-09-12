"""Provider-agnostic chat-model factory for Dragon."""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from darkintel.config import settings


def dragon_model() -> BaseChatModel | None:
    """Build Dragon's chat model, or ``None`` if it isn't configured.

    Opt-in only: returns ``None`` (never raises) when ``DARKINTEL_LLM_DRAGON``
    is unset or the provider/key is missing, so callers can skip Dragon the
    same way a missing role is skipped elsewhere in both source projects.
    """
    if not settings.llm_dragon:
        return None
    try:
        return init_chat_model(settings.llm_dragon, temperature=settings.llm_temperature_dragon)
    except Exception:
        return None


def complete(model: BaseChatModel, system_prompt: str, user_prompt: str) -> str:
    """Single-turn completion returning the assistant text."""
    response = model.invoke([SystemMessage(system_prompt), HumanMessage(user_prompt)])
    content = response.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") if isinstance(block, dict) else str(block) for block in content
    )
