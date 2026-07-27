"""Deterministic Review Board agents that evaluate architecture options.

These agents turn concrete option attributes into structured ``AgentVerdict``
values. No verdict comes from a user or an LLM: the board applies fixed hard
rules so a developer can describe options and learn which one fits best.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import AgentVerdict, ArchitectureCandidate, ProblemContext

# Option attribute keys the board understands.
ATTR_ENCRYPTION = "encryption_at_rest"
ATTR_AUTH = "authentication"
ATTR_PUBLIC = "public_network"
ATTR_BACKUPS = "has_backups"
ATTR_COST = "monthly_cost_usd"
CONTEXT_BUDGET = "budget_usd"

# Fraction of the budget above which cost is flagged as a warning.
_COST_WARN_RATIO = 0.8


def review_board(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> List[AgentVerdict]:
    """Evaluate one option with the full board and return its verdicts."""
    return [
        security_agent(candidate),
        cost_agent(context, candidate),
        reliability_agent(candidate),
    ]


def security_agent(candidate: ArchitectureCandidate) -> AgentVerdict:
    """Block options that miss core security controls."""
    encryption = _require_bool(candidate, ATTR_ENCRYPTION)
    authentication = _require_bool(candidate, ATTR_AUTH)
    public = _optional_bool(candidate, ATTR_PUBLIC, default=False)

    reasons: List[str] = []
    passed = 0
    total = 3

    if encryption:
        passed += 1
    else:
        reasons.append("No cifra los datos en reposo.")

    if authentication:
        passed += 1
    else:
        reasons.append("No exige autenticación.")

    if not public or authentication:
        passed += 1
    else:
        reasons.append("Expone la red públicamente sin autenticación.")

    if passed < total:
        return AgentVerdict(
            agent="security",
            verdict="FAIL",
            severity="blocker",
            risk=" ".join(reasons),
            hard_rules_passed=passed,
            hard_rules_total=total,
        )
    return AgentVerdict(
        agent="security",
        verdict="PASS",
        severity="info",
        risk=None,
        hard_rules_passed=total,
        hard_rules_total=total,
    )


def cost_agent(
    context: ProblemContext, candidate: ArchitectureCandidate
) -> AgentVerdict:
    """Block options whose monthly cost exceeds the declared budget."""
    budget = _optional_number(context, CONTEXT_BUDGET)
    cost = _optional_number(candidate, ATTR_COST)

    if budget is None or cost is None:
        return AgentVerdict(
            agent="cost",
            verdict="PASS",
            severity="info",
            risk=None,
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    if cost > budget:
        return AgentVerdict(
            agent="cost",
            verdict="FAIL",
            severity="blocker",
            risk=(
                "El costo mensual ({cost}) supera el presupuesto ({budget})."
            ).format(cost=_money(cost), budget=_money(budget)),
            hard_rules_passed=0,
            hard_rules_total=1,
        )
    if cost > _COST_WARN_RATIO * budget:
        return AgentVerdict(
            agent="cost",
            verdict="WARN",
            severity="warning",
            risk=(
                "El costo mensual ({cost}) se acerca al límite del "
                "presupuesto ({budget})."
            ).format(cost=_money(cost), budget=_money(budget)),
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    return AgentVerdict(
        agent="cost",
        verdict="PASS",
        severity="info",
        risk=None,
        hard_rules_passed=1,
        hard_rules_total=1,
    )


def reliability_agent(candidate: ArchitectureCandidate) -> AgentVerdict:
    """Warn (never block) when an option omits backups."""
    if _optional_bool(candidate, ATTR_BACKUPS, default=False):
        return AgentVerdict(
            agent="reliability",
            verdict="PASS",
            severity="info",
            risk=None,
            hard_rules_passed=1,
            hard_rules_total=1,
        )
    return AgentVerdict(
        agent="reliability",
        verdict="WARN",
        severity="warning",
        risk="La opción no declara copias de seguridad.",
        hard_rules_passed=1,
        hard_rules_total=1,
    )


def _require_bool(candidate: Dict[str, Any], key: str) -> bool:
    value = candidate.get(key)
    if not isinstance(value, bool):
        raise ValueError("{} debe ser verdadero o falso".format(key))
    return value


def _optional_bool(candidate: Dict[str, Any], key: str, default: bool) -> bool:
    if key not in candidate or candidate[key] is None:
        return default
    value = candidate[key]
    if not isinstance(value, bool):
        raise ValueError("{} debe ser verdadero o falso".format(key))
    return value


def _optional_number(source: Dict[str, Any], key: str) -> Optional[float]:
    if key not in source or source[key] is None:
        return None
    value = source[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} debe ser un número".format(key))
    if value < 0:
        raise ValueError("{} no puede ser negativo".format(key))
    return float(value)


def _money(value: float) -> str:
    if float(value).is_integer():
        return "${:,}".format(int(value))
    return "${:,.2f}".format(value)
