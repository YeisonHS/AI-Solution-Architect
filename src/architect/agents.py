"""Architect Agent and the Architecture Review Board (deterministic).

The Architect proposes a candidate from the ProblemContext via the technique
recommender; the Board challenges it. Only Security and Cost may emit blocking
FAILs (spec §3.2); Best Practices, Product and Devil's Advocate may only PASS or
WARN. Verdicts use the structured AgentVerdict contract from the consensus core.
"""

from __future__ import annotations

from typing import List, Sequence

from orchestrator import AgentVerdict

from .catalog import GPU_DEPLOY_TARGETS, HEAVY_TECHNIQUES
from .models import PRIVACY_ON_PREM, ArchitectureCandidate, ProblemContext
from .techniques import next_candidate, resolve_family


def architect_agent(
    context: ProblemContext, rejected_identities: Sequence[str]
) -> ArchitectureCandidate:
    """Propose the next candidate, skipping already-rejected ones."""
    return next_candidate(context, rejected_identities)


def review_board(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> List[AgentVerdict]:
    """Run all Board agents against a candidate and return their verdicts."""
    return [
        security_agent(context, candidate),
        cost_agent(context, candidate),
        best_practices_agent(context, candidate),
        product_agent(context, candidate),
        devils_advocate_agent(context, candidate),
    ]


def _is_heavy(candidate: ArchitectureCandidate) -> bool:
    return (
        candidate.strategy in HEAVY_TECHNIQUES
        or (candidate.deploy_target in GPU_DEPLOY_TARGETS)
    )


def security_agent(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> AgentVerdict:
    """Block only when on-prem-only data would be pushed to heavy cloud compute."""
    total = 2
    passed = 1  # managed AWS storage is treated as controlled.
    reasons: List[str] = []
    conflict = context.constraints.privacy == PRIVACY_ON_PREM and _is_heavy(candidate)
    if not conflict:
        passed += 1
    else:
        reasons.append(
            "Datos on-premise no deberían salir a entrenamiento/serving GPU en la nube."
        )
    if passed < total:
        return AgentVerdict(
            agent="security",
            verdict="FAIL",
            severity="blocker",
            risk=" ".join(reasons),
            hard_rules_passed=passed,
            hard_rules_total=total,
        )
    return AgentVerdict("security", "PASS", "info", None, total, total)


def cost_agent(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> AgentVerdict:
    """Block architectures whose monthly cost exceeds the budget."""
    budget = context.constraints.monthly_budget_usd
    monthly = candidate.estimated_monthly_usd or 0.0
    if budget is None:
        return AgentVerdict("cost", "PASS", "info", None, 1, 1)
    if monthly > budget:
        return AgentVerdict(
            agent="cost",
            verdict="FAIL",
            severity="blocker",
            risk="Costo estimado ${:,.0f}/mes supera el presupuesto ${:,.0f}/mes.".format(
                monthly, budget
            ),
            hard_rules_passed=0,
            hard_rules_total=1,
        )
    if monthly > 0.8 * budget:
        return AgentVerdict(
            agent="cost",
            verdict="WARN",
            severity="warning",
            risk="Costo ${:,.0f}/mes cerca del límite del presupuesto ${:,.0f}/mes.".format(
                monthly, budget
            ),
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    return AgentVerdict("cost", "PASS", "info", None, 1, 1)


def best_practices_agent(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> AgentVerdict:
    """Warn on MLOps/scalability/latency complexity; never blocks."""
    latency = context.constraints.max_latency_ms
    if latency is not None and latency < 50 and _is_heavy(candidate):
        return AgentVerdict(
            agent="best_practices",
            verdict="WARN",
            severity="warning",
            risk="Latencia objetivo <50 ms con endpoint/modelo GPU pesado: difícil de cumplir.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    if _is_heavy(candidate):
        return AgentVerdict(
            agent="best_practices",
            verdict="WARN",
            severity="warning",
            risk="Entrenar/servir en GPU añade complejidad de MLOps, versionado y CI/CD.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    return AgentVerdict("best_practices", "PASS", "info", None, 1, 1)


def product_agent(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> AgentVerdict:
    """Warn on over-engineering / delivery risk; never blocks."""
    if (
        candidate.strategy == "fine_tuning"
        and context.constraints.data_changes_frequently
    ):
        return AgentVerdict(
            agent="product",
            verdict="WARN",
            severity="warning",
            risk="Sobre-ingeniería: el corpus cambia seguido; reentrenar no aporta valor.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    small_data = context.dataset_rows is not None and context.dataset_rows < 10000
    if candidate.strategy in HEAVY_TECHNIQUES and small_data:
        return AgentVerdict(
            agent="product",
            verdict="WARN",
            severity="warning",
            risk="Sobre-ingeniería: con pocos datos un modelo más simple suele bastar.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    if context.constraints.interpretability_required and _is_heavy(candidate):
        return AgentVerdict(
            agent="product",
            verdict="WARN",
            severity="warning",
            risk="Se requiere interpretabilidad; prefiere un modelo más explicable.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    if context.constraints.class_imbalance and resolve_family(context) == "classification":
        return AgentVerdict(
            agent="product",
            verdict="WARN",
            severity="warning",
            risk="Hay desbalance de clases: aplica resampling/pesos y evalúa con PR-AUC.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    return AgentVerdict("product", "PASS", "info", None, 1, 1)


def devils_advocate_agent(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> AgentVerdict:
    """Fixed stress questions; may warn, never blocks (spec §3.1)."""
    if (
        candidate.strategy == "fine_tuning"
        and context.constraints.data_changes_frequently
    ):
        return AgentVerdict(
            agent="devils_advocate",
            verdict="WARN",
            severity="warning",
            risk="Si el corpus cambia a diario, cada cambio exige un reentrenamiento.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    if _is_heavy(candidate):
        return AgentVerdict(
            agent="devils_advocate",
            verdict="WARN",
            severity="warning",
            risk="¿El volumen de datos justifica el costo de GPU y el reentrenamiento?",
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    return AgentVerdict("devils_advocate", "PASS", "info", None, 1, 1)
