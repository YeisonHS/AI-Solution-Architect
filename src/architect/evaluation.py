"""Curated evaluation guidance per problem family (metrics, validation, pitfalls).

Deterministic knowledge so the tool tells an AI developer not only *what* to use
but *how to measure and validate* it correctly.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .catalog import (
    FAMILY_ANOMALY,
    FAMILY_CLASSIFICATION,
    FAMILY_CLUSTERING,
    FAMILY_FORECASTING,
    FAMILY_GENERATIVE,
    FAMILY_RECOMMENDATION,
    FAMILY_REGRESSION,
    FAMILY_VISION,
)


def _entry(metrics, validation, pitfalls, baseline) -> Dict[str, Any]:
    return {
        "metrics": [{"name": n, "note": note} for n, note in metrics],
        "validation": list(validation),
        "pitfalls": list(pitfalls),
        "baseline": baseline,
    }


EVALUATION: Dict[str, Dict[str, Any]] = {
    FAMILY_REGRESSION: _entry(
        [
            ("RMSE", "Penaliza errores grandes; en las unidades del objetivo."),
            ("MAE", "Error medio absoluto; robusto a outliers."),
            ("R²", "Proporción de varianza explicada."),
            ("MAPE", "Error porcentual; útil para comparar escalas."),
        ],
        [
            "Split train/validation/test (p. ej. 70/15/15).",
            "K-fold cross-validation (k=5) para estimar la varianza.",
            "Compara siempre contra un baseline (media o mediana).",
        ],
        [
            "Evita fugas: ajusta el escalado dentro de cada fold.",
            "Revisa los residuales; los outliers inflan el RMSE.",
        ],
        "Predecir la media/mediana del objetivo.",
    ),
    FAMILY_CLASSIFICATION: _entry(
        [
            ("F1", "Equilibra precisión y recall; útil con desbalance."),
            ("Precision / Recall", "Falsos positivos vs falsos negativos."),
            ("ROC-AUC / PR-AUC", "Capacidad de ranking; PR-AUC si hay desbalance."),
            ("Matriz de confusión", "Diagnóstico por clase."),
        ],
        [
            "Split estratificado y k-fold estratificado.",
            "Ajusta el umbral de decisión según el costo de error.",
            "Baseline = predecir la clase mayoritaria.",
        ],
        [
            "Con desbalance NO uses accuracy; usa F1/PR-AUC.",
            "Calibra probabilidades si necesitas umbrales fiables.",
        ],
        "Clase mayoritaria (ZeroR).",
    ),
    FAMILY_CLUSTERING: _entry(
        [
            ("Silhouette", "Cohesión vs separación (sin etiquetas)."),
            ("Davies-Bouldin", "Menor es mejor."),
            ("Calinski-Harabasz", "Mayor es mejor."),
            ("ARI / NMI", "Solo si tienes etiquetas de referencia."),
        ],
        [
            "Prueba varios k y elige por silhouette o método del codo.",
            "Evalúa estabilidad re-sembrando (varias semillas).",
            "Escala/normaliza las variables antes de agrupar.",
        ],
        [
            "K-Means asume clusters esféricos y es sensible a la escala.",
            "Sin ground truth, valida también con criterio de negocio.",
        ],
        "Un solo cluster / asignación aleatoria.",
    ),
    FAMILY_FORECASTING: _entry(
        [
            ("MAE / RMSE", "Error absoluto y penalización de picos."),
            ("MAPE / sMAPE", "Error porcentual (cuidado con ceros)."),
            ("Cobertura del intervalo", "Si predices incertidumbre."),
        ],
        [
            "Split temporal: entrena en el pasado, prueba en el futuro.",
            "Backtesting con ventana deslizante (rolling origin).",
            "Baseline = naïve o naïve estacional.",
        ],
        [
            "Nunca hagas shuffle aleatorio: causa fuga de futuro.",
            "Modela estacionalidad y festivos explícitamente.",
        ],
        "Último valor (naïve) o estacional.",
    ),
    FAMILY_ANOMALY: _entry(
        [
            ("PR-AUC", "Mejor que ROC con clases muy desbalanceadas."),
            ("Precision@k / Recall", "Calidad de las alertas priorizadas."),
            ("F1", "Si dispones de etiquetas de anomalía."),
        ],
        [
            "Valida en un conjunto etiquetado retenido (aunque sea pequeño).",
            "Ajusta el umbral por tasa de falsos positivos tolerable.",
        ],
        [
            "Define el costo relativo de falsos positivos vs negativos.",
            "Las anomalías cambian con el tiempo: re-evalúa periódicamente.",
        ],
        "Regla simple por umbral estadístico (z-score).",
    ),
    FAMILY_RECOMMENDATION: _entry(
        [
            ("Precision@k / Recall@k", "Aciertos en el top-k."),
            ("NDCG@k", "Calidad del orden del ranking."),
            ("MAP", "Precisión promedio."),
            ("Cobertura / Diversidad", "Más allá de la exactitud."),
        ],
        [
            "Split por usuario o temporal (leave-last-out).",
            "Evalúa arranque en frío por separado.",
            "Baseline = recomendar lo más popular.",
        ],
        [
            "Evita fuga temporal (no uses el futuro para predecir el pasado).",
            "Vigila el sesgo de popularidad.",
        ],
        "Popularidad global.",
    ),
    FAMILY_VISION: _entry(
        [
            ("Accuracy / F1", "Clasificación de imágenes."),
            ("mAP", "Detección de objetos."),
            ("IoU / Dice", "Segmentación."),
        ],
        [
            "Split estratificado con conjunto de test separado.",
            "Usa data augmentation en entrenamiento, no en test.",
            "Transfer learning: valida el fine-tuning con early stopping.",
        ],
        [
            "Cuida imágenes casi duplicadas entre splits (fuga).",
            "Revisa el desbalance de clases.",
        ],
        "Clase mayoritaria / modelo preentrenado sin ajustar.",
    ),
    FAMILY_GENERATIVE: _entry(
        [
            ("Groundedness / Faithfulness", "Que la respuesta se apoye en el contexto."),
            ("Exactitud / F1 en QA", "Contra un conjunto dorado."),
            ("Tasa de alucinación", "Respuestas no soportadas."),
            ("Latencia p95 y costo/consulta", "Operación y presupuesto."),
        ],
        [
            "Construye un conjunto dorado de preguntas y respuestas.",
            "Evaluación humana o LLM-as-judge con rúbrica.",
            "En RAG, mide también recall@k del recuperador.",
        ],
        [
            "No midas solo fluidez; verifica veracidad y fuentes.",
            "Controla costo y latencia, no solo calidad.",
        ],
        "Prompt simple sin recuperación.",
    ),
}


def evaluation_for(family: str) -> Dict[str, Any]:
    """Return evaluation guidance for a family (regression as safe default)."""
    return EVALUATION.get(family, EVALUATION[FAMILY_REGRESSION])
