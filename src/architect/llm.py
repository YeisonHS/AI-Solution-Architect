"""Model-agnostic LLM provider abstraction.

The Architect and Board are deterministic (spec §4), so the system runs with no
API key using ``DeterministicProvider``. A cloud or local model can be plugged
in later to enrich natural-language explanations without changing the decision
logic.
"""

from __future__ import annotations

from typing import Optional, Protocol


class LLMProvider(Protocol):
    """Minimal interface: turn a prompt into explanatory prose."""

    name: str

    def explain(self, prompt: str) -> str:
        ...


class DeterministicProvider:
    """Default provider: echoes structured reasoning with no external calls."""

    name = "deterministic"

    def explain(self, prompt: str) -> str:
        # The decision itself is computed by rules; this only frames it.
        return prompt.strip()


class ConfiguredCloudProvider:
    """Placeholder for a cloud model (Claude/GPT/Gemini).

    Kept intentionally inert until an API key and client are wired, so the MVP
    never depends on network access or secrets to produce a decision.
    """

    def __init__(self, name: str, api_key: Optional[str]) -> None:
        self.name = name
        self._api_key = api_key

    def explain(self, prompt: str) -> str:
        if not self._api_key:
            raise RuntimeError(
                "El proveedor '{}' requiere una API key configurada.".format(self.name)
            )
        raise NotImplementedError(
            "Cliente de '{}' no cableado todavía; usa DeterministicProvider.".format(
                self.name
            )
        )


def default_provider() -> LLMProvider:
    """Return the safe, offline default provider."""
    return DeterministicProvider()
