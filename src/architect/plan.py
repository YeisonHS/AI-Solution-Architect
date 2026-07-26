"""Deterministic implementation plan derived from the ADR.

Turns the decision (family, technique, deploy, metrics) into an actionable,
step-by-step roadmap with a rough effort estimate per step. No LLM.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .catalog import DEPLOY_TARGETS, GPU_DEPLOY_TARGETS, HEAVY_TECHNIQUES
from .evaluation import evaluation_for
from .models import ArchitectureDecisionRecord, ProblemContext
from .techniques import resolve_family


def _is_heavy(strategy: str, deploy_target: str) -> bool:
    return strategy in HEAVY_TECHNIQUES or deploy_target in GPU_DEPLOY_TARGETS


def implementation_plan(
    context: ProblemContext, adr: ArchitectureDecisionRecord
) -> List[Dict[str, Any]]:
    rec = adr.recommendation
    evaluation = evaluation_for(resolve_family(context))
    deploy = DEPLOY_TARGETS.get(rec.deploy_target or "", None)
    deploy_name = deploy.name if deploy else (rec.infrastructure or "AWS")
    cost = rec.estimated_monthly_usd or 0.0
    heavy = _is_heavy(rec.strategy, rec.deploy_target or "")
    train_effort = "alto" if heavy else "medio"

    metrics = ", ".join(m["name"] for m in evaluation["metrics"][:3])
    validation = evaluation["validation"][0] if evaluation["validation"] else "validación estándar"
    primary_metric = evaluation["metrics"][0]["name"] if evaluation["metrics"] else "la métrica clave"

    return [
        {
            "title": "1. Preparar los datos",
            "detail": "Limpia nulos, codifica enumeradores, escala numéricas y separa "
            "train/validation/test. Usa el Validador de datos (EDA) para guiarte.",
            "effort": "medio",
        },
        {
            "title": "2. Baseline",
            "detail": "Implementa y mide un baseline: {}.".format(evaluation["baseline"]),
            "effort": "bajo",
        },
        {
            "title": "3. Modelo recomendado",
            "detail": "Entrena {} con {}.".format(rec.model, rec.framework),
            "effort": train_effort,
        },
        {
            "title": "4. Evaluación",
            "detail": "Valida con {} y mide {}. El objetivo es superar el baseline.".format(
                validation, metrics
            ),
            "effort": "bajo",
        },
        {
            "title": "5. Despliegue",
            "detail": "Empaqueta con el Dockerfile y despliega en {} (~${:,.0f}/mes). "
            "Descarga los artefactos generados como punto de partida.".format(
                deploy_name, cost
            ),
            "effort": "medio",
        },
        {
            "title": "6. Monitoreo y reentrenamiento",
            "detail": "Vigila {} en producción y define disparadores de reentrenamiento "
            "ante drift de datos.".format(primary_metric),
            "effort": "medio",
        },
    ]
