# Watering Reminder

Bot de Telegram que recuerda regar tus plantas. Cada planta tiene un intervalo de riego para
verano y otro para invierno; el bot calcula la temporada según la **zona horaria** que eliges y
te avisa a las **08:00 hora local**. Si no confirmas, insiste cada 4 horas (08:00, 12:00, 16:00,
20:00) hasta que confirmes.

Especificación y decisiones: [`specs/001-plant-watering-reminders/`](specs/001-plant-watering-reminders/).

## Comandos del bot

| Comando | Qué hace |
|---|---|
| `/start` | Muestra los comandos disponibles |
| `/zona` | Elige tu zona horaria (región → zona, o escribe `America/Santiago`) |
| `/agregar` | Registra una planta: nombre, tipo, días en verano, días en invierno |
| `/plantas` | Lista tus plantas y su próximo riego |
| `/eliminar` | Elimina una planta (con confirmación) |
| `/cancelar` | Cancela el registro en curso |

Temporadas: hemisferio sur, verano octubre–marzo; hemisferio norte, verano abril–septiembre.

## Variables de entorno

Ver `.env.example`. Nunca subas `.env` a git.

| Variable | Uso |
|---|---|
| `BOT_TOKEN` | Token de BotFather |
| `DATABASE_URL` | PostgreSQL |
| `RUN_MODE` | `polling` (local) o `webhook` (producción, por defecto) |
| `WEBHOOK_SECRET`, `WEBHOOK_SECRET_TOKEN`, `RENDER_EXTERNAL_URL` | Solo en modo webhook |
| `CLOCK_OFFSET_HOURS` | Adelanta el reloj del bot para probar sin esperar las 08:00 |
| `TEST_DATABASE_URL` | Base para los tests de PostgreSQL |

## Ejecutar localmente con Docker

```bash
cp .env.example .env        # completa BOT_TOKEN
docker compose up --build   # PostgreSQL + bot en modo polling
curl http://localhost:8000/healthz
```

## Tests

```bash
devbox shell
uv sync
docker compose up -d db
export TEST_DATABASE_URL=postgresql://waterbot:waterbot@localhost:5432/waterbot_test
uv run pytest
```

Sin Docker: `uv pip install pgserver` y `uv run pytest` levanta un PostgreSQL embebido
automáticamente si `TEST_DATABASE_URL` no está definida. Sin ninguna de las dos opciones, los
tests de PostgreSQL se omiten.

Lint: `uv run ruff check .`

## Despliegue (Render + UptimeRobot)

1. Crea la base PostgreSQL (por ejemplo en Neon) y copia su `DATABASE_URL`.
2. Crea el bot con BotFather y genera dos valores aleatorios para `WEBHOOK_SECRET` y
   `WEBHOOK_SECRET_TOKEN`.
3. En Render crea un *Web Service* desde este repositorio (`render.yaml`, plan gratis) y define
   las variables de entorno en el panel.
4. Comprueba `https://<servicio>.onrender.com/healthz` (debe responder 200).
5. En UptimeRobot crea un monitor HTTP(s) para esa URL cada 10 minutos, para que Render no
   duerma la instancia.

Los términos de los planes gratuitos cambian: revísalos antes de desplegar.
