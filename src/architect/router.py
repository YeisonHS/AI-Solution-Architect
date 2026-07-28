"""Deterministic router: decide when an EDA helps vs a direct recommendation.

No LLM. Uses the problem family (explicit task or keyword detection) plus whether
a dataset is present. The result is a non-blocking suggestion for the UI.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .catalog import (
    FAMILY_ANOMALY,
    FAMILY_CLASSIFICATION,
    FAMILY_CLUSTERING,
    FAMILY_FORECASTING,
    FAMILY_GENERATIVE,
    FAMILY_GENERATIVE_MEDIA,
    FAMILY_LABELS,
    FAMILY_RECOMMENDATION,
    FAMILY_REGRESSION,
    FAMILY_VISION,
    detect_family,
)

EDA_FIRST = "eda_first"
RECOMMENDATION_ONLY = "recommendation_only"

_TABULAR = {
    FAMILY_REGRESSION,
    FAMILY_CLASSIFICATION,
    FAMILY_CLUSTERING,
    FAMILY_FORECASTING,
    FAMILY_ANOMALY,
    FAMILY_RECOMMENDATION,
}

_DATA_KEYWORDS = (
    "dataset", "datos", "csv", "columna", "tabla", "tabular",
    "etiquetad", "registros", "filas", "features", "variables",
)


def route(
    description: str,
    task: Optional[str] = None,
    has_dataset: bool = False,
) -> Dict[str, Any]:
    """Return the suggested path (eda_first | recommendation_only) and why."""
    text = (description or "").lower()
    family = task if (task and task in FAMILY_LABELS) else detect_family(description)
    mentions_data = any(word in text for word in _DATA_KEYWORDS)

    if family in (FAMILY_GENERATIVE, FAMILY_VISION, FAMILY_GENERATIVE_MEDIA):
        path = RECOMMENDATION_ONLY
        reason = (
            "Caso generativo o de visión: un EDA de CSV tabular no aplica. "
            "Ve directo a la recomendación del Board."
        )
    elif has_dataset:
        path = EDA_FIRST
        reason = (
            "Tienes un dataset cargado: perfílalo con el EDA antes de recomendar "
            "para afinar técnica y preparación de datos."
        )
    elif family in _TABULAR and mentions_data:
        path = EDA_FIRST
        reason = (
            "Problema tabular con datos disponibles: un EDA mejora la recomendación "
            "(tipos, enumeradores, correlaciones)."
        )
    else:
        path = RECOMMENDATION_ONLY
        reason = (
            "Puedes ir directo a la recomendación. Si más adelante tienes un "
            "dataset, el EDA es opcional y la refina."
        )

    return {
        "recommended_path": path,
        "reason": reason,
        "family": family,
        "family_label": FAMILY_LABELS.get(family, family),
        "eda_suggested": path == EDA_FIRST,
    }
