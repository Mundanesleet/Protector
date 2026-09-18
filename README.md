# Prospector C&D

Herramienta de prospección comercial para encontrar, investigar y gestionar empresas ubicadas en Bogotá y municipios cercanos (Funza, Mosquera, Chía, Cajicá, Cota y Madrid) que puedan necesitar servicios de cargue y descargue de mercancías: bodegas, centros de distribución, empresas logísticas, distribuidoras, mayoristas, importadoras, comercializadoras, empresas de alimentos/bebidas, industriales, etc.

La aplicación **no contacta empresas automáticamente ni hace spam**. Encuentra empresas en varias fuentes públicas, investiga y completa sus datos de contacto, elimina duplicados/cadenas, y da una herramienta ordenada para hacerles seguimiento comercial manual. El envío final de cualquier mensaje siempre lo hace la persona, desde su propio correo o WhatsApp.

## Descripción del problema

La primera versión solo usaba OpenStreetMap (Overpass API): encontraba muchas empresas, pero casi ninguna tenía teléfono, email o sitio web, y cadenas grandes (Carulla, UNO, etc.) aparecían decenas de veces como si cada sucursal fuera una empresa distinta — cantidad sin calidad. Esta versión convierte el sistema de "buscador de empresas" a "buscador + investigador de empresas": combina varias fuentes, elimina duplicados/cadenas, y completa los datos de contacto que faltan antes de mostrar el resultado.

## Tecnologías

- **Backend:** Python, Flask, Flask-SQLAlchemy, SQLite, openpyxl (exportación a Excel)
- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript vanilla
- **Fuentes de búsqueda:** OpenStreetMap (Overpass API, gratis) + Google Places API (New) (opcional, nivel gratis)
- **Investigación/enriquecimiento:** Brave Search API (opcional, nivel gratis) + extracción directa de la web propia de cada empresa
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

La aplicación queda disponible en `http://127.0.0.1:5000/`. La base de datos SQLite se crea automáticamente (`instance/prospector.db`) en el primer arranque; si ya existía de una versión anterior, las columnas nuevas se agregan solas sin perder datos (ver "Migraciones" más abajo).

Sin configurar ninguna key, la aplicación funciona igual usando solo OpenStreetMap — Google Places y Brave Search son mejoras opcionales.

### Variables de entorno (`.env`)

| Variable | Descripción | Obligatoria |
|---|---|---|
| `SECRET_KEY` | Clave de Flask | No (tiene default de desarrollo) |
| `DATABASE_URL` | URI de SQLAlchemy | No |
| `OVERPASS_API_URL` / `OVERPASS_TIMEOUT` | Overpass API | No |
| `GOOGLE_MAPS_API_KEY` | Habilita Google Places como fuente de búsqueda | No — sin ella, solo se usa Overpass |
| `BRAVE_SEARCH_API_KEY` | Habilita la investigación con Brave Search | No — sin ella, el botón "Investigar" avisa que falta configurar |

**Cómo obtener `GOOGLE_MAPS_API_KEY`:** consola de Google Cloud → crear proyecto → activar facturación (obligatorio aunque el uso quede en $0 dentro del nivel gratis) → habilitar "Places API (New)" → Credentials → Create API Key.

**Cómo obtener `BRAVE_SEARCH_API_KEY`:** [api-dashboard.search.brave.com](https://api-dashboard.search.brave.com/) → crear cuenta → nueva API key (no requiere tarjeta para el nivel gratis).

## Arquitectura

```
protector/
├── app.py                              # Application factory de Flask + migraciones ligeras
├── config.py                           # Configuracion via variables de entorno
├── database/__init__.py                # Instancia SQLAlchemy (db) + ensure_schema_migrations()
├── models/                             # Company, Prospect, Note, Location, Source
├── routes/                             # Blueprints: controladores delgados
│   ├── main_routes.py                  # Vista del dashboard
│   ├── company_routes.py               # /api/search, /api/companies*
│   ├── prospect_routes.py              # /api/prospects*
│   └── api_routes.py                   # /api/stats, /api/meta
├── services/
│   ├── data_sources/
│   │   ├── overpass_service.py         # Busqueda por tags de OpenStreetMap (gratis)
│   │   ├── google_places_service.py    # Busqueda por intencion comercial (Google Places)
│   │   └── brave_search_service.py     # Investigacion web (sitio oficial, Facebook, LinkedIn)
│   ├── company_service.py              # Dedup/cadenas, filtros, normalizacion, export a Excel
│   ├── company_enrichment_service.py   # Orquesta Brave + contact_finder por empresa
│   ├── contact_finder_service.py       # Extrae email/WhatsApp de la web propia de una empresa
│   └── message_template_service.py     # Mensaje sugerido y editable por categoria
├── templates/                          # Jinja2 + Bootstrap 5
└── static/
    ├── css/style.css
    └── js/{app,dashboard,map}.js
```

**Por qué esta separación:**

- `services/data_sources/` aísla cada fuente de búsqueda externa. Las tres exponen la misma forma de resultado (dict con `name`, `address`, `phone`, `website`, `source`, `source_id`, etc.), así que `company_service.save_companies()` no necesita saber de dónde vino cada empresa.
- `company_enrichment_service.py` está separado de `company_service.py` porque orquesta *otro* servicio (`brave_search_service`) más el ya existente `contact_finder_service` — es lógica de composición, no de persistencia.
- `models/`: `Company` son los datos de la empresa; `Location` son sucursales legítimas de una empresa con varias sedes reales (no cadenas grandes, esas se excluyen); `Source` guarda de dónde vino cada dato individual (campo + tipo de fuente + URL + fecha); `Prospect`/`Note` son la gestión comercial, separada a propósito de los datos de la empresa.

### Migraciones

SQLite/`db.create_all()` crea tablas nuevas pero no agrega columnas a una tabla que ya existe con datos. `database/ensure_schema_migrations()` corre `ALTER TABLE` para las columnas nuevas la primera vez que hacen falta, y se llama automáticamente al arrancar la app — no hay que hacer nada manual, y los datos existentes nunca se borran.

### Deduplicación y exclusión de cadenas

- Cada `Company` tiene una restricción única `(source, source_id)`; sin eso, se identifica por nombre + dirección + coordenadas.
- **Cadenas/franquicias** (Carulla, UNO, etc.): se normaliza el nombre (sin acentos, números ni sufijos de sucursal) y si **3 o más** ubicaciones comparten el mismo nombre normalizado, se excluyen **todas** — no son buenos prospectos, ya tienen su propia logística. El botón **"Limpiar cadenas duplicadas"** aplica esto retroactivamente a datos guardados antes de este cambio.
- **Teléfonos**: se normalizan a un formato consistente (`+57 XXXXXXXXXX`) para que `"+57 601 1234567"`, `"(601) 1234567"` y `"6011234567"` no se traten como datos distintos.

### Búsqueda multi-fuente

`POST /api/search` acepta `sources: ["overpass", "google_places"]`. Si se piden varias, se corren todas y se combinan los resultados; si una falla (incluido "no configurada"), se reporta como advertencia sin tumbar la búsqueda completa mientras al menos una fuente funcione.

- **Overpass** (siempre disponible, sin key): filtra por tags de OpenStreetMap.
- **Google Places** (opcional): usa Text Search (New) con consultas en lenguaje natural por intención ("bodegas en Funza", "empresas de logística en Cota"). **No pide teléfono a Google a propósito** — verificado en la documentación oficial, el campo teléfono está en el nivel de precio "Enterprise" (solo 1.000 consultas gratis/mes), mientras que `website` está en "Pro" (5.000 gratis/mes). El teléfono se consigue igual, gratis, desde la propia web de la empresa.

### Investigación/enriquecimiento (por empresa, bajo demanda)

Desde la ficha de cada empresa:

- **Buscar contacto en su web**: una sola solicitud a la página oficial ya conocida, extrae email/WhatsApp visibles por texto.
- **Investigar (Google + Brave Search)**: si falta el sitio web, lo busca con Brave (descartando explícitamente resultados que sean directorios/redes sociales — si no hay un resultado confiable, no adivina); busca perfiles públicos de Facebook/LinkedIn (solo guarda la URL pública, nunca intenta acceder a su contenido); si encuentra un sitio nuevo, extrae de ahí email/teléfono. Cada dato guardado queda registrado en `Source` con su procedencia. No sobreescribe datos ya confirmados, y no vuelve a gastar cuota de Brave si la misma empresa ya se investigó en las últimas 24 horas.

Se eligió **bajo demanda por empresa** (no un proceso automático en lote) para que el usuario controle exactamente cuánta cuota gratuita de Brave Search se gasta, y porque enviar mensajes o investigar cientos de empresas automáticamente sin supervisión iba en contra del alcance original del proyecto (no spam).

### Mensaje sugerido (sin envío automático)

Un borrador editable por categoría, con botones **Abrir en correo**/**Abrir en WhatsApp** que abren tu propio cliente con el destinatario y mensaje ya cargados — el clic final de enviar siempre lo das tú.

### ¿Por qué SQLite y no Excel como base de datos?

SQLite ya es gratis (es un archivo local, igual que sería un Excel) y evita los problemas reales de usar una hoja de cálculo como almacenamiento de una app web: bloqueo del archivo si lo tienes abierto mientras la app escribe, y tener que reimplementar a mano la deduplicación y las relaciones que aquí ya resuelve el ORM. El botón **Exportar a Excel** genera un `.xlsx` bajo demanda como respaldo portable, sin ese riesgo.

## Uso

1. En **Buscar empresas**, selecciona zonas, categorías y fuente(s) (OpenStreetMap siempre disponible; Google Places si configuraste la key).
2. **BUSCAR EMPRESAS**: se consultan las fuentes elegidas, se excluyen cadenas/duplicados, y se guardan.
3. Filtra la tabla por ciudad, categoría, estado, teléfono/website, o busca por nombre.
4. En cada fila: **Ver** (ficha completa), **Guardar** (crear prospecto gestionable), **Editar** (corregir datos a mano).
5. En la ficha, si falta información: **Buscar contacto en su web** (rápido, solo su sitio) o **Investigar (Google + Brave Search)** (más profundo: sitio + redes sociales + contacto).
6. Ajusta el **mensaje sugerido** y usa **Abrir en correo**/**Abrir en WhatsApp** para contactarla tú mismo.
7. **Exportar a Excel** cuando quieras un respaldo de lo que ves en la tabla (con los filtros aplicados).

## Referencia de la API

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/search` | Busca empresas (`zones`, `categories`, `sources`: `overpass`/`google_places`) y las guarda sin duplicar |
| `GET` | `/api/companies` | Lista empresas (filtros: `city`, `category`, `status`, `q`, `has_phone`, `has_website`) |
| `GET` | `/api/companies/export` | Descarga en `.xlsx` las empresas (mismos filtros que arriba) |
| `GET` | `/api/companies/<id>` | Detalle de una empresa (incluye prospecto, notas, fuentes por dato y mensaje sugerido) |
| `POST` | `/api/companies/<id>/find-contact` | Busca email/WhatsApp en la web ya conocida de la empresa |
| `POST` | `/api/companies/<id>/enrich` | Investiga con Brave Search + web propia (`force: true` para saltar el enfriamiento de 24h) |
| `POST` | `/api/companies/cleanup-chains` | Limpia retroactivamente cadenas/franquicias ya guardadas |
| `PUT` | `/api/companies/<id>` | Edición manual de una empresa |
| `POST` | `/api/companies/<id>/save` | Guarda una empresa como prospecto (idempotente) |
| `PUT` | `/api/prospects/<id>` | Cambia el estado comercial de un prospecto |
| `POST` | `/api/prospects/<id>/notes` | Agrega una nota comercial |
| `GET` | `/api/stats` | Estadísticas para las tarjetas del dashboard |
| `GET` | `/api/meta` | Zonas, categorías y estados disponibles (usado por el frontend) |

Todas las respuestas son JSON. Los errores nunca exponen detalles técnicos al usuario (`{"error": "mensaje amigable"}`); el detalle técnico queda en el log del servidor. Ninguna API key llega nunca al frontend — todas las llamadas externas se hacen desde el backend.

## Cuotas gratuitas y costos (verificado en la documentación oficial de cada proveedor, no asumido)

| Fuente | Nivel gratis | Costo después |
|---|---|---|
| Overpass API (OpenStreetMap) | Ilimitado, pero es un recurso público compartido: puede responder lento o con error en horas de alta demanda | Gratis siempre |
| Google Places Text Search (campos usados: nombre, dirección, ubicación, website — nivel "Pro") | 5.000 solicitudes/mes | US$32 por cada 1.000 adicionales |
| Brave Search API | US$5 en crédito automático/mes (≈1.000 búsquedas) | US$5 por cada 1.000 adicionales |

**Recomendaciones para no superar la cuota:**
- No repitas la misma búsqueda de zona+categoría muy seguido — `google_places_service.py` ya evita relanzar la misma consulta dentro de 6 horas.
- Usa "Investigar (Google + Brave Search)" solo en las empresas que realmente te interesan, no en todas — es una acción por empresa, no un proceso masivo. El sistema tampoco vuelve a investigar una empresa ya investigada en las últimas 24 horas salvo que lo fuerces.
- Revisa tu consumo real en la consola de Google Cloud y en el dashboard de Brave antes de asumir que sigues en el nivel gratis.

## Limitaciones conocidas

- Overpass: las zonas se referencian por ID de relación OSM fijo, no por nombre (un filtro de país para desambiguar saturaba el servidor público; nombres como "Madrid" o "Cota" son ambiguos a nivel mundial).
- Ni Overpass ni Google Places dan email directamente — siempre se obtiene, cuando existe públicamente, desde la propia web de la empresa o desde Brave Search.
- La detección de cadenas es por coincidencia de nombre normalizado (3+ ubicaciones); una cadena con muy pocas sucursales visibles en una sola búsqueda podría no detectarse hasta que aparezca de nuevo en otra búsqueda o tras usar "Limpiar cadenas duplicadas".
- El enriquecimiento con Brave Search es por empresa, no en lote automático — investigar 300+ empresas a fondo significa 300+ clics (a propósito, para no gastar cuota ni enviar nada sin supervisión).
- No hay NIT/razón social automáticos: esos campos existen en el modelo pero solo se llenan si se editan manualmente (ninguna de las fuentes actuales los expone de forma confiable).

## Roadmap

- Migración de SQLite a PostgreSQL.
- Despliegue en un servicio cloud (Render/Railway/PythonAnywhere).
- Autenticación y usuarios.
- Bot de Discord para notificar nuevas empresas encontradas.

No implementado todavía (a propósito): login/registro, pagos, envío automático de WhatsApp/email, scraping agresivo de redes sociales, IA generativa, Docker.
