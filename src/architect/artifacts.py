"""Deterministic artifact generation from an ADR.

Produces starter files (README, ADR, Dockerfile, requirements, a training/serving
stub, Terraform scaffold and a CI workflow) as plain text. Artifacts are a
consequence of the Board's decision (spec §8) and are meant to be reviewed, not
executed blindly.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .catalog import DEPLOY_TARGETS
from .evaluation import evaluation_for
from .plan import implementation_plan
from .techniques import resolve_family
from .models import ArchitectureDecisionRecord, ProblemContext


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:40] or "ai-solution")


def generate_files(
    context: ProblemContext, adr: ArchitectureDecisionRecord
) -> List[Dict[str, str]]:
    rec = adr.recommendation
    project = _slug(context.description)
    deploy = DEPLOY_TARGETS.get(rec.deploy_target or "", None)
    deploy_name = deploy.name if deploy else (rec.infrastructure or "AWS")
    cost = rec.estimated_monthly_usd or 0.0

    files: List[Dict[str, str]] = []

    def add(path: str, content: str) -> None:
        files.append({"path": path, "content": content.strip() + "\n"})

    add("README.md", _readme(project, context, rec, deploy_name, cost, adr))
    add("docs/ADR.md", _adr_md(context, adr, deploy_name, cost))
    add("requirements.txt", _requirements(rec.framework))
    add("src/train.py", _train_stub(rec.strategy, rec.model, rec.framework))
    add("src/serve.py", _serve_stub(rec.strategy))
    add("Dockerfile", _dockerfile())
    add("infra/main.tf", _terraform(project, rec.deploy_target or "sagemaker_serverless"))
    add(".github/workflows/ci.yml", _ci_workflow())
    return files


def _readme(project, context, rec, deploy_name, cost, adr) -> str:
    return (
        "# {project}\n\n"
        "Proyecto generado por **AI Solution Architect**. Los artefactos son la\n"
        "consecuencia de la decisión auditada del Architecture Review Board.\n\n"
        "## Problema\n{description}\n\n"
        "## Decisión recomendada\n"
        "- **Estrategia/Técnica:** {strategy}\n"
        "- **Modelo/algoritmo:** {model}\n"
        "- **Framework:** {framework}\n"
        "- **Infraestructura:** {infra}\n"
        "- **Despliegue:** {deploy}\n"
        "- **Costo estimado:** ${cost:,.0f}/mes\n"
        "- **Confianza (calculada):** {confidence}%\n\n"
        "## Estructura\n"
        "- `src/train.py` — entrenamiento (stub).\n"
        "- `src/serve.py` — servicio de inferencia (stub).\n"
        "- `infra/main.tf` — scaffold de Terraform.\n"
        "- `docs/ADR.md` — decisión y alternativas rechazadas.\n\n"
        "> Revisa y valida los artefactos (`terraform validate`, linters) antes de usarlos.\n"
    ).format(
        project=project,
        description=context.description,
        strategy=rec.strategy,
        model=rec.model,
        framework=rec.framework,
        infra=rec.infrastructure,
        deploy=deploy_name,
        cost=cost,
        confidence=adr.confidence,
    )


def _adr_md(context, adr, deploy_name, cost) -> str:
    rec = adr.recommendation
    lines = [
        "# Architecture Decision Record",
        "",
        "## Contexto",
        context.description,
        "",
        "## Decisión",
        "Recomendación: **{}** ({})  ·  Confidence: **{}%** (calculado)".format(
            rec.strategy, rec.model, adr.confidence
        ),
        "",
        "- Infraestructura: {}".format(rec.infrastructure),
        "- Despliegue: {} (~${:,.0f}/mes)".format(deploy_name, cost),
        "- Framework: {}".format(rec.framework),
        "- Rondas de debate: {}{}".format(
            adr.rounds, " (entrega forzada)" if adr.forced else ""
        ),
        "",
    ]
    if adr.accepted_risks:
        lines.append("## Riesgos aceptados")
        lines.extend("- {}".format(r) for r in adr.accepted_risks)
        lines.append("")
    if adr.unresolved_risks:
        lines.append("## Riesgos no resueltos")
        lines.extend("- {}".format(r) for r in adr.unresolved_risks)
        lines.append("")
    lines.append("## Rejected Alternatives")
    if not adr.rejected_alternatives:
        lines.append("Ninguna: la primera propuesta convergió.")
    else:
        for alt in adr.rejected_alternatives:
            lines.append("### {}".format(alt.strategy))
            lines.append("Veredicto del Board: {}".format(alt.board_summary))
            lines.extend("- {}".format(r) for r in alt.reasons)
            lines.append("")

    evaluation = evaluation_for(resolve_family(context))
    lines.append("## Métricas y validación")
    lines.append("Métricas sugeridas:")
    lines.extend(
        "- **{}**: {}".format(m["name"], m["note"]) for m in evaluation["metrics"]
    )
    lines.append("")
    lines.append("Validación:")
    lines.extend("- {}".format(v) for v in evaluation["validation"])
    lines.append("")
    lines.append("Baseline a superar: {}".format(evaluation["baseline"]))
    lines.append("")
    lines.append("Errores comunes a evitar:")
    lines.extend("- {}".format(p) for p in evaluation["pitfalls"])

    plan = implementation_plan(context, adr)
    lines.append("")
    lines.append("## Plan de implementación")
    for step in plan:
        lines.append("- **{}** (esfuerzo {}): {}".format(
            step["title"], step["effort"], step["detail"]
        ))
    return "\n".join(lines)


def _requirements(framework: str) -> str:
    base = {"fastapi", "uvicorn", "pydantic"}
    fw = framework.lower()
    if "xgboost" in fw:
        base.update({"xgboost", "scikit-learn", "pandas"})
    elif "lightgbm" in fw:
        base.update({"lightgbm", "scikit-learn", "pandas"})
    elif "scikit" in fw:
        base.update({"scikit-learn", "pandas"})
    elif "pytorch" in fw:
        base.update({"torch", "numpy"})
    elif "tensorflow" in fw:
        base.update({"tensorflow", "numpy"})
    elif "statsmodels" in fw:
        base.update({"statsmodels", "pandas"})
    elif "prophet" in fw:
        base.update({"prophet", "pandas"})
    elif "langgraph" in fw or "llama" in fw:
        base.update({"langgraph", "langchain", "boto3"})
    else:
        base.update({"scikit-learn", "pandas"})
    return "\n".join(sorted(base))


def _train_stub(strategy: str, model: str, framework: str) -> str:
    return (
        '"""Entrenamiento (stub) para la estrategia recomendada: {strategy}.\n\n'
        "Modelo/algoritmo: {model}\nFramework: {framework}\n"
        'Rellena la carga de datos y el guardado del artefacto entrenado.\n"""\n\n'
        "from pathlib import Path\n\n\n"
        "def load_data():\n"
        "    # TODO: cargar tu dataset (S3, parquet, etc.)\n"
        "    raise NotImplementedError\n\n\n"
        "def train(data):\n"
        "    # TODO: entrenar {model} con {framework}.\n"
        "    raise NotImplementedError\n\n\n"
        'def main() -> None:\n'
        "    data = load_data()\n"
        "    model = train(data)\n"
        '    Path("artifacts").mkdir(exist_ok=True)\n'
        '    print("Modelo entrenado; guarda el artefacto en artifacts/.")\n\n\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    ).format(strategy=strategy, model=model, framework=framework)


def _serve_stub(strategy: str) -> str:
    return (
        '"""Servicio de inferencia (stub) con FastAPI."""\n\n'
        "from fastapi import FastAPI\n"
        "from pydantic import BaseModel\n\n"
        'app = FastAPI(title="AI Solution Architect - {strategy}")\n\n\n'
        "class PredictRequest(BaseModel):\n"
        "    features: dict\n\n\n"
        '@app.get("/health")\n'
        "def health() -> dict:\n"
        '    return {{"status": "ok"}}\n\n\n'
        '@app.post("/predict")\n'
        "def predict(request: PredictRequest) -> dict:\n"
        "    # TODO: cargar el modelo entrenado y predecir.\n"
        '    return {{"prediction": None, "received": request.features}}\n'
    ).format(strategy=strategy)


def _dockerfile() -> str:
    return (
        "FROM python:3.12-slim\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\n"
        "WORKDIR /app\n"
        "COPY requirements.txt .\n"
        "RUN pip install --no-cache-dir -r requirements.txt\n"
        "COPY src ./src\n"
        "EXPOSE 8080\n"
        'CMD ["uvicorn", "src.serve:app", "--host", "0.0.0.0", "--port", "8080"]\n'
    )


def _terraform(project: str, deploy_target: str) -> str:
    template = (
        "terraform {\n"
        '  required_version = ">= 1.5.0"\n'
        "  required_providers {\n"
        "    aws = {\n"
        '      source  = "hashicorp/aws"\n'
        '      version = "~> 5.0"\n'
        "    }\n"
        "  }\n"
        "}\n\n"
        'variable "region" {\n'
        '  type    = string\n'
        '  default = "us-east-1"\n'
        "}\n\n"
        'provider "aws" {\n'
        "  region = var.region\n"
        "}\n\n"
        "# Bucket para artefactos del modelo y datasets.\n"
        'resource "aws_s3_bucket" "artifacts" {\n'
        '  bucket = "__PROJECT__-artifacts"\n'
        "}\n\n"
        "# Objetivo de despliegue recomendado: __DEPLOY__\n"
        "# Este scaffold deja el bucket listo; añade aquí el recurso de serving\n"
        "# (SageMaker endpoint, Lambda o ECS) según el despliegue elegido.\n"
    )
    return template.replace("__PROJECT__", project).replace("__DEPLOY__", deploy_target)


def _ci_workflow() -> str:
    return (
        "name: ci\n"
        "on:\n"
        "  push:\n"
        "    branches: [ main ]\n"
        "  pull_request:\n"
        "jobs:\n"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - uses: actions/setup-python@v5\n"
        "        with:\n"
        '          python-version: "3.12"\n'
        "      - run: pip install -r requirements.txt\n"
        "      - run: python -m compileall src\n"
    )
