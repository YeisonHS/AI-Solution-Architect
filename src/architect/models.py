"""Domain models for the AI Solution Architect MVP.

These structures describe the decision problem, the hardware profile used by the
Capability Matrix, and the architecture candidate the Architect Agent proposes.
They are deterministic, dependency-free dataclasses (Python 3.9 compatible).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Architecture strategies the Architect can choose among.
STRATEGY_RAG = "rag"
STRATEGY_FINE_TUNING = "fine_tuning"
STRATEGY_LORA = "lora"
STRATEGY_AGENTS = "agents"
STRATEGIES = (STRATEGY_RAG, STRATEGY_AGENTS, STRATEGY_LORA, STRATEGY_FINE_TUNING)

# Privacy postures.
PRIVACY_PUBLIC = "public"
PRIVACY_PRIVATE = "private_cloud"
PRIVACY_ON_PREM = "on_prem_only"
PRIVACY_LEVELS = (PRIVACY_PUBLIC, PRIVACY_PRIVATE, PRIVACY_ON_PREM)

# Serving modes influence the deployment target.
SERVING_REALTIME = "realtime"
SERVING_BATCH = "batch"
SERVING_STREAMING = "streaming"
SERVING_MODES = (SERVING_REALTIME, SERVING_BATCH, SERVING_STREAMING)


@dataclass(frozen=True)
class HardwareProfile:
    """The machine the Capability Matrix is computed against."""

    cpu_cores: int
    ram_gb: float
    has_gpu: bool = False
    vram_gb: float = 0.0
    unified_memory: bool = False
    storage_gb: float = 0.0

    def usable_model_memory_gb(self) -> float:
        """Memory realistically available to hold a model for inference."""
        if self.has_gpu and self.vram_gb > 0:
            return self.vram_gb
        if self.unified_memory:
            # Apple Silicon and similar share RAM with the accelerator.
            return round(self.ram_gb * 0.6, 2)
        return 0.0


@dataclass(frozen=True)
class Constraints:
    """Constraints the user declares in the entry wizard."""

    monthly_budget_usd: Optional[float] = None
    max_latency_ms: Optional[int] = None
    privacy: str = PRIVACY_PUBLIC
    expected_requests_per_day: Optional[int] = None
    data_changes_frequently: bool = False
    interpretability_required: bool = False
    class_imbalance: bool = False
    serving_mode: str = "realtime"

    def __post_init__(self) -> None:
        if self.privacy not in PRIVACY_LEVELS:
            raise ValueError("privacy must be one of {}".format(PRIVACY_LEVELS))
        if self.serving_mode not in SERVING_MODES:
            raise ValueError("serving_mode must be one of {}".format(SERVING_MODES))
        for name, value in (
            ("monthly_budget_usd", self.monthly_budget_usd),
            ("max_latency_ms", self.max_latency_ms),
            ("expected_requests_per_day", self.expected_requests_per_day),
        ):
            if value is not None and (isinstance(value, bool) or value < 0):
                raise ValueError("{} must be a non-negative number".format(name))


@dataclass(frozen=True)
class ProblemContext:
    """The full decision problem: what to build and under which limits."""

    description: str
    hardware: HardwareProfile
    constraints: Constraints = field(default_factory=Constraints)
    knowledge_base_docs: Optional[int] = None
    task: Optional[str] = None
    dataset_labeled: Optional[bool] = None
    dataset_rows: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be a non-empty string")
        if self.dataset_rows is not None and (
            isinstance(self.dataset_rows, bool) or self.dataset_rows < 0
        ):
            raise ValueError("dataset_rows must be a non-negative integer")


@dataclass(frozen=True)
class CapabilityEntry:
    """One row of the AI Capability Matrix."""

    technique: str
    score: int
    recommended: bool
    reason: str


@dataclass(frozen=True)
class ArchitectureCandidate:
    """A concrete architecture the Architect Agent proposes."""

    strategy: str
    model: str
    infrastructure: str
    database: str
    framework: str
    rationale: str = ""
    estimated_monthly_usd: Optional[float] = None
    deploy_target: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, str) or not self.strategy.strip():
            raise ValueError("strategy must be a non-empty string")
        for name in ("model", "infrastructure", "database", "framework"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("{} must be a non-empty string".format(name))

    def identity(self) -> str:
        """Stable identity for the re-proposal loop (technique + deploy)."""
        return "{}::{}".format(self.strategy, self.deploy_target or "-")

    def summary(self) -> str:
        return "{strategy} · {model} · {infra} · {db} · {fw}".format(
            strategy=self.strategy,
            model=self.model,
            infra=self.infrastructure,
            db=self.database,
            fw=self.framework,
        )


@dataclass(frozen=True)
class RejectedAlternative:
    """An alternative the Board rejected, with reasons for the ADR."""

    strategy: str
    reasons: List[str]
    board_summary: str


@dataclass
class ArchitectureDecisionRecord:
    """The final ADR with rejected alternatives and a calculated confidence."""

    recommendation: ArchitectureCandidate
    confidence: int
    accepted_risks: List[str] = field(default_factory=list)
    unresolved_risks: List[str] = field(default_factory=list)
    rejected_alternatives: List[RejectedAlternative] = field(default_factory=list)
    rounds: int = 1
    forced: bool = False
