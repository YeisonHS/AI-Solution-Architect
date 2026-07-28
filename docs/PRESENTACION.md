# AI Solution Architect — Presentación de producto

> *"Large Language Models can generate code. Our agents generate defendable architectural decisions."*

**En vivo:** https://korvino.cloud/consensus/ · **Repo:** https://github.com/YeisonHS/AI-Solution-Architect

---

## 1. Qué es (en una frase)

Un **sistema multiagente** que **debate, justifica y audita** la arquitectura de una solución de IA/ML **antes de escribir una sola línea de código**, y entrega una decisión **explicable, trazable y con confianza calculada** — más los artefactos para empezar.

No compite con Kiro/Copilot/Cursor: ellos **generan código**; nosotros respondemos lo que se decide **antes** de codificar (¿RAG o fine-tuning?, ¿regresión o clustering?, ¿qué modelo?, ¿qué infra AWS?, ¿cuánto cuesta?, ¿qué riesgos?, ¿qué se descarta y por qué?).

---

## 2. Categoría relacionada

**Reto 3 — Agentes especializados.** El corazón del producto es un **Architecture Review Board**: agentes con roles definidos (Security, Cost, Best Practices, Product, Devil's Advocate) que producen **salidas estructuradas** y un **Consensus Agent** que aplica una **regla explícita de convergencia** con loop acotado. No es un LLM contestando de una pasada: es un **debate adversarial que converge en una decisión defendible**.

Encaja además con los criterios transversales: uso de conocimiento curado (RAG interno de precios AWS y límites por VRAM), modelos local + cloud (Capability Matrix local; razonamiento del Board conectable a cloud), y calidad de implementación (salidas estructuradas, regla de consenso, confidence calculado, artefactos validados).

---

## 3. Impacto

- **Ahorra la fase más cara y menos trazable:** decidir *cómo* construir. Pasa de horas de intuición a una **decisión auditada en minutos**.
- **Decisiones defendibles:** cada recomendación viene con **alternativas rechazadas y por qué**, y un **confidence calculado** (no inventado por un LLM).
- **Cubre todo el espectro de IA/ML:** regresión, clasificación, clustering, forecasting, anomalías, recomendación, visión y generativo (8 familias, 4–7 técnicas cada una).
- **Números anclados:** costos por técnica y despliegue desde una **tabla curada de precios AWS**, con presupuesto y *what-if*.
- **Accionable de punta a punta:** valida datos (EDA), recomienda técnica, dice **dónde desplegar y cuánto cuesta**, **cómo medir/validar**, un **plan de implementación** y genera los **artefactos** (Terraform, Docker, CI, ADR, stubs).
- **A prueba de fallos y sin costos ocultos:** 100% determinista, sin dependencias externas, sin persistir datos.

---

## 4. Diferenciación

| | Generadores de código (Kiro/Copilot/Cursor) | **AI Solution Architect** |
|---|---|---|
| Capa | Escriben el código | **Deciden y auditan** qué construir *antes* de codificar |
| Salida | Código/archivos | **Decisión + ADR + alternativas rechazadas + confidence** |
| Mecanismo | Un modelo responde | **Debate multiagente** con regla de consenso y loop acotado |
| Números | Estimación del LLM | **Precios AWS curados** (no alucinados) |
| Datos | — | **EDA en memoria** (correlaciones, enumeradores, objetivo→familia), sin almacenar |

El foso no es la generación (eso lo hace cualquiera): es **el mecanismo determinista de debate + la auditabilidad + los datos reales**. Y es **complementario**: este producto lo construimos **con Kiro**.

Flujo completo que ningún generador ofrece de corrido:
**Router (¿EDA?) → EDA → señales → Board (técnica + costo + despliegue + ADR) → métricas y validación → what-if → plan → artefactos.**

---

## 5. Pitch de 5 minutos (guion)

**0:00–0:30 — El problema.** "Antes de escribir código, un equipo de IA pierde horas decidiendo *cómo* construir, sin trazabilidad y sin que nadie lo audite. Eso es lo que atacamos."

**0:30–1:00 — La tesis.** "Los LLM generan código. Nuestros **agentes generan decisiones de arquitectura defendibles**. La arquitectura no se genera una vez: se **somete a debate** hasta ser técnicamente defendible."

**1:00–1:45 — Caso generativo (el wow).** Describo: *"chatbot sobre 5.000 PDFs que cambian cada semana, presupuesto bajo."*
- **Capability Matrix** de la máquina (determinista).
- **Architect propone Fine-Tuning** → el **Board lo rechaza**: Cost FAIL ($7.607/mes > presupuesto), Product/Best-Practices/Devil's Advocate WARN.
- **Consensus converge en RAG** · **confidence 100%** · **ADR con Rejected Alternatives** actualizado solo.

**1:45–2:45 — Caso ML clásico (amplitud).** *"Quiero predecir el precio a partir de un dataset etiquetado."*
- El **Router** sugiere **EDA**; el **Validador de datos** (en memoria) detecta tipos, normaliza enumeradores, marca correlaciones y sugiere **columna objetivo → regresión**.
- El Board recomienda **Gradient Boosting**, **SageMaker Serverless ~$45/mes**, con **menú de técnicas** y **opciones de despliegue con costos**.

**2:45–3:30 — Accionable.** Muestro **Métricas y validación** (RMSE/MAE/R², split correcto, baseline), el **Plan de implementación** (6 pasos con esfuerzo) y **What-if** (cómo cambia con $50 vs $1.000).

**3:30–4:15 — Del debate al código.** Un clic → **Descargar artefactos (ZIP)**: Terraform, Dockerfile, CI, `ADR.md`, stubs. "Los artefactos son la **consecuencia** del razonamiento, no el producto." Toggle **Beginner/Expert**.

**4:15–5:00 — Cierre.** "Determinista, sin dependencias, sin almacenar datos, **desplegado en vivo** y con 78 pruebas en verde. *The architecture is not generated once. It is challenged by specialized agents until it becomes technically defensible.*"

---

## 6. Por qué debería ganar

- **Responde el Reto 3 de forma literal:** agentes especializados que **debaten y convergen**, con regla explícita y confidence calculado — no hand-waving.
- **Innovación real y defendible:** un Board multiagente que audita la arquitectura *antes* de codificar no existe en los generadores actuales; el foso está en el **mecanismo + auditabilidad + datos curados**.
- **Amplitud + profundidad:** 8 familias de problema, 4–7 técnicas cada una, costos y despliegues AWS, EDA, métricas, plan y artefactos. Sirve para IA generativa **y** ML clásico.
- **Demo a prueba de fallos:** 100% determinista y guionado (guardarraíles del spec), sin depender de una nube externa en vivo ni de un LLM inestable.
- **Calidad de ingeniería:** sin dependencias externas, **78 pruebas** en verde, empaquetado en Docker, **desplegado en producción** (`korvino.cloud/consensus/`) y versionado en GitHub.
- **Impacto claro:** convierte una decisión difusa y sin trazabilidad en un **ADR auditable en minutos**, con el camino a producción incluido.

---

## 7. Estado actual

- **En vivo:** https://korvino.cloud/consensus/
- **Cobertura:** Router · EDA · Board (5 agentes) · Consensus/ADR · Catálogo (8 familias) · Costos · Despliegues · Métricas/validación · What-if · Plan · Artefactos ZIP.
- **Roadmap (post-hackathon):** LLM cloud para enriquecer explicaciones, PR automático a GitHub, deploy real (Terraform apply/SageMaker), multi-cloud.
