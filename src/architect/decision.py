"""Decision engine: Architect -> Review Board -> Consensus -> ADR.

Reuses the pure consensus policy from the ``orchestrator`` core (``decide`` and
``confidence``) so the convergence rule and the calculated confidence match the
spec exactly, while the Architect and Board are the AI-architecture agents.
"""

from __future__ import annotations

from typing import Any, Dict, List

from orchestrator import AgentVerdict, confidence, decide

from .agents import architect_agent, review_board
from .capability import capability_matrix
from .catalog import FAMILY_LABELS
from .models import (
    ArchitectureCandidate,
    ArchitectureDecisionRecord,
    ProblemContext,
    RejectedAlternative,
)
from .techniques import deployment_options, resolve_family, technique_options
from .evaluation import evaluation_for
from .plan import implementation_plan

_MAX_ROUNDS = 3


def run_review(context: ProblemContext) -> ArchitectureDecisionRecord:
    """Run the bounded debate and return the ADR with rejected alternatives."""
    rejected_ids: List[str] = []
    rejected_alternatives: List[RejectedAlternative] = []

    for round_number in range(_MAX_ROUNDS):
        candidate = architect_agent(context, rejected_ids)
        verdicts = review_board(context, candidate)
        action = decide(verdicts, round_number)

        if action == "re_propose":
            if candidate.identity() not in rejected_ids:
                rejected_alternatives.append(_rejected(candidate, verdicts))
                rejected_ids.append(candidate.identity())
            continue

        forced = action == "force_deliver"
        return ArchitectureDecisionRecord(
            recommendation=candidate,
            confidence=confidence(verdicts),
            accepted_risks=_risks(verdicts, blockers=False),
            unresolved_risks=_risks(verdicts, blockers=True) if forced else [],
            rejected_alternatives=rejected_alternatives,
            rounds=round_number + 1,
            forced=forced,
        )

    raise RuntimeError("review exceeded its bounded rounds")


def _rejected(
    candidate: ArchitectureCandidate, verdicts: List[AgentVerdict]
) -> RejectedAlternative:
    reasons = [
        verdict.risk
        for verdict in verdicts
        if verdict.risk and verdict.verdict in ("FAIL", "WARN")
    ]
    summary = " · ".join(
        "{} {}".format(verdict.agent, verdict.verdict)
        for verdict in verdicts
        if verdict.verdict in ("FAIL", "WARN")
    )
    return RejectedAlternative(
        strategy=candidate.strategy, reasons=reasons, board_summary=summary
    )


def _risks(verdicts: List[AgentVerdict], blockers: bool) -> List[str]:
    risks: List[str] = []
    for verdict in verdicts:
        include = verdict.is_blocker if blockers else verdict.verdict == "WARN"
        if include and verdict.risk and verdict.risk not in risks:
            risks.append(verdict.risk)
    return risks


def serialize_adr(
    context: ProblemContext, adr: ArchitectureDecisionRecord
) -> Dict[str, Any]:
    """Convert the ADR and capability matrix into JSON-only response data."""
    family = resolve_family(context)
    return {
        "problem": {
            "family": family,
            "label": FAMILY_LABELS.get(family, family),
        },
        "evaluation": evaluation_for(family),
        "implementation_plan": implementation_plan(context, adr),
        "technique_options": technique_options(context),
        "deployment_options": deployment_options(context),
        "capability_matrix": [
            {
                "technique": entry.technique,
                "score": entry.score,
                "recommended": entry.recommended,
                "reason": entry.reason,
            }
            for entry in capability_matrix(context.hardware)
        ],
        "recommendation": {
            "strategy": adr.recommendation.strategy,
            "model": adr.recommendation.model,
            "infrastructure": adr.recommendation.infrastructure,
            "database": adr.recommendation.database,
            "framework": adr.recommendation.framework,
            "rationale": adr.recommendation.rationale,
            "estimated_monthly_usd": adr.recommendation.estimated_monthly_usd,
            "deploy_target": adr.recommendation.deploy_target,
            "summary": adr.recommendation.summary(),
        },
        "confidence": adr.confidence,
        "forced": adr.forced,
        "rounds": adr.rounds,
        "accepted_risks": adr.accepted_risks,
        "unresolved_risks": adr.unresolved_risks,
        "rejected_alternatives": [
            {
                "strategy": alt.strategy,
                "reasons": alt.reasons,
                "board_summary": alt.board_summary,
            }
            for alt in adr.rejected_alternatives
        ],
    }
