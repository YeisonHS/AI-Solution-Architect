"""Deterministic monthly cost estimation from the curated AWS pricing KB.

Estimates are intentionally simple and explainable: each strategy maps to a set
of AWS components with stated assumptions (e.g., training hours). The goal is
anchored, defensible numbers for the Cost Agent and the ADR, not billing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .kb import AWS_SERVICES
from .models import (
    STRATEGY_AGENTS,
    STRATEGY_FINE_TUNING,
    STRATEGY_LORA,
    STRATEGY_RAG,
    ProblemContext,
)

# Assumed monthly training hours for techniques that train a model.
_LORA_TRAIN_HOURS = 40.0
_FINE_TUNING_TRAIN_HOURS = 200.0
_SERVING_HOURS = 730.0


@dataclass(frozen=True)
class CostLine:
    label: str
    monthly_usd: float


@dataclass(frozen=True)
class CostEstimate:
    strategy: str
    monthly_usd: float
    lines: List[CostLine]

    def breakdown(self) -> str:
        return "; ".join(
            "{}: ${:,.0f}".format(line.label, line.monthly_usd) for line in self.lines
        )


def _hourly(key: str, hours: float) -> float:
    return AWS_SERVICES[key].unit_price_usd * hours


def estimate_cost(strategy: str, context: ProblemContext) -> CostEstimate:
    """Return a deterministic monthly estimate for a strategy."""
    lines: List[CostLine] = []

    if strategy in (STRATEGY_RAG, STRATEGY_AGENTS):
        vcpu = 1.0 if strategy == STRATEGY_RAG else 2.0
        gb = 2.0 if strategy == STRATEGY_RAG else 4.0
        lines.append(
            CostLine(
                "ECS Fargate",
                round(
                    _hourly("fargate_vcpu", _SERVING_HOURS) * vcpu
                    + _hourly("fargate_gb", _SERVING_HOURS) * gb,
                    2,
                ),
            )
        )
        lines.append(
            CostLine(
                "RDS PostgreSQL (pgvector)",
                round(_hourly("rds_pg_t3_medium", _SERVING_HOURS), 2),
            )
        )
        lines.append(CostLine("S3 documentos", 5.0))
        lines.append(
            CostLine("Bedrock tokens", 20.0 if strategy == STRATEGY_RAG else 45.0)
        )
    elif strategy == STRATEGY_LORA:
        lines.append(
            CostLine(
                "EC2 g5.xlarge (entrenamiento LoRA)",
                round(_hourly("ec2_g5_xlarge", _LORA_TRAIN_HOURS), 2),
            )
        )
        lines.append(
            CostLine(
                "SageMaker endpoint (serving)",
                round(_hourly("sagemaker_g5_xlarge", _SERVING_HOURS), 2),
            )
        )
        lines.append(CostLine("S3 datasets", 15.0))
    elif strategy == STRATEGY_FINE_TUNING:
        lines.append(
            CostLine(
                "EC2 p4d.24xlarge (fine-tuning completo)",
                round(_hourly("ec2_p4d_24xlarge", _FINE_TUNING_TRAIN_HOURS), 2),
            )
        )
        lines.append(
            CostLine(
                "SageMaker endpoint (serving)",
                round(_hourly("sagemaker_g5_xlarge", _SERVING_HOURS), 2),
            )
        )
        lines.append(CostLine("S3 datasets", 25.0))

    monthly = round(sum(line.monthly_usd for line in lines), 2)
    return CostEstimate(strategy=strategy, monthly_usd=monthly, lines=lines)
