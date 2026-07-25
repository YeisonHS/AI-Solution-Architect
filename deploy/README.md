# Despliegue — AWS Free Tier y Hostinger

La aplicación se empaqueta como una imagen Docker que sirve frontend y backend en el mismo origen. No necesita base de datos, secretos ni variables de entorno obligatorias. Este documento no crea recursos ni modifica cuentas: ejecuta los pasos solo en una cuenta y región que controles.

> **Coste y elegibilidad:** los beneficios Free Tier, tamaños de instancia y cargos de IP/transferencia cambian. Antes de crear recursos, consulta la consola de AWS y configura un presupuesto/alerta. Hostinger compartido normalmente no permite procesos Python persistentes ni Docker: usa un **VPS** o Cloud VPS para ejecutar el backend.

## Verificación previa

En tu máquina o servidor con Docker:
```sh
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:8080/api/health
docker compose logs --tail=100
```

La respuesta esperada es `{"status":"ok","version":"0.1.0"}`. Para detenerlo: `docker compose down`.

## AWS: EC2 elegible para Free Tier

1. Crea una instancia Linux elegible para tu plan Free Tier; usa una clave SSH y limita el puerto 22 a tu IP. Activa alertas de presupuesto antes de continuar.
2. En el Security Group permite `80/tcp` y `443/tcp` al público. **No** abras `8080` al público cuando uses Nginx.
3. Instala Docker y Compose siguiendo la documentación oficial de la distribución elegida. Copia el proyecto al servidor (repositorio privado, SCP o artefacto) sin incluir claves ni archivos `.env` con secretos.
4. En el directorio del proyecto ejecuta:
   ```sh
   docker compose up --build -d
   docker compose ps
   curl -fsS http://127.0.0.1:8080/api/health
   ```
5. Instala Nginx en el host y copia `deploy/nginx-consensus.conf` como bloque de servidor, sustituyendo `example.com` por tu dominio. Valida con `sudo nginx -t` y recarga solo si la validación es correcta.
6. Emite un certificado TLS con tu herramienta aprobada (por ejemplo Certbot) y redirige HTTP a HTTPS. Mantén el puerto 8080 accesible solo desde localhost.

Para actualizaciones:
```sh
docker compose pull
docker compose up --build -d
docker compose ps
```

## Hostinger VPS

1. Contrata un VPS con acceso root/sudo. Un plan de hosting compartido sirve solo archivos estáticos y no puede ejecutar este backend same-origin.
2. Configura un usuario administrador no root, claves SSH y firewall: SSH restringido a tu IP; `80`/`443` públicos; `8080` privado.
3. Instala Docker Engine y Docker Compose Plugin según la distribución del VPS.
4. Sube el proyecto, ejecuta `docker compose up --build -d` y verifica `/api/health` en localhost.
5. Configura Nginx y TLS igual que en AWS. Configura copias del directorio del proyecto y actualiza el sistema según la política de tu organización.

## Nginx y exposición pública

El ejemplo `nginx-consensus.conf` limita el cuerpo a 1 MiB y reenvía al contenedor en loopback. Antes de exponer la aplicación, define una política de autenticación y rate limiting adecuada: el producto es deliberadamente sin usuarios ni persistencia, por lo que cualquier visitante que alcance el proxy puede evaluar solicitudes.

Nunca pongas contraseñas, claves privadas, credenciales AWS ni tokens dentro del repositorio, los argumentos Docker o los JSON enviados desde la interfaz.
