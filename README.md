# Consensus Engine

Aplicación web determinista para evaluar rondas de arquitectura con veredictos estructurados. La interfaz y la API se sirven desde el mismo proceso Python: no requiere Node.js, base de datos ni LLM.

## Características
- Política de consenso reproducible: máximo dos re-propuestas y entrega forzada en ronda 2.
- UI responsive para crear de 1 a 3 rondas, ver riesgos, confianza, candidatas rechazadas y resultado final.
- API JSON same-origin: `GET /api/health` y `POST /api/consensus`.
- Sin persistencia de solicitudes; límite de 1 MiB; validación estricta; cabeceras CSP, `nosniff`, anti-frame y referrer.
- Compatible con Python 3.9+ en macOS, Linux y Windows; imagen Docker para servidores.

## Ejecutar localmente

Requisito: Python 3.9 o posterior.

**macOS/Linux**
```sh
sh scripts/run-local.sh
```

**Windows CMD**
```bat
scripts\run-local.bat
```

**Windows PowerShell**
```powershell
.\scripts\run-local.ps1
```

Abre `http://127.0.0.1:8080`. Para cambiar el puerto: `PORT=8090 sh scripts/run-local.sh` (PowerShell: `$env:PORT=8090; .\scripts\run-local.ps1`). El servidor se enlaza a loopback por defecto; usa `--host 0.0.0.0` únicamente detrás de un firewall/proxy configurado.

## Pruebas
```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

## API y despliegue
- Contrato detallado: [`docs/API.md`](docs/API.md).
- Docker local o servidor: `docker compose up --build -d`, después abre `http://localhost:8080`.
- Guía de AWS Free Tier y Hostinger VPS: [`deploy/README.md`](deploy/README.md).

No hay credenciales ni variables secretas requeridas por la aplicación. Si se publica en Internet, termina TLS en Nginx/Caddy/ALB y aplica autenticación/rate limiting de acuerdo con tu organización.
# AI-Solution-Architect
