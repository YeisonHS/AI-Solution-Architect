"""Technique and deployment recommender.

Resolves the problem family from the context, builds the candidate plan the
Architect will propose, and exposes the technique menu and deployment options
(with curated costs) that guide an AI developer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from . import catalog
from .catalog import (
    DEPLOY_TARGETS,
    FAMILY_GENERATIVE,
    FAMILY_LABELS,
    Technique,
    detect_family,
    recommended_technique,
    techniques_for,
)
from .cost import estimate_cost
from .models import ArchitectureCandidate, ProblemContext

_TRAIN_SURCHARGE_GPU = 150.0
_TRAIN_SURCHARGE_CPU = 10.0

_GENERATIVE_DEPLOY = {
    "rag": "ecs_fargate",
    "agents": "ecs_fargate",
    "lora": "sagemaker_realtime_gpu",
    "fine_tuning": "sagemaker_realtime_gpu",
}


def resolve_family(context: ProblemContext) -> str:
    """Use the explicit task if valid, otherwise detect it from the description."""
    if context.task and context.task in FAMILY_LABELS:
        return context.task
    return detect_family(context.description)


def estimate_monthly(technique: Technique, target_key: str) -> float:
    target = DEPLOY_TARGETS[target_key]
    surcharge = _TRAIN_SURCHARGE_GPU if technique.needs_gpu else _TRAIN_SURCHARGE_CPU
    return round(target.base_monthly_usd + surcharge, 2)


def _feasible_target_keys(technique: Technique) -> List[str]:
    if technique.needs_gpu:
        return ["batch_transform", "sagemaker_realtime_gpu"]
    return [
        "lambda",
        "sagemaker_serverless",
        "batch_transform",
        "ecs_fargate",
        "sagemaker_realtime",
    ]


def _preferred_target(technique: Technique, context: Optional[ProblemContext] = None) -> str:
    if technique.needs_gpu:
        return "sagemaker_realtime_gpu"
    mode = context.constraints.serving_mode if context else "realtime"
    if mode == "batch":
        return "batch_transform"
    if mode == "streaming":
        return "ecs_fargate"
    return "sagemaker_serverless"


def _ordered_targets(
    technique: Technique, context: Optional[ProblemContext] = None
) -> List[str]:
    """Preferred deploy first (by serving mode), then cheaper feasible ones."""
    preferred = _preferred_target(technique, context)
    others = [k for k in _feasible_target_keys(technique) if k != preferred]
    others.sort(key=lambda k: estimate_monthly(technique, k))
    return [preferred] + others


def pick_technique(family: str, context: Optional[ProblemContext] = None):
    """Recommended technique, favouring interpretable ones when required."""
    options = techniques_for(family)
    if not options:
        return None
    if context and context.constraints.interpretability_required:
        interpretable = [
            t for t in options if not t.needs_gpu and t.complexity in ("baja", "media")
        ]
        interpretable.sort(key=lambda t: 0 if t.complexity == "baja" else 1)
        if interpretable:
            return interpretable[0]
    return options[0]


def _classic_candidate(
    family: str, technique: Technique, target_key: str
) -> ArchitectureCandidate:
    target = DEPLOY_TARGETS[target_key]
    monthly = estimate_monthly(technique, target_key)
    return ArchitectureCandidate(
        strategy=technique.key,
        model=technique.name,
        infrastructure=target.name,
        database="S3 (datos) + Feature Store" if family != "clustering" else "S3 (datos)",
        framework=technique.frameworks[0],
        rationale="{} Despliegue: {} (~${:,.0f}/mes).".format(
            technique.summary, target.name, monthly
        ),
        estimated_monthly_usd=monthly,
        deploy_target=target_key,
    )


def _generative_candidate(strategy: str, context: ProblemContext) -> ArchitectureCandidate:
    cost = estimate_cost(strategy, context)
    target_key = _GENERATIVE_DEPLOY.get(strategy, "ecs_fargate")
    technique = next(
        (t for t in techniques_for(FAMILY_GENERATIVE) if t.key == strategy), None
    )
    name = technique.name if technique else strategy
    framework = technique.frameworks[0] if technique else "LangGraph"
    infra_map = {
        "rag": "ECS Fargate + API Gateway",
        "agents": "ECS Fargate + API Gateway",
        "lora": "SageMaker (serving GPU) + EC2 (entrenamiento)",
        "fine_tuning": "EC2 p4d (entrenamiento) + SageMaker (serving)",
    }
    db_map = {
        "rag": "RDS PostgreSQL con pgvector",
        "agents": "RDS PostgreSQL con pgvector",
        "lora": "S3 + RDS PostgreSQL",
        "fine_tuning": "S3 + RDS PostgreSQL",
    }
    return ArchitectureCandidate(
        strategy=strategy,
        model={
            "rag": "Claude 3.5 Sonnet (Bedrock) + embeddings",
            "agents": "Claude 3.5 Sonnet (Bedrock)",
            "lora": "Llama 3.1 8B + LoRA",
            "fine_tuning": "Llama 3.3 70B (fine-tuned)",
        }.get(strategy, "LLM"),
        infrastructure=infra_map.get(strategy, "ECS Fargate"),
        database=db_map.get(strategy, "RDS PostgreSQL"),
        framework=framework,
        rationale="{} {}".format(name, cost.breakdown()),
        estimated_monthly_usd=cost.monthly_usd,
        deploy_target=target_key,
    )


def candidate_plan(context: ProblemContext) -> List[ArchitectureCandidate]:
    """Ordered candidates the Architect will try across rounds."""
    family = resolve_family(context)
    if family == FAMILY_GENERATIVE:
        order = (
            ["fine_tuning", "rag"]
            if context.constraints.data_changes_frequently
            else ["rag", "agents"]
        )
        return [_generative_candidate(s, context) for s in order]

    technique = pick_technique(family, context)
    if technique is None:
        return [_generative_candidate("rag", context)]
    return [_classic_candidate(family, technique, key) for key in _ordered_targets(technique, context)]


def next_candidate(
    context: ProblemContext, rejected_identities: Sequence[str]
) -> ArchitectureCandidate:
    plan = candidate_plan(context)
    rejected = set(rejected_identities)
    for candidate in plan:
        if candidate.identity() not in rejected:
            return candidate
    return plan[-1]


def technique_options(context: ProblemContext) -> List[Dict[str, Any]]:
    """The menu of techniques for the resolved family (recommended flagged)."""
    family = resolve_family(context)
    options = techniques_for(family)
    chosen = pick_technique(family, context)
    chosen_key = chosen.key if chosen else None
    return [
        {
            "key": t.key,
            "name": t.name,
            "summary": t.summary,
            "when_to_use": t.when_to_use,
            "frameworks": list(t.frameworks),
            "complexity": t.complexity,
            "needs_gpu": t.needs_gpu,
            "recommended": t.key == chosen_key,
        }
        for t in options
    ]


def deployment_options(context: ProblemContext) -> List[Dict[str, Any]]:
    """Deployment targets feasible for the recommended technique, with costs."""
    family = resolve_family(context)
    technique = pick_technique(family, context)
    if technique is None:
        return []
    budget = context.constraints.monthly_budget_usd
    results = []
    for key in _ordered_targets(technique, context):
        target = DEPLOY_TARGETS[key]
        monthly = estimate_monthly(technique, key)
        results.append(
            {
                "target": key,
                "name": target.name,
                "summary": target.summary,
                "best_for": target.best_for,
                "estimated_monthly_usd": monthly,
                "gpu": target.gpu,
                "within_budget": budget is None or monthly <= budget,
            }
        )
    return results
