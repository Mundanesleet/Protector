# Prospector C&D

Herramienta de prospección comercial para encontrar, organizar y gestionar empresas ubicadas en Bogotá y municipios cercanos (Funza, Mosquera, Chía, Cajicá, Cota y Madrid) que puedan necesitar servicios de cargue y descargue de mercancías: bodegas, centros de distribución, empresas logísticas, distribuidoras, mayoristas, importadoras, comercializadoras, empresas de alimentos/bebidas, industriales, etc.

La aplicación **no contacta empresas automáticamente ni hace spam**. Su objetivo es encontrar prospectos comerciales a partir de datos públicos, extraer sus datos de contacto (teléfono, email, website) y dar una herramienta ordenada para hacerles seguimiento comercial manual.

## Descripción del problema

Encontrar manualmente, una por una, las empresas de una zona que podrían necesitar un servicio de cargue/descargue es lento y desorganizado (búsquedas sueltas en Google Maps, hojas de cálculo, sin seguimiento del estado comercial de cada contacto). Prospector C&D automatiza la parte de *descubrimiento* (consulta datos abiertos de OpenStreetMap), organiza los datos de contacto de cada empresa, y ofrece un flujo de gestión comercial (estados, notas) para cada empresa que se decide perseguir como prospecto. En cualquier momento se puede exportar todo a un archivo Excel como respaldo portable.

## Tecnologías

- **Backend:** Python, Flask, Flask-SQLAlchemy, SQLite, openpyxl (exportación a Excel)
- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript vanilla
- **Datos:** OpenStreetMap vía Overpass API
- **Mapa:** Leaflet + OpenStreetMap

## Instalación

```bash
git clone https://github.com/Mundanesleet/Protector.git
cd Protector

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS

python app.py
```

La aplicación queda disponible en `http://127.0.0.1:5000/`. La base de datos SQLite se crea automáticamente (`instance/prospector.db`) en el primer arranque.

### Variables de entorno (`.env`)

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Clave de Flask | `dev-secret-key` |
| `DATABASE_URL` | URI de SQLAlchemy | `sqlite:///prospector.db` |
| `OVERPASS_API_URL` | Endpoint de Overpass | `https://overpass-api.de/api/interpreter` |
| `OVERPASS_TIMEOUT` | Timeout de la consulta (segundos) | `30` |

## Arquitectura

```
protector/
├── app.py                          # Application factory de Flask
├── config.py                       # Configuracion via variables de entorno
├── database/__init__.py            # Instancia SQLAlchemy (db), sin logica
├── models/                         # Company, Prospect, Note (SQLAlchemy)
├── routes/                         # Blueprints: controladores delgados
│   ├── main_routes.py              # Vista del dashboard
│   ├── company_routes.py           # /api/search, /api/companies*
│   ├── prospect_routes.py          # /api/prospects*
│   └── api_routes.py               # /api/stats, /api/meta
├── services/
│   ├── data_sources/
│   │   └── overpass_service.py     # Consulta y normaliza datos de OSM
│   └── company_service.py          # Deduplicacion, filtros, gestion comercial, export a Excel
├── templates/                      # Jinja2 + Bootstrap 5
└── static/
    ├── css/style.css
    └── js/{app,dashboard,map}.js
```

**Por qué esta separación:**

- `models/` separa **Company** (datos de la empresa tal como se encontraron en la fuente) de **Prospect** (gestión comercial: estado, notas). Una empresa se convierte en prospecto solo cuando el usuario la guarda explícitamente.
- `services/data_sources/` aísla la lógica específica de cada fuente de datos. Hoy solo existe `overpass_service.py`; una futura fuente (p. ej. `google_places_service.py`) se agrega ahí sin tocar el resto de la app.
- `services/company_service.py` concentra la deduplicación, los filtros, la gestión comercial y la exportación a Excel, para que las rutas de Flask solo reciban la petición, llamen al servicio y devuelvan JSON (o el archivo).

### Deduplicación

Cada `Company` tiene una restricción única `(source, source_id)`. Si Overpass no trae un identificador utilizable, se usa como respaldo la combinación nombre + dirección + coordenadas. Repetir una búsqueda no crea registros duplicados: actualiza los existentes.

### ¿Por qué SQLite y no Excel como base de datos?

SQLite ya es gratis (es un archivo local, igual que sería un Excel) y evita los problemas reales de usar una hoja de cálculo como almacenamiento de una app web: bloqueo del archivo si lo tienes abierto mientras la app escribe, y tener que reimplementar a mano la deduplicación y las relaciones Company↔Prospect↔Note que aquí ya resuelve el ORM. SQLite sigue siendo la fuente de verdad; el botón **Exportar a Excel** del dashboard genera un `.xlsx` bajo demanda como respaldo portable, sin ese riesgo.

## Uso

1. Abre el dashboard (`/`) y en la sección **Buscar empresas** selecciona una o más zonas y categorías.
2. Haz clic en **BUSCAR EMPRESAS**. La app consulta Overpass, normaliza los resultados y los guarda evitando duplicados.
3. La tabla y el mapa se actualizan con las empresas encontradas. Puedes filtrar por ciudad, categoría, estado comercial, nombre, o si tienen teléfono/website.
4. En cada fila:
   - **Ver** abre la ficha completa (información de contacto, gestión comercial y notas).
   - **Guardar** convierte la empresa encontrada en un prospecto gestionable (estado inicial "Sin contactar").
   - **Editar** permite corregir o enriquecer manualmente los datos de la empresa.
5. Desde la ficha de un prospecto puedes cambiar su estado comercial (Contactado, Interesado, Cliente, etc.) y agregar notas de seguimiento.
6. **Exportar a Excel** (arriba de la tabla) descarga un `.xlsx` con las empresas actualmente filtradas: nombre, ciudad, categoría, dirección, teléfono, email, website y estado comercial.

## Referencia de la API

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/search` | Busca empresas en Overpass (`zones`, `categories`) y las guarda sin duplicar |
| `GET` | `/api/companies` | Lista empresas (filtros: `city`, `category`, `status`, `q`, `has_phone`, `has_website`) |
| `GET` | `/api/companies/export` | Descarga en `.xlsx` las empresas (mismos filtros que arriba) |
| `GET` | `/api/companies/<id>` | Detalle de una empresa (incluye prospecto y notas si existen) |
| `PUT` | `/api/companies/<id>` | Edición manual de una empresa |
| `POST` | `/api/companies/<id>/save` | Guarda una empresa como prospecto (idempotente) |
| `PUT` | `/api/prospects/<id>` | Cambia el estado comercial de un prospecto |
| `POST` | `/api/prospects/<id>/notes` | Agrega una nota comercial |
| `GET` | `/api/stats` | Estadísticas para las tarjetas del dashboard |
| `GET` | `/api/meta` | Zonas, categorías y estados disponibles (usado por el frontend) |

Todas las respuestas son JSON. Los errores nunca exponen detalles técnicos al usuario (`{"error": "mensaje amigable"}`); el detalle técnico queda en el log del servidor.

## Limitaciones conocidas (Overpass/OpenStreetMap)

- Las zonas se referencian por ID de relación OSM fijo, no por nombre: un filtro de país para desambiguar nombres saturaba el servidor público de Overpass, y nombres como "Madrid" o "Cota" son ambiguos a nivel mundial.
- Overpass es un recurso público compartido: la app espera 1 segundo entre consultas de zonas distintas y puede recibir 429/504 en horas de alta demanda (se maneja como error amigable, no como caída de la app).
- Muchos datos (teléfono, email, website) no están disponibles en OpenStreetMap para negocios pequeños; esos campos quedan vacíos en vez de inventarse.

## Roadmap

- **Fase 2:** Enriquecimiento con Google Places u otra fuente (teléfonos, websites, reseñas).
- **Fase 3:** Bot de Discord para notificar nuevas empresas encontradas.
- **Fase 4:** Migración de SQLite a PostgreSQL.
- **Fase 5:** Despliegue en un servicio cloud (Render/Railway).
- **Fase 6:** Autenticación y usuarios.

No implementado todavía (a propósito, para mantener el MVP simple): login/registro, pagos, envío automático de WhatsApp/email, scraping agresivo, Google Places, IA, Discord, PostgreSQL, Docker.
