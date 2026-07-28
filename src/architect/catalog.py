"""Curated catalog of AI/ML problem families, techniques and deploy targets.

This is the domain knowledge that lets the tool guide an AI developer from a
problem statement ("predict a value from labeled data") to concrete techniques
(regression, gradient boosting, ...), their technical details, costs and where
to deploy them on AWS. All data is curated and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---- Problem families -------------------------------------------------------

FAMILY_REGRESSION = "regression"
FAMILY_CLASSIFICATION = "classification"
FAMILY_CLUSTERING = "clustering"
FAMILY_FORECASTING = "forecasting"
FAMILY_ANOMALY = "anomaly_detection"
FAMILY_RECOMMENDATION = "recommendation"
FAMILY_VISION = "computer_vision"
FAMILY_GENERATIVE = "nlp_generative"
FAMILY_GENERATIVE_MEDIA = "generative_media"

FAMILY_LABELS: Dict[str, str] = {
    FAMILY_REGRESSION: "Regresión (predecir un valor numérico)",
    FAMILY_CLASSIFICATION: "Clasificación (predecir una categoría)",
    FAMILY_CLUSTERING: "Clustering (agrupar sin etiquetas)",
    FAMILY_FORECASTING: "Pronóstico de series temporales",
    FAMILY_ANOMALY: "Detección de anomalías",
    FAMILY_RECOMMENDATION: "Sistemas de recomendación",
    FAMILY_VISION: "Visión por computadora",
    FAMILY_GENERATIVE: "IA generativa / NLP sobre documentos",
    FAMILY_GENERATIVE_MEDIA: "Generación de contenido (imagen/video/audio)",
}


@dataclass(frozen=True)
class Technique:
    key: str
    name: str
    summary: str
    when_to_use: str
    frameworks: List[str]
    complexity: str  # "baja", "media", "alta"
    needs_gpu: bool = False


@dataclass(frozen=True)
class DeployTarget:
    key: str
    name: str
    summary: str
    best_for: str
    base_monthly_usd: float
    gpu: bool = False


# ---- Deploy targets (curated monthly estimates, USD) ------------------------

DEPLOY_TARGETS: Dict[str, DeployTarget] = {
    "lambda": DeployTarget(
        "lambda", "AWS Lambda", "Función serverless para modelos ligeros.",
        "Modelos pequeños y tráfico intermitente", 10.0
    ),
    "sagemaker_serverless": DeployTarget(
        "sagemaker_serverless", "SageMaker Serverless Inference",
        "Endpoint gestionado que escala a cero.",
        "Tráfico variable sin administrar servidores", 35.0
    ),
    "sagemaker_realtime": DeployTarget(
        "sagemaker_realtime", "SageMaker Endpoint (ml.m5.large)",
        "Endpoint CPU de baja latencia constante.",
        "Baja latencia estable en CPU", 84.0
    ),
    "sagemaker_realtime_gpu": DeployTarget(
        "sagemaker_realtime_gpu", "SageMaker Endpoint (ml.g5.xlarge)",
        "Endpoint GPU para modelos grandes/deep.",
        "Modelos deep o de gran tamaño en tiempo real", 1028.0, gpu=True
    ),
    "ecs_fargate": DeployTarget(
        "ecs_fargate", "ECS Fargate", "Contenedor propio con tu API.",
        "APIs contenedizadas a medida", 42.0
    ),
    "batch_transform": DeployTarget(
        "batch_transform", "SageMaker Batch Transform",
        "Inferencia offline por lotes.",
        "Predicción por lotes, no en tiempo real", 20.0
    ),
}


# ---- Technique catalog per family (first entry = recommended default) -------

FAMILY_TECHNIQUES: Dict[str, List[Technique]] = {
    FAMILY_REGRESSION: [
        Technique(
            "gradient_boosting", "Gradient Boosting (XGBoost/LightGBM)",
            "Ensamble de árboles que suele ganar en datos tabulares.",
            "Datos tabulares etiquetados con relaciones no lineales.",
            ["XGBoost", "LightGBM", "scikit-learn"], "media"
        ),
        Technique(
            "linear_regression", "Regresión lineal / Ridge / Lasso",
            "Modelo lineal simple e interpretable, buen baseline.",
            "Relaciones aproximadamente lineales o como línea base.",
            ["scikit-learn"], "baja"
        ),
        Technique(
            "random_forest", "Random Forest",
            "Ensamble robusto con poco tuning.",
            "Baseline no lineal rápido y estable.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "deep_regression", "Red neuronal (MLP)",
            "Red densa para relaciones complejas o mucha data.",
            "Datasets grandes o señales no tabulares.",
            ["PyTorch", "TensorFlow"], "alta", needs_gpu=True
        ),
        Technique(
            "support_vector_regression", "Support Vector Regression (SVR)",
            "Regresión con márgenes y kernels no lineales.",
            "Datasets pequeños/medianos con relaciones no lineales.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "knn_regression", "K-Nearest Neighbors",
            "Predice promediando los vecinos más cercanos.",
            "Baseline simple sin supuestos de forma.",
            ["scikit-learn"], "baja"
        ),
    ],
    FAMILY_CLASSIFICATION: [
        Technique(
            "gradient_boosting_clf", "Gradient Boosting (XGBoost/LightGBM)",
            "Clasificador de árboles potenciados, fuerte en tabular.",
            "Clasificación tabular etiquetada (churn, fraude, scoring).",
            ["XGBoost", "LightGBM", "scikit-learn"], "media"
        ),
        Technique(
            "logistic_regression", "Regresión logística",
            "Clasificador lineal interpretable, buen baseline.",
            "Baseline y problemas linealmente separables.",
            ["scikit-learn"], "baja"
        ),
        Technique(
            "random_forest_clf", "Random Forest",
            "Ensamble robusto multiclase.",
            "Baseline no lineal con poco tuning.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "deep_classifier", "Red neuronal",
            "Red profunda para señales complejas (texto/imagen/tabular grande).",
            "Datos grandes o no tabulares.",
            ["PyTorch", "TensorFlow"], "alta", needs_gpu=True
        ),
        Technique(
            "svm_classifier", "Support Vector Machine (SVM)",
            "Separa clases con márgenes y kernels.",
            "Datasets pequeños/medianos con fronteras claras.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "naive_bayes", "Naive Bayes",
            "Clasificador probabilístico muy rápido.",
            "Texto/conteos y baselines veloces.",
            ["scikit-learn"], "baja"
        ),
        Technique(
            "knn_classifier", "K-Nearest Neighbors",
            "Clasifica por mayoría de los vecinos cercanos.",
            "Baseline simple sin entrenamiento explícito.",
            ["scikit-learn"], "baja"
        ),
    ],
    FAMILY_CLUSTERING: [
        Technique(
            "kmeans", "K-Means",
            "Particiona en k grupos por cercanía.",
            "Segmentación general con clusters aproximadamente esféricos.",
            ["scikit-learn"], "baja"
        ),
        Technique(
            "dbscan", "DBSCAN",
            "Agrupa por densidad, detecta ruido.",
            "Clusters de forma arbitraria y outliers.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "gmm", "Gaussian Mixture",
            "Clustering probabilístico blando.",
            "Pertenencia suave y clusters elípticos.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "hierarchical", "Clustering jerárquico (aglomerativo)",
            "Construye un árbol de agrupamientos (dendrograma).",
            "Explorar estructura y número de clusters.",
            ["scikit-learn", "SciPy"], "media"
        ),
        Technique(
            "hdbscan", "HDBSCAN",
            "Densidad jerárquica; clusters de tamaño variable y ruido.",
            "Densidades variables sin fijar k.",
            ["hdbscan"], "media"
        ),
        Technique(
            "spectral", "Spectral Clustering",
            "Agrupa usando el grafo de similitud.",
            "Clusters no convexos o basados en conectividad.",
            ["scikit-learn"], "media"
        ),
    ],
    FAMILY_FORECASTING: [
        Technique(
            "gradient_boosting_ts", "Gradient Boosting con features de lag",
            "Árboles potenciados sobre variables rezagadas.",
            "Series con estacionalidad y variables externas.",
            ["XGBoost", "LightGBM"], "media"
        ),
        Technique(
            "classical_ts", "ARIMA / ETS",
            "Modelos estadísticos clásicos de series.",
            "Series univariadas con patrón estable.",
            ["statsmodels"], "baja"
        ),
        Technique(
            "prophet", "Prophet",
            "Modelo aditivo con estacionalidad y feriados.",
            "Series de negocio con estacionalidad marcada.",
            ["Prophet"], "baja"
        ),
        Technique(
            "deep_ts", "Deep (LSTM / Temporal Fusion Transformer)",
            "Redes para series largas y multivariadas.",
            "Muchas series y relaciones complejas.",
            ["PyTorch", "TensorFlow"], "alta", needs_gpu=True
        ),
        Technique(
            "sarimax", "SARIMAX",
            "ARIMA estacional con variables exógenas.",
            "Estacionalidad clara y regresores externos.",
            ["statsmodels"], "media"
        ),
        Technique(
            "deepar", "DeepAR / N-BEATS",
            "Modelos probabilísticos profundos para muchas series.",
            "Miles de series relacionadas con incertidumbre.",
            ["GluonTS", "PyTorch"], "alta", needs_gpu=True
        ),
    ],
    FAMILY_ANOMALY: [
        Technique(
            "isolation_forest", "Isolation Forest",
            "Aísla outliers con árboles aleatorios.",
            "Detección no supervisada de anomalías tabulares.",
            ["scikit-learn"], "baja"
        ),
        Technique(
            "one_class_svm", "One-Class SVM",
            "Frontera alrededor de lo normal.",
            "Pocos datos y frontera bien definida.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "autoencoder", "Autoencoder",
            "Reconstruye lo normal; error alto = anomalía.",
            "Señales complejas (series/imágenes) con mucha data.",
            ["PyTorch", "TensorFlow"], "alta", needs_gpu=True
        ),
        Technique(
            "local_outlier_factor", "Local Outlier Factor",
            "Compara densidad local con la de los vecinos.",
            "Anomalías locales en datos de densidad variable.",
            ["scikit-learn"], "media"
        ),
        Technique(
            "elliptic_envelope", "Elliptic Envelope",
            "Ajusta una gaussiana y marca lo que cae fuera.",
            "Datos aproximadamente gaussianos.",
            ["scikit-learn"], "baja"
        ),
    ],
    FAMILY_RECOMMENDATION: [
        Technique(
            "matrix_factorization", "Filtrado colaborativo (factorización)",
            "Factoriza la matriz usuario-ítem.",
            "Historial de interacciones usuario-ítem.",
            ["implicit", "Surprise", "scikit-learn"], "media"
        ),
        Technique(
            "content_based", "Basado en contenido",
            "Recomienda por similitud de atributos.",
            "Pocos datos de interacción; ricos metadatos de ítems.",
            ["scikit-learn"], "baja"
        ),
        Technique(
            "two_tower", "Deep (two-tower)",
            "Embeddings de usuario e ítem con redes.",
            "Catálogos grandes y mucho tráfico.",
            ["TensorFlow Recommenders", "PyTorch"], "alta", needs_gpu=True
        ),
        Technique(
            "popularity_baseline", "Baseline de popularidad",
            "Recomienda lo más popular; referencia mínima.",
            "Arranque en frío y línea base a superar.",
            ["pandas"], "baja"
        ),
        Technique(
            "neural_cf", "Neural Collaborative Filtering",
            "Interacciones usuario-ítem con redes profundas.",
            "Señales de interacción abundantes y no lineales.",
            ["PyTorch", "TensorFlow Recommenders"], "alta", needs_gpu=True
        ),
    ],
    FAMILY_VISION: [
        Technique(
            "transfer_learning", "Transfer learning (CNN preentrenada)",
            "Ajusta una CNN preentrenada a tu dataset.",
            "Clasificación de imágenes con dataset moderado.",
            ["PyTorch", "TensorFlow"], "media", needs_gpu=True
        ),
        Technique(
            "yolo", "Detección de objetos (YOLO)",
            "Detecta y ubica objetos en la imagen.",
            "Localización de objetos en imágenes/video.",
            ["Ultralytics YOLO", "PyTorch"], "alta", needs_gpu=True
        ),
        Technique(
            "vit", "Vision Transformer (ViT)",
            "Transformer para clasificación de imágenes.",
            "Datasets grandes donde una CNN se queda corta.",
            ["PyTorch", "timm"], "alta", needs_gpu=True
        ),
        Technique(
            "segmentation", "Segmentación (U-Net / Mask R-CNN)",
            "Etiqueta la imagen a nivel de píxel/instancia.",
            "Delimitar regiones u objetos con precisión.",
            ["PyTorch", "Detectron2"], "alta", needs_gpu=True
        ),
    ],
    # Generative techniques keep the existing GenAI strategy keys.
    FAMILY_GENERATIVE: [
        Technique(
            "rag", "RAG (recuperación aumentada)",
            "Recupera contexto de un índice y responde con un LLM.",
            "Preguntas sobre un corpus que cambia sin reentrenar.",
            ["LangGraph", "LlamaIndex", "pgvector"], "media"
        ),
        Technique(
            "agents", "Agentes multi-herramienta",
            "LLM que orquesta herramientas en varios pasos.",
            "Tareas que requieren acciones y razonamiento multi-paso.",
            ["LangGraph"], "alta"
        ),
        Technique(
            "lora", "Fine-tuning ligero (LoRA)",
            "Adapta un modelo con pocos pesos entrenables.",
            "Estilo/dominio estable con datos moderados.",
            ["PEFT", "PyTorch"], "alta", needs_gpu=True
        ),
        Technique(
            "fine_tuning", "Fine-tuning completo",
            "Reentrena el modelo sobre tu corpus.",
            "Dominio muy específico y estable; presupuesto alto.",
            ["PyTorch", "PEFT"], "alta", needs_gpu=True
        ),
        Technique(
            "prompting", "Prompt engineering (sin entrenamiento)",
            "Usa un LLM con instrucciones y few-shot, sin entrenar.",
            "Prototipos y tareas simples; el baseline más barato.",
            ["LangChain"], "baja"
        ),
    ],
    FAMILY_GENERATIVE_MEDIA: [
        Technique(
            "pretrained_generation", "Modelo generativo preentrenado (API/endpoint)",
            "Usa un modelo de difusión/generación ya entrenado (texto→imagen/video) vía API o endpoint gestionado.",
            "La mayoría de casos: rápido, sin entrenar y escalable.",
            ["Diffusers", "Bedrock/Replicate API", "ComfyUI"], "media"
        ),
        Technique(
            "diffusion_lora", "Personalización con LoRA (difusión)",
            "Ajusta estilo, marca o personaje con LoRA sobre un modelo de difusión.",
            "Necesitas un estilo propio con pocos datos.",
            ["Diffusers", "PEFT"], "alta", needs_gpu=True
        ),
        Technique(
            "full_diffusion_training", "Entrenar difusión desde cero",
            "Entrena un modelo generativo propio de imagen/video.",
            "Dominio único y presupuesto muy alto (poco común).",
            ["PyTorch"], "alta", needs_gpu=True
        ),
    ],
}


# ---- Keyword detection ------------------------------------------------------

_KEYWORDS = [
    (FAMILY_GENERATIVE_MEDIA, ["generar video", "generar vídeo", "generar imagen",
                               "generar imágen", "generar imagenes", "generar imágenes",
                               "generar audio", "generar música", "crear video",
                               "crear vídeo", "crear imagen", "crear imágen",
                               "crear imagenes", "crear imágenes", "crear audio",
                               "hacer video", "hacer vídeo", "hacer imagen",
                               "texto a video", "texto a imagen", "video generativ",
                               "imagen generativ", "contenido generativ",
                               "síntesis de voz", "voz sintética", "deepfake",
                               "difusión", "stable diffusion", "generación de video",
                               "generación de imagen", "generación de imágenes",
                               "generación de audio"]),
    (FAMILY_GENERATIVE, ["chatbot", "documento", "pdf", "rag", "resumen",
                         "pregunta", "generar texto", "genera texto", "nlp",
                         "llm"]),
    (FAMILY_VISION, ["imagen", "imágenes", "visión", "foto", "objeto", "video",
                     "detección de objeto"]),
    (FAMILY_FORECASTING, ["serie", "pronóstico", "pronosticar", "forecast",
                          "demanda", "ventas futuras", "temporal"]),
    (FAMILY_ANOMALY, ["anomalía", "anomalia", "fraude", "outlier", "atípico"]),
    (FAMILY_RECOMMENDATION, ["recomend", "recommend", "sugerir productos"]),
    (FAMILY_CLUSTERING, ["agrupar", "segmentar", "segmentación", "cluster",
                         "grupos"]),
    (FAMILY_CLASSIFICATION, ["clasificar", "clasificación", "categoría",
                             "categoria", "churn", "spam", "etiqueta de clase"]),
    (FAMILY_REGRESSION, ["predecir", "predicción", "estimar", "valor", "precio",
                         "cantidad", "número", "monto", "regresión"]),
]


def detect_family(description: str) -> str:
    """Best-effort keyword detection of the problem family (a hint, not a verdict)."""
    text = (description or "").lower()
    for family, words in _KEYWORDS:
        if any(word in text for word in words):
            return family
    return FAMILY_REGRESSION


def techniques_for(family: str) -> List[Technique]:
    return FAMILY_TECHNIQUES.get(family, [])


def recommended_technique(family: str) -> Optional[Technique]:
    options = FAMILY_TECHNIQUES.get(family, [])
    return options[0] if options else None


# Techniques that imply heavy training/serving (over-engineering / MLOps flags).
HEAVY_TECHNIQUES = {
    "deep_regression", "deep_classifier", "deep_ts", "autoencoder",
    "two_tower", "transfer_learning", "yolo", "lora", "fine_tuning",
    "diffusion_lora", "full_diffusion_training",
}

GPU_DEPLOY_TARGETS = {key for key, t in DEPLOY_TARGETS.items() if t.gpu}
