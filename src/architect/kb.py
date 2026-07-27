"""Curated, deterministic knowledge base for the AI Solution Architect.

Numbers here are a curated snapshot used to keep the demo's figures anchored in
real data rather than hallucinated by an LLM (see MVP spec §4). Prices are
approximate USD on-demand references and are labelled with an as-of date; they
are meant for estimation and comparison, not billing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

PRICING_AS_OF = "2024-06 curated snapshot (USD, on-demand, us-east-1 approx.)"


@dataclass(frozen=True)
class AwsService:
    key: str
    name: str
    unit: str
    unit_price_usd: float
    hours_per_month: float = 730.0

    def monthly_if_hourly(self) -> Optional[float]:
        if self.unit == "hour":
            return round(self.unit_price_usd * self.hours_per_month, 2)
        return None


# Curated AWS reference prices relevant to AI inference/hosting.
AWS_SERVICES: Dict[str, AwsService] = {
    "ec2_g5_xlarge": AwsService(
        "ec2_g5_xlarge", "EC2 g5.xlarge (A10G 24GB)", "hour", 1.006
    ),
    "ec2_g4dn_xlarge": AwsService(
        "ec2_g4dn_xlarge", "EC2 g4dn.xlarge (T4 16GB)", "hour", 0.526
    ),
    "ec2_p4d_24xlarge": AwsService(
        "ec2_p4d_24xlarge", "EC2 p4d.24xlarge (8×A100 40GB)", "hour", 32.7726
    ),
    "sagemaker_g5_xlarge": AwsService(
        "sagemaker_g5_xlarge", "SageMaker ml.g5.xlarge endpoint", "hour", 1.408
    ),
    "fargate_vcpu": AwsService(
        "fargate_vcpu", "ECS Fargate vCPU", "hour", 0.04048
    ),
    "fargate_gb": AwsService("fargate_gb", "ECS Fargate GB", "hour", 0.004445),
    "rds_pg_t3_medium": AwsService(
        "rds_pg_t3_medium", "RDS PostgreSQL db.t3.medium (pgvector)", "hour", 0.068
    ),
    "opensearch_t3_medium": AwsService(
        "opensearch_t3_medium", "OpenSearch t3.medium.search", "hour", 0.075
    ),
    "s3_gb_month": AwsService("s3_gb_month", "S3 Standard", "gb-month", 0.023),
}

# Bedrock-style token pricing (USD per 1K tokens) for hosted models.
BEDROCK_TOKEN_PRICES: Dict[str, Dict[str, float]] = {
    "claude-3.5-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
    "titan-embed-text": {"input_per_1k": 0.0001, "output_per_1k": 0.0},
}


@dataclass(frozen=True)
class ModelProfile:
    """Local-model footprint used by the Capability Matrix and Architect."""

    key: str
    name: str
    params_b: float
    vram_gb_q4: float
    tool_calling: bool
    notes: str = ""


# Curated local model footprints (Q4 quantization, approximate).
MODEL_PROFILES: Dict[str, ModelProfile] = {
    "qwen3-8b": ModelProfile(
        "qwen3-8b", "Qwen3 8B", 8, 6.0, True, "Buen tool-calling; corre en 8GB."
    ),
    "qwen2.5-14b": ModelProfile(
        "qwen2.5-14b", "Qwen2.5 14B", 14, 10.0, True, "Equilibrio calidad/tamaño."
    ),
    "qwen2.5-32b": ModelProfile(
        "qwen2.5-32b", "Qwen2.5 32B", 32, 20.0, True, "Requiere GPU de 24GB."
    ),
    "llama-3.3-70b": ModelProfile(
        "llama-3.3-70b", "Llama 3.3 70B", 70, 40.0, True, "Alta calidad; 40GB+."
    ),
}


@dataclass(frozen=True)
class TechniqueRequirement:
    """Resource thresholds per AI technique, for the Capability Matrix."""

    technique: str
    label: str
    min_memory_gb: float
    recommended_memory_gb: float
    needs_gpu: bool
    min_ram_gb: float


# Requirements per technique. RAG/Agents run on inference-class memory;
# LoRA/Fine-Tuning need real accelerator memory to train.
TECHNIQUE_REQUIREMENTS: Dict[str, TechniqueRequirement] = {
    "rag": TechniqueRequirement("rag", "RAG", 2.0, 8.0, False, 8.0),
    "agents": TechniqueRequirement("agents", "Agents", 6.0, 12.0, False, 12.0),
    "lora": TechniqueRequirement("lora", "LoRA", 16.0, 24.0, True, 16.0),
    "fine_tuning": TechniqueRequirement(
        "fine_tuning", "Fine-Tuning", 24.0, 48.0, True, 32.0
    ),
}


def largest_local_model_for(vram_gb: float) -> Optional[ModelProfile]:
    """Return the biggest curated model that fits in the given memory."""
    fitting = [m for m in MODEL_PROFILES.values() if m.vram_gb_q4 <= vram_gb]
    if not fitting:
        return None
    return max(fitting, key=lambda model: model.params_b)
