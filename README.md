# AI Solution Architect

> *"Large Language Models can generate code. Our agents generate defendable architectural decisions."*

Sistema **multiagente** que **debate, justifica y audita** la arquitectura de una solución de IA/ML **antes de escribir código**, y entrega una decisión **explicable, trazable y con confianza calculada**, más los artefactos para empezar.

No compite con los generadores de código (Kiro/Copilot/Cursor): responde lo que se decide *antes* de codificar — ¿RAG o fine-tuning?, ¿regresión o clustering?, ¿qué modelo?, ¿qué infra AWS?, ¿cuánto cuesta?, ¿qué riesgos?, ¿qué se descarta y por qué?

- **En vivo:** https://korvino.cloud/consensus/
- **Reto objetivo:** Reto 3 — Agentes especializados.
- **Stack:** Python 3.9+, biblioteca estándar (sin dependencias de ejecución). Frontend estático same-origin. Determinista y a prueba de fallos.

## Cómo funciona

```
Problema → Router (¿EDA?) → EDA (opcional) → Architect Agent
        → Architecture Review Board (Security · Cost · Best Practices · Product · Devil's Advocate)
        → Consensus Agent (regla explícita, máx. 2 rondas, confidence calculado)
        → ADR con Rejected Alternatives → Métricas y validación → What-if → Plan → Artefactos (ZIP)
```

El consenso opera sobre **veredictos estructurados** (JSON), no sobre prosa. Solo **Security** y **Cost** pueden bloquear; el resto advierte. El `confidence` se **calcula** del acuerdo del Board y las reglas duras superadas — nunca se le pregunta al LLM. Los costos salen de una **tabla curada de precios AWS**.

## Características

- **AI Capability Matrix** determinista según tu hardware (con autodetección best-effort de CPU/RAM y Apple Silicon en el navegador).
- **Router** que sugiere cuándo conviene un EDA vs una recomendación directa.
- **Validador de datos (EDA)** en memoria (nunca almacena): tipos, enumeradores + encoding, correlaciones, ranking de variables vs objetivo, detección de fechas (→ forecasting) y aviso de faltantes/casi-constantes.
- **9 familias de problema** (regresión, clasificación, clustering, forecasting, anomalías, recomendación, visión, IA generativa/NLP, generación de contenido) con 3–7 técnicas cada una.
- **Costos y opciones de despliegue AWS** por técnica (Lambda, SageMaker Serverless/Realtime/GPU, ECS, Batch).
- **ADR con Rejected Alternatives** y confidence calculado.
- **Métricas y validación** por familia (qué medir y cómo validar).
- **Señales avanzadas** (interpretabilidad, latencia, desbalance, modo de servicio) que ponderan técnica/despliegue y el Board.
- **What-if**: compara la recomendación al variar presupuesto/privacidad.
- **Plan de implementación** accionable (6 pasos con esfuerzo).
- **Generación de artefactos** (Terraform, Dockerfile, CI, README, ADR, stubs) descargables como ZIP.
- **Modos Beginner / Expert.**

## Ejecutar localmente

Requisito: Python 3.9 o posterior.

```sh
# macOS/Linux
sh scripts/run-local.sh
# Windows CMD
scripts\run-local.bat
# Windows PowerShell
.\scripts\run-local.ps1
```

Abre `http://127.0.0.1:8080`. Para cambiar el puerto: `PORT=8090 sh scripts/run-local.sh`. El servidor se enlaza a loopback por defecto.

## API (JSON, same-origin)

| Método y ruta | Uso |
| --- | --- |
| `GET /api/health` | Estado y versión. |
| `POST /api/route` | Sugiere EDA vs recomendación directa. |
| `POST /api/eda` | Analiza un CSV en memoria (no persiste). |
| `POST /api/architect` | Ejecuta Architect → Board → ADR y devuelve la decisión completa. |
| `POST /api/evaluate` | Compara varias opciones y recomienda (evaluador de opciones). |
| `POST /api/whatif` | Compara la recomendación en varios escenarios. |
| `POST /api/artifacts` · `POST /api/artifacts.zip` | Genera los artefactos (JSON o descarga ZIP). |
| `POST /api/consensus` | Contrato de rondas de bajo nivel (integraciones). |

Límite de 1 MiB por solicitud, validación estricta, sin persistencia, cabeceras CSP/`nosniff`/anti-frame/referrer, sin CORS. Detalle: [`docs/API.md`](docs/API.md).

## Pruebas

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

## Despliegue

- Docker: `docker compose up --build -d`, luego `http://localhost:8080`.
- Guía AWS Free Tier / Hostinger VPS: [`deploy/README.md`](deploy/README.md).
- El LLM cloud es **conectable** (proveedor por defecto determinista, guardarraíl de demo). AWS es *target* de la recomendación, no hay deploy en vivo.

## Documentación

- Presentación del producto: [`docs/PRESENTACION.md`](docs/PRESENTACION.md)
- Especificación MVP: [`AI-Solution-Architect_MVP-Spec.md`](AI-Solution-Architect_MVP-Spec.md)
- Requisitos, diseño y tareas: [`requirements.md`](requirements.md) · [`design.md`](design.md) · [`tasks.md`](tasks.md)

No se requieren credenciales ni variables secretas. Si se publica en Internet, termina TLS en un proxy (Nginx/Caddy/ALB) y aplica autenticación/rate limiting según tu organización.
