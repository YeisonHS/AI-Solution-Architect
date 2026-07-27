# Tasks — consensus-engine

- [x] 1. Definir `GraphState`, `AgentVerdict`, `RejectedCandidate` y `ConsensusResult` con `dataclass`/`TypedDict` sin dependencias externas.
- [x] 2. Implementar `decide(verdicts, round)` y `confidence(verdicts)` como funciones puras, exactas y reproducibles.
- [x] 3. Construir el pipeline síncrono `architect → review_board → consensus → (architect | adr)` con límite de rondas, registro de rechazos y copias defensivas.
- [x] 4. Implementar producto web same-origin: frontend estático responsive, `GET /api/health` y `POST /api/consensus` con validación y cabeceras de seguridad.
- [x] 5. Preparar ejecución multiplataforma: scripts macOS/Linux, Windows CMD/PowerShell, wheel con assets y Docker Compose no-root.
- [x] 6. Documentar API, operación local, AWS Free Tier y Hostinger VPS; el hosting compartido de Hostinger no puede ejecutar el backend persistente.
- [x] 7. Validar dominio, pipeline y HTTP (16 pruebas), compilación, wheel instalado con frontend y arranque POSIX. Docker no se validó localmente porque Docker no está instalado.
