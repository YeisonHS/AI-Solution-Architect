# API web — consensus-engine

Base local: `http://127.0.0.1:8080`. La aplicación no persiste solicitudes ni requiere autenticación porque solo evalúa datos enviados en cada petición. Para exponerla públicamente, sitúala tras HTTPS y aplica control de acceso/rate limiting en el proxy.

## `GET /api/health`

Respuesta `200`:
```json
{"status":"ok","version":"0.1.0"}
```

## `POST /api/consensus`

Requiere `Content-Type: application/json` y un cuerpo máximo de 1 MiB. Solo permite las claves raíz `context` y `rounds`; `context` es opcional y por defecto es `{}`.

```json
{
  "context": {"project": "checkout"},
  "rounds": [
    {
      "candidate": {"name": "Arquitectura inicial", "database": "managed"},
      "verdicts": [
        {
          "agent": "security",
          "verdict": "PASS",
          "severity": "info",
          "risk": null,
          "hard_rules_passed": 2,
          "hard_rules_total": 2
        },
        {
          "agent": "reliability",
          "verdict": "WARN",
          "severity": "warning",
          "risk": "Probar la recuperación ante fallos antes del despliegue.",
          "hard_rules_passed": 1,
          "hard_rules_total": 1
        }
      ]
    }
  ]
}
```

Cada ronda debe tener exactamente `candidate` y `verdicts`. Cada veredicto debe incluir todos los campos mostrados y cumplir el contrato de `requirements.md`. `PASS` usa `severity: "info"` y `risk: null`; `WARN` usa `warning` y riesgo no vacío; `FAIL` solo puede ser de `security` o `cost`, con `blocker`, riesgo no vacío y al menos una regla dura no superada.

Si hay blocker en las rondas 0 o 1, se debe aportar la siguiente ronda. Si no hay blocker (o al alcanzar ronda 2), la secuencia termina ahí; las rondas adicionales son un error `400` para evitar que se ignoren datos.

Respuesta `200`:
```json
{
  "result": {
    "architecture": {"name": "Arquitectura inicial", "database": "managed"},
    "verdicts": [],
    "accepted_risks": ["Probar la recuperación ante fallos antes del despliegue."],
    "unresolved_risks": [],
    "rejected": [],
    "round_reached": 0,
    "confidence": 75,
    "forced": false
  }
}
```

Errores de cliente devuelven `{"error": "mensaje seguro"}` con `400`, `404`, `405`, `411`, `413` o `415`. La API no habilita CORS; la interfaz incluida se consume same-origin.

## `POST /api/evaluate`

Evalúa varias opciones con el Board determinista (agentes `security`, `cost`, `reliability`) y devuelve una recomendación con ranking. Es el endpoint que usa la interfaz.

Requiere `Content-Type: application/json` (máximo 1 MiB). Claves raíz: `options` (obligatoria, 1 a 5), `budget_usd` y `project` (opcionales).

Cada opción exige `name`, `encryption_at_rest` y `authentication`. Son opcionales `description`, `public_network`, `has_backups` y `monthly_cost_usd`.

```json
{
  "project": "Base de datos para checkout",
  "budget_usd": 200,
  "options": [
    {
      "name": "Postgres administrado",
      "encryption_at_rest": true,
      "authentication": true,
      "public_network": false,
      "has_backups": true,
      "monthly_cost_usd": 120
    },
    {
      "name": "Cache pública sin cifrado",
      "encryption_at_rest": false,
      "authentication": false,
      "public_network": true,
      "monthly_cost_usd": 40
    }
  ]
}
```

Reglas del Board:
- `security`: falla (blocker) si no cifra en reposo, no exige autenticación, o se expone públicamente sin autenticación.
- `cost`: falla si el costo supera el presupuesto; advierte si supera el 80%; en otro caso pasa. Sin presupuesto o sin costo, pasa.
- `reliability`: advierte (nunca bloquea) si la opción no declara copias de seguridad.

Respuesta `200`:
```json
{
  "recommendation": {
    "name": "Postgres administrado",
    "description": null,
    "confidence": 100,
    "forced": false,
    "strengths": ["security", "cost", "reliability"],
    "warnings": [],
    "blockers": []
  },
  "comparison": [
    {
      "rank": 1,
      "name": "Postgres administrado",
      "confidence": 100,
      "blocked": false,
      "recommended": true,
      "strengths": ["security", "cost", "reliability"],
      "warnings": [],
      "blockers": [],
      "verdicts": []
    }
  ]
}
```

Se recomienda la opción no bloqueada de mayor `confidence`. Si todas están bloqueadas, se devuelve la de mayor `confidence` con `forced: true`.

