# AI Solution Architect — Hackathon MVP Spec (v0.3)

### Un sistema multiagente autónomo que debate, justifica y audita arquitecturas de IA antes de escribir una sola línea de código.

**Versión:** v0.3 (Reposicionamiento a sistema multiagente + guardarraíles de demo)
**Reto objetivo:** Reto 3 — Agentes especializados
**Plataforma:** Web app + sistema de agentes (LLM cloud + análisis local)
**Cloud de referencia:** AWS (como *target* de la recomendación, no como deploy en vivo)

> **Frase de cierre del pitch:** *"Large Language Models can generate code. Our agents generate defendable architectural decisions."*
> *"La arquitectura no se genera una sola vez; se somete a debate entre agentes especializados hasta convertirse en una decisión técnicamente defendible."*

---

## 0. Posicionamiento

No competimos con Cursor, Claude Code, Copilot ni Kiro — ellos **generan código**. Nosotros respondemos las preguntas que se toman *antes* de escribir código: ¿RAG o Fine-tuning? ¿qué modelo? ¿ECS o SageMaker? ¿cuánto cuesta? ¿qué riesgos tiene? ¿qué alternativa descartamos y por qué? La generación de infraestructura es una **consecuencia**, no el producto.

La diferencia central respecto a la v0.2: la arquitectura **ya no la decide un solo agente**. Emerge del **debate y consenso de un Architecture Review Board**. Eso es lo que convierte esto en un caso genuino de IA agéntica y lo alinea con el Reto 3.

---

## 1. Evolución de versiones

| | v0.1 | v0.2 | v0.3 (esta) |
|---|---|---|---|
| Foco | Producto SaaS "todo en uno" | Agente de decisión + recorte de riesgo | Sistema multiagente de debate/consenso |
| Decisión | Engine único | Engine único → review | **Architect → Board → Consensus (con loop)** |
| Deploy | Real a AWS en vivo | Eliminado → PR a GitHub | Igual: PR a GitHub, sin deploy |
| Riesgo demo | Alto | Bajo | Bajo **si se guiona el escenario** |

Lo que se recortó en v0.2 se mantiene recortado: sin deploy real, sin IAM, sin `terraform apply`, sin Kubernetes/Azure/multi-cloud, sin ejecución de fine-tuning, sin dashboard operativo. El MVP resuelve **una** pregunta:

> **¿Cuál es la mejor arquitectura para mi solución de IA, y por qué es defendible?**

---

## 2. El problema (puntual)

Un dev o tech lead que arranca una app de IA pierde horas decidiendo *cómo* construirla, no *qué* construir. Esas decisiones (RAG vs fine-tuning, modelo, infra AWS, costo, riesgos) se toman con intuición, sin trazabilidad y sin que nadie las audite antes de escribir código. **AI Solution Architect** ataca solo esa fase y produce una decisión **explicable, auditada y trazable** en < 5 minutos.

---

## 3. El Architecture Review Board (el corazón)

En vez de un pipeline lineal, el flujo es un **proceso de consenso**:

```
Problem
  ↓
Architect Agent            → propone una arquitectura candidata
  ↓
Architecture Review Board  → la someten a debate (en paralelo)
  ├─ Security Agent
  ├─ Best Practices Agent
  ├─ Product Agent
  ├─ Cost Optimization Agent
  └─ Devil's Advocate Agent (opcional, acotado)
  ↓
Consensus Agent            → agrega vetos y scores; ¿converge?
  ↓ (si hay veto bloqueante → re-propuesta, máx. 2 rondas)
ADR                        → decisión + alternativas rechazadas + confidence calculado
  ↓
Asset Generator → GitHub PR
```

### 3.1 Miembros del Board

- **Architect Agent** — propone la arquitectura candidata (estrategia, modelo, infra, DB, framework) a partir del `ProblemContext`.
- **Security Agent** — IAM mínimo, secretos, exposición de red, recursos públicos, cifrado.
- **Best Practices Agent** — escalabilidad, calidad de IaC, naming, CI/CD.
- **Product Agent** — alineación con negocio, sobre-ingeniería, riesgo de entrega.
- **Cost Optimization Agent** — estima costo mensual, busca alternativas más baratas, evalúa trade-off costo/rendimiento y **justifica** (ej: "Arquitectura B, −85% de costo con −4 de score → recomendada").
- **Devil's Advocate Agent** *(opcional, 1 ronda, set fijo de preguntas)* — intenta romper la arquitectura: tráfico ×100, presupuesto ↓, latencia < 50 ms, datos que no pueden salir a cloud, corpus que cambia a diario.

### 3.2 El Consensus Agent no es magia — regla explícita

El consenso opera sobre **salidas estructuradas** de cada agente (JSON con `veredicto`, `severidad`, `razón`), no sobre prosa. Regla de convergencia declarada:

- Un **FAIL bloqueante** de Security o Cost fuerza una **re-propuesta** del Architect (máx. 2 rondas).
- Los **WARN** se registran como riesgos aceptados en el ADR, no bloquean.
- Si tras 2 rondas persiste un bloqueo, se entrega la mejor arquitectura disponible con los riesgos marcados explícitamente.

Esto responde la pregunta que hará el jurado ("¿cómo converge?") con una regla, no con hand-waving.

---

## 4. Guardarraíles para que el demo no se rompa

El debate es no-determinista por naturaleza. Cuatro medidas obligatorias:

1. **Escenario guionado.** El caso de demo ("5.000 PDFs que cambian semanalmente + presupuesto bajo") está diseñado para empujar determinísticamente el debate hacia el resultado deseado (Architect propone Fine-tuning → Board lo rechaza → Consensus converge en RAG).
2. **Salidas estructuradas.** Cada agente devuelve JSON, no texto libre → el Consensus razona sobre datos.
3. **Cap de rondas.** Máximo 2 iteraciones de debate para no consumir los 5 minutos.
4. **Números anclados en datos reales.** Los costos del Cost Agent salen de una tabla curada de precios AWS en la KB (no alucinados). El `confidence` del ADR se **calcula** a partir del nivel de acuerdo del Board y de las reglas duras superadas — nunca se le pregunta al LLM "¿qué tan seguro estás?".

---

## 5. Alcance del MVP

### Incluido
- Wizard de entrada (descripción + constraints: presupuesto, hardware, privacidad, tráfico).
- **Hardware Analyzer** → AI Capability Matrix (ver §7).
- **Architect Agent** + **Architecture Review Board** (5–6 agentes) + **Consensus Agent** con loop.
- **ADR** con Rejected Alternatives y confidence calculado.
- Modos de explicación **Beginner / Expert** (switch en cualquier momento).
- Generación de artefactos como archivos: Terraform, Dockerfile, docker-compose, GitHub Actions, diagrama, README, ADR (validados estáticamente, **no ejecutados**).
- Salida final: **PR a GitHub** (vía GitHub MCP) o ZIP.

### Fuera del MVP (roadmap)
Deploy real a AWS, IAM, `terraform apply`, Kubernetes, Azure/GCP, multi-cloud, ejecución de fine-tuning, dashboard operativo.

---

## 6. ADR con Rejected Alternatives

El ADR ya no solo explica la decisión — explica **por qué se descartó cada alternativa**:

```
Recomendación: RAG (pgvector)   ·   Confidence: 92% (calculado)

Rejected Alternatives
  Fine-Tuning
    Motivos: base de conocimiento dinámica · alto costo operativo · ciclos de retraining largos
    Veredicto del Board: Cost FAIL · Product WARN (sobre-ingeniería)
  Agent multi-paso
    Motivos: complejidad innecesaria para el caso · latencia añadida
```

Confidence = f(acuerdo del Board, reglas duras superadas). Trazable, no inventado.

---

## 7. AI Capability Matrix (antes "Readiness Score")

En vez de un número suelto, una matriz visual — el gancho de apertura del demo, y determinístico:

```
AI Capability Matrix
  RAG           ██████████  100%
  Agents        ████████░░   85%
  LoRA          ███████░░░   72%
  Fine-Tuning   ██░░░░░░░░   20%   ← no recomendado en esta máquina
```

Se calcula cruzando CPU/RAM/GPU/VRAM/almacenamiento contra una tabla de requisitos por técnica y modelo.

---

## 8. Terraform NO es el protagonista

Cualquier LLM genera Terraform hoy — no lo vendemos como innovación. Los artefactos son la **consecuencia** del razonamiento del Board. La innovación es el debate previo. En el pitch, los artefactos aparecen al final, en 10 segundos, no como el centro.

---

## 9. Stack sugerido (construible en hackathon)

- **Orquestación:** **LangGraph** — grafo de estados con nodos por agente, aristas de veto y re-entrada al Architect (el loop de consenso). No montar el debate con llamadas encadenadas a mano.
- **LLM motor:** cloud (Claude / GPT) para el razonamiento del Board; opción de modelo local (Ollama) para reforzar el ángulo "corre en tu máquina" de la Capability Matrix.
- **KB / RAG interno:** pgvector o LanceDB con patrones de arquitectura, **tabla curada de precios AWS** y límites de modelos por VRAM.
- **MCPs:** GitHub MCP (crear PR), Filesystem MCP (escribir artefactos). Terraform/AWS MCP quedan como "future-ready".
- **Frontend:** React — wizard, Capability Matrix, vista del debate del Board, ADR con Rejected Alternatives, toggle Beginner/Expert.
- **Kiro:** úsalo como IDE spec-driven para construirlo y muéstralo en el pitch (specs → hooks → implementación). Diferénciate: Kiro construye cualquier código; tú **decides y auditas la arquitectura de IA**.

---

## 10. Flujo del demo (5–7 min, a prueba de fallos)

1. Describo la app: "chatbot sobre 5.000 PDFs que cambian cada semana, presupuesto bajo".
2. **AI Capability Matrix** de la máquina en vivo. *(visual, determinístico)*
3. **Architect Agent** propone **Fine-Tuning**.
4. **El Board debate en vivo:** Security ✗, Cost ✗ (muy caro), Product ✗ (sobre-ingeniería). *(el wow moment)*
5. **Consensus Agent** converge en **RAG** y el **ADR se actualiza automáticamente** con las Rejected Alternatives.
6. Cambio de **Beginner** a **Expert** con un clic.
7. Genero los artefactos (Terraform + Docker + CI + diagrama + README, validados).
8. **Un clic → PR a GitHub** con la infra y el ADR. *(sin deploy, sin credenciales)*
9. Cierre: *"The architecture is not generated once. It is challenged by specialized agents until it becomes technically defensible."*

Ningún paso depende de desplegar en una nube externa en vivo.

---

## 11. Cómo mapea a los criterios (Reto 3)

- **Problema específico:** decisión arquitectónica de IA, debatida y auditada. No es "genera cualquier cosa".
- **Innovación e impacto:** un Board multiagente que debate y converge sobre la arquitectura *antes* de escribir código no existe en los generadores actuales.
- **Uso creativo de RAG / MCPs:** RAG interno sobre patrones + precios AWS reales + límites de modelos; GitHub/Filesystem MCP para el output.
- **Modelos local + cloud:** Capability Matrix con modelo local + razonamiento del Board en cloud.
- **Calidad de implementación:** salidas estructuradas, regla de consenso explícita, artefactos validados, confidence calculado.

---

## 12. Métricas de éxito (realistas)

- Propuesta inicial del Architect en < 60 s.
- Debate del Board + ADR final en < 2 min (máx. 2 rondas).
- Artefactos validados (`terraform validate` / `hadolint` en verde).
- Toda recomendación con justificación trazable, alternativas rechazadas y confidence calculado.

---

## 13. Roadmap post-hackathon

- **Fase 2:** deploy real (ECS/EC2/SageMaker) con credenciales gestionadas, Terraform MCP, Cost Explorer real, Bedrock Agents.
- **Fase 3:** Azure/GCP, plantillas de arquitectura, RBAC, organizaciones, policy engine, compliance, marketplace.

El recorte no tira la visión — la ordena en fases. El hackathon prueba el foso: **el debate multiagente que produce una decisión defendible.**
