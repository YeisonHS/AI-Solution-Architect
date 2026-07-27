# Requirements — consensus-engine

## Introducción
El Consensus Agent agrega los veredictos estructurados del Board, aplica una regla de convergencia explícita y decide si converge o devuelve una re-propuesta al Architect. El ciclo está acotado y sus decisiones no dependen de prosa ni de un LLM.

## Contrato de entrada

### `AgentVerdict`
El sistema acepta una lista **no vacía** de objetos `AgentVerdict`; cualquier objeto que no cumpla este contrato se rechaza antes de decidir.

| Campo | Tipo y regla |
| --- | --- |
| `agent` | Identificador canónico en minúsculas. Los agentes que pueden bloquear en este incremento son `security` y `cost`. |
| `verdict` | Uno de `PASS`, `WARN` o `FAIL`. |
| `severity` | `info` para `PASS`, `warning` para `WARN` y `blocker` para `FAIL`. |
| `risk` | Ausente para `PASS`; texto no vacío para `WARN` y `FAIL`. |
| `hard_rules_passed` | Entero no negativo. |
| `hard_rules_total` | Entero mayor que cero; `hard_rules_passed <= hard_rules_total`. |

Para que los estados sean accionables y no haya `FAIL` silenciosos: un `PASS` o `WARN` debe haber superado todas sus reglas duras, y un `FAIL` debe proceder de `security` o `cost`, ser `blocker` y tener al menos una regla dura no superada. Añadir otros tipos de fallo o nuevos agentes bloqueantes requiere ampliar explícitamente la política de convergencia.

## Requisitos (EARS)

### R1 — Agregación estructurada
- The system shall operar únicamente sobre `list[AgentVerdict]` estructurados y validados, nunca sobre prosa.

### R2 — Regla de convergencia
- When `security` o `cost` devuelven `FAIL` con severidad `blocker`, the system shall solicitar una re-propuesta al Architect Agent, salvo el límite de R3.
- While solo queden veredictos `WARN` junto con `PASS`, the system shall registrar sus `risk` como riesgos aceptados y proceder a converger.
- When todos los veredictos válidos son `PASS` o `WARN`, the system shall marcar la arquitectura como convergida.

### R3 — Cap de rondas
- The system shall permitir como máximo dos re-propuestas: las transiciones de ronda `0 → 1` y `1 → 2`.
- When se evalúa la ronda `2` y persiste un `blocker`, the system shall entregar la mejor arquitectura disponible, con `forced=True` y los riesgos bloqueantes en `unresolved_risks`.

### R4 — `confidence` calculado
- The system shall calcular `confidence` (entero de 0 a 100) solo a partir de los veredictos validados; nunca se le preguntará al LLM.
- `pass_ratio = número de PASS / número total de veredictos`.
- `no_blocker = 1` si no hay un blocker de `security` o `cost`; en otro caso, `0`.
- `hard_rules_ratio = sum(hard_rules_passed) / sum(hard_rules_total)`.
- El valor será `50 * pass_ratio + 30 * no_blocker + 20 * hard_rules_ratio`, redondeado al entero más cercano con empates hacia arriba. Los cálculos se harán con aritmética exacta para que sean reproducibles.

### R5 — Salida
- The system shall producir un `ConsensusResult` con la arquitectura final opaca para este componente, el detalle de veredictos, riesgos aceptados, riesgos no resueltos, candidatas rechazadas, ronda alcanzada, `confidence` y `forced`.
- Los riesgos aceptados son los `risk` de `WARN`, sin duplicados y en orden de aparición. Los riesgos no resueltos son los `risk` de blockers al entregar forzadamente.

### R6 — Adaptadores del pipeline
- The system shall invocar `Architect(context, rejected)` una vez por cada ronda evaluada. Debe devolver una `ArchitectureCandidate` como diccionario copiable.
- The system shall invocar `ReviewBoard(context, candidate)` una vez por candidata. Debe devolver una `list[AgentVerdict]` no vacía y válida.
- When una candidata recibe un blocker en las rondas 0 o 1, the system shall añadir un `RejectedCandidate` con `candidate`, `rejected_round` y los `reasons` de los blockers antes de volver a invocar Architect.
- The system shall invocar `ADR(result)` exactamente una vez al converger o forzar la entrega. Su valor de retorno no cambia el resultado de consenso.
- The system shall pasar copias defensivas de `context`, `candidate`, `rejected` y el resultado entregado a los adaptadores. Las excepciones de un adaptador se propagan; el orquestador no usa resultados parciales ni hace fallbacks silenciosos.

### R7 — Producto web y API
- The system shall servir una aplicación web estática same-origin y una API JSON desde un único proceso Python, sin requerir Node.js ni servicios externos.
- When se recibe `POST /api/consensus` con una solicitud válida de una a tres rondas, the system shall ejecutar el pipeline y devolver el `ConsensusResult` serializado en JSON.
- The system shall exponer `GET /api/health` para comprobaciones de disponibilidad y `GET /` para la interfaz.
- The system shall rechazar rondas sobrantes, rondas insuficientes para un blocker y campos JSON desconocidos; los datos de entrada nunca se persisten.

### R8 — Operación segura y multiplataforma
- The system shall aceptar como máximo 1 MiB por solicitud JSON y exigir `Content-Type: application/json` en el endpoint de consenso.
- The system shall responder con errores JSON sin trazas internas y con códigos HTTP apropiados (`400`, `404`, `405`, `411`, `413`, `415`, `500`).
- The system shall enviar cabeceras de seguridad (`Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) y no habilitar CORS por defecto.
- The system shall ejecutarse de forma local en macOS, Windows y Linux con Python 3.9+, enlazando por defecto solo a `127.0.0.1`; un despliegue de contenedor podrá optar explícitamente por `0.0.0.0`.

### R9 — Board evaluador automático
- The system shall evaluar cada opción con un Review Board determinista formado por un `security` agent y un `cost` agent que pueden bloquear, y un `reliability` agent que solo advierte; ningún veredicto proviene del usuario ni de un LLM.
- The `security` agent shall aplicar reglas duras sobre atributos de la opción (cifrado en reposo, autenticación, exposición pública) y emitir `FAIL` blocker cuando incumpla alguna, indicando el motivo.
- The `cost` agent shall comparar el costo mensual de la opción con el presupuesto de la necesidad: `FAIL` blocker si lo supera, `WARN` si se acerca al límite, `PASS` en otro caso o si no hay restricción declarada.
- The `reliability` agent shall emitir `WARN` cuando la opción no declare copias de seguridad y `PASS` en otro caso.

### R10 — Comparación y recomendación
- When se recibe `POST /api/evaluate` con una necesidad y de una a cinco opciones descritas por atributos, the system shall evaluar cada opción con el Board y devolver: la recomendación, un ranking con `confidence` por opción, y los motivos de fortalezas, advertencias y bloqueos.
- The system shall recomendar la opción no bloqueada de mayor `confidence`; si todas están bloqueadas, the system shall entregar la de mayor `confidence` marcándola como `forced` con sus riesgos no resueltos.
- The system shall mantener `POST /api/consensus` con el contrato de rondas para integraciones existentes.

## Criterios de aceptación
- Un blocker de `security`/`cost` dispara `re_propose` en las rondas 0 y 1.
- Un blocker en la ronda 2 produce `force_deliver`; nunca hay más de dos re-propuestas.
- `confidence` es una función pura y determinística de un conjunto válido de veredictos.
- Solo `WARN` (o `WARN` mezclados con `PASS`) converge y conserva los riesgos aceptados.
- Datos vacíos o que incumplen el contrato se rechazan; no se interpretan como consenso.
- El pipeline conserva dos candidatas rechazadas y sus motivos cuando un blocker persiste hasta la ronda 2; Architect y ADR no pueden mutar el estado interno del orquestador.
- La UI carga desde el servidor local y puede enviar un caso válido al endpoint para mostrar resultado, riesgos y rondas.
- La API mantiene los límites de cuerpo y validación al recibir errores de cliente, y no requiere dependencias distintas de Python estándar en tiempo de ejecución.
