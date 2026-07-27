# Design — consensus-engine

## Alcance del primer incremento
El núcleo de consenso será una biblioteca Python sin dependencias externas, compatible con Python 3.9. Usa `@dataclass(frozen=True)` para `AgentVerdict`, `@dataclass` para `ConsensusResult` y `TypedDict` para `GraphState`. Esta elección evita instalar Pydantic o LangGraph antes de definir los contratos de los nodos que los usarán.

`ProblemContext` y `ArchitectureCandidate` se representan por ahora como `dict[str, Any]`: son datos opacos para el consenso. El componente solo inspecciona `AgentVerdict`.

## Modelos y estado
```python
class GraphState(TypedDict):
    context: ProblemContext
    candidate: ArchitectureCandidate
    verdicts: list[AgentVerdict]
    round: int  # 0, 1 o 2
    rejected: list[RejectedCandidate]
    result: Optional[ConsensusResult]

@dataclass
class ConsensusResult:
    architecture: ArchitectureCandidate
    verdicts: list[AgentVerdict]
    accepted_risks: list[str]
    unresolved_risks: list[str]
    rejected: list[RejectedCandidate]
    round_reached: int
    confidence: int
    forced: bool
```

`RejectedCandidate` se define como un `TypedDict` con `candidate`, `rejected_round` y `reasons`; el pipeline valida que los rechazos estén ordenados y correspondan a las re-propuestas anteriores. En la entrega forzada, `unresolved_risks` conserva los riesgos que produjeron los blockers.

## Producto web

### Proceso y rutas
`consensus_web.server` usa exclusivamente `http.server.ThreadingHTTPServer` de la biblioteca estándar. Sirve los únicos recursos estáticos permitidos (`/`, `/app.css`, `/app.js`) desde el paquete y expone:

| Ruta | Método | Uso |
| --- | --- | --- |
| `/` | GET | Interfaz de creación de rondas y visualización del consenso. |
| `/api/health` | GET | Estado y versión, sin datos de solicitudes. |
| `/api/consensus` | POST | Ejecuta una secuencia validada de 1 a 3 rondas. |

La solicitud es JSON con `context` opcional (objeto) y `rounds` (lista). Cada ronda contiene `candidate` (objeto) y `verdicts` (lista de objetos `AgentVerdict`). El adaptador HTTP crea nodos Architect y Review Board deterministas que consumen esas rondas y llama a `run_consensus`; ADR es un no-op porque la API devuelve el resultado directamente. La secuencia debe terminar exactamente en convergencia o entrega forzada: no hay rondas sin usar ni blockers sin siguiente ronda.

### Seguridad de borde
El manejador limita el cuerpo a 1 MiB antes de leerlo, valida tipo y estructura JSON, y nunca deriva rutas de archivos de la entrada. Los errores de validación se envían como JSON sin detalles internos; los fallos inesperados se registran sin devolver trazas. Las cabeceras CSP same-origin, `nosniff`, `DENY` para marcos y `same-origin` para referrer se aplican a todas las respuestas. No se habilita CORS ni persistencia.

### Portabilidad y despliegue
El proceso requiere Python 3.9+ y se inicia por defecto en `127.0.0.1`; los scripts POSIX y Windows no requieren dependencias de ejecución. Un `Dockerfile` no root y `docker-compose.yml` ejecutan el mismo proceso en `0.0.0.0:8080`. El frontend se sirve desde el backend, por lo que no requiere configuración CORS ni un build de Node. Las instrucciones de AWS Free Tier y Hostinger VPS describen el proxy HTTPS externo y no incluyen credenciales ni secretos.

## Validación de veredictos
`AgentVerdict` valida en construcción las reglas del contrato de `requirements.md`. Las funciones públicas también comprueban que reciben una lista no vacía de instancias de ese tipo y que la ronda es un entero entre 0 y 2. Así, datos no estructurados, listas vacías y estados de fallo no accionables producen una excepción explícita en vez de una convergencia accidental.

## Regla de convergencia (función pura, testeable)
```python
def decide(
    verdicts: list[AgentVerdict], round: int
) -> Literal["converge", "re_propose", "force_deliver"]:
    blockers = [
        verdict for verdict in verdicts
        if verdict.verdict == "FAIL"
        and verdict.severity == "blocker"
        and verdict.agent in ("security", "cost")
    ]
    if not blockers:
        return "converge"
    if round == 2:
        return "force_deliver"
    return "re_propose"
```

## `confidence` (calculado, no preguntado)
```python
def confidence(verdicts: list[AgentVerdict]) -> int:
    pass_ratio = pass_count / len(verdicts)
    no_blocker = 0 if any_blocker else 1
    hard_rules_ratio = sum(passed) / sum(total)
    return round_half_up(
        50 * pass_ratio + 30 * no_blocker + 20 * hard_rules_ratio
    )
```

La implementación usa `fractions.Fraction`, no `float`, y aplica redondeo al entero más cercano con empates hacia arriba. Por tanto, su salida no depende de precisión de plataforma ni de un LLM.

## Pipeline ejecutable (sin LangGraph)
El grafo objetivo se implementa como un orquestador síncrono y acotado para no acoplar la política a LangGraph. Sus adaptadores son `Protocol` inyectables:

```python
class ArchitectNode(Protocol):
    def __call__(
        self,
        context: ProblemContext,
        rejected: Sequence[RejectedCandidate],
    ) -> ArchitectureCandidate: ...

class ReviewBoardNode(Protocol):
    def __call__(
        self,
        context: ProblemContext,
        candidate: ArchitectureCandidate,
    ) -> list[AgentVerdict]: ...

class ADRNode(Protocol):
    def __call__(self, result: ConsensusResult) -> None: ...
```

`run_consensus(context, architect, review_board, adr)` ejecuta, como máximo, tres evaluaciones de candidata:
1. Architect recibe el contexto y un historial inicialmente vacío; produce la candidata de la ronda 0.
2. Review Board devuelve los veredictos y `decide` selecciona la transición.
3. En `re_propose` (solo rondas 0 y 1), se añade `{"candidate", "rejected_round", "reasons"}` a `rejected` y se vuelve a Architect.
4. En `converge` o `force_deliver`, se construye el único `ConsensusResult`, se lo entrega a ADR una vez y se lo retorna al llamador.

La decisión de la ronda 2 con blocker se entrega forzadamente; no existe una cuarta generación de candidata. `accepted_risks` y `unresolved_risks` se derivan de los veredictos, se eliminan duplicados manteniendo el orden y son validados por `ConsensusResult`.

Antes de invocar cada adaptador, el orquestador usa `copy.deepcopy` sobre los diccionarios y colecciones del dominio. Los contratos, por tanto, exigen datos copiables. Esto evita que un adaptador pueda modificar la candidata canónica, el historial de rechazos, el contexto del llamador o el resultado retornado. Si un adaptador falla o devuelve un tipo inválido, la excepción se propaga de forma visible.

Un adaptador futuro de LangGraph podrá llamar a este mismo núcleo, pero no cambia sus contratos ni sus reglas de límite de rondas.
