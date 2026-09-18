"""Fuente de datos: Google Places API (New) - Text Search.

Busca empresas con consultas en lenguaje natural orientadas a la intencion
comercial ("bodegas en Funza"), a diferencia de Overpass que filtra por
tags de OpenStreetMap. Requiere GOOGLE_MAPS_API_KEY; si no esta
configurada, search() avisa con un error claro (is_configured() permite
a las rutas detectarlo antes de intentar la busqueda).

Nota de costos (verificado en la documentacion oficial de Google, no
asumido): en Text Search (New), `websiteUri` esta en el nivel "Pro"
(5.000 consultas gratis/mes, luego $32/1000), mientras que el telefono
esta en el nivel "Enterprise" (solo 1.000 gratis/mes, luego $35/1000).
Por eso este servicio NO pide telefono a Google -- se prioriza el nivel
gratuito mas amplio, y el telefono se consigue igual, sin costo
adicional, desde la propia pagina web de la empresa via
contact_finder_service.
"""

import logging
import time

import requests

from config import Config
from models.company import CATEGORY_CHOICES  # noqa: F401 (validacion futura)
from services.data_sources.overpass_service import ZONES as ZONE_INFO

logger = logging.getLogger(__name__)

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Solo campos del nivel Pro (no Enterprise) -- ver nota de costos arriba.
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.primaryType,places.types,places.websiteUri,places.businessStatus"
)

REQUEST_TIMEOUT = 10
REQUEST_DELAY_SECONDS = 0.5

# Frases de busqueda por intencion comercial (punto 4 del alcance). "otra"
# no tiene una frase razonable, igual que en overpass_service.
CATEGORY_QUERY_PHRASES = {
    "bodega": "bodegas",
    "almacenamiento": "centros de almacenamiento",
    "logistica": "empresas de logística",
    "distribuidora": "distribuidoras",
    "mayorista": "almacenes mayoristas",
    "alimentos": "empresas de alimentos con centro de distribución",
    "bebidas": "distribuidoras de bebidas",
    "industria": "empresas de manufactura",
    "importadora": "empresas importadoras",
    "comercializadora": "empresas comercializadoras",
    "transporte": "empresas de transporte de carga",
}

# Evita relanzar la misma consulta muy seguido: a diferencia de Overpass,
# cada consulta aqui consume cuota real de Google. Se resetea si se
# reinicia el servidor (cache en memoria, no en BD -- alcance de un MVP).
_RECENT_QUERIES = {}
_QUERY_COOLDOWN_SECONDS = 6 * 60 * 60


class GooglePlacesServiceError(Exception):
    """Error al consultar Google Places."""


class GooglePlacesNotConfiguredError(GooglePlacesServiceError):
    """No hay GOOGLE_MAPS_API_KEY configurada."""


class InvalidSearchError(GooglePlacesServiceError):
    """Los parametros de busqueda (zonas/categorias) no son validos."""


def is_configured():
    return bool(Config.GOOGLE_MAPS_API_KEY)


def build_query(zone, category):
    phrase = CATEGORY_QUERY_PHRASES.get(category)
    if not phrase:
        raise InvalidSearchError(
            f"La categoria '{category}' no tiene una consulta definida para Google Places"
        )
    if zone not in ZONE_INFO:
        raise InvalidSearchError(f"Zona no soportada: {zone}")

    department = ZONE_INFO[zone]["department"]
    return f"{phrase} en {zone}, {department}, Colombia"


def search(zones, categories):
    """Busca empresas en Google Places y devuelve dicts normalizados (sin
    persistir), en el mismo formato que overpass_service.search()."""
    if not is_configured():
        raise GooglePlacesNotConfiguredError(
            "Google Places no esta configurado (falta GOOGLE_MAPS_API_KEY en .env)"
        )
    if not zones:
        raise InvalidSearchError("Debes seleccionar al menos una zona")

    valid_categories = [c for c in categories if c in CATEGORY_QUERY_PHRASES]
    if not valid_categories:
        raise InvalidSearchError(
            "Ninguna de las categorias seleccionadas tiene consulta definida para Google Places"
        )

    companies = []
    first_request = True

    for zone in zones:
        for category in valid_categories:
            if not first_request:
                time.sleep(REQUEST_DELAY_SECONDS)
            first_request = False

            query = build_query(zone, category)
            try:
                places = _run_text_search(query)
            except GooglePlacesServiceError as exc:
                logger.warning("Fallo la busqueda de Google Places '%s': %s", query, exc)
                continue

            for place in places:
                company = _place_to_company_dict(place, zone, category)
                if company:
                    companies.append(company)

    return companies


def _run_text_search(query):
    cache_key = query.lower()
    now = time.time()
    last_run = _RECENT_QUERIES.get(cache_key)
    if last_run and now - last_run < _QUERY_COOLDOWN_SECONDS:
        logger.info("Consulta de Google Places omitida (repetida hace poco): %s", query)
        return []

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": Config.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {"textQuery": query, "languageCode": "es"}

    try:
        response = requests.post(
            TEXT_SEARCH_URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.RequestException as exc:
        raise GooglePlacesServiceError(f"No se pudo conectar con Google Places: {exc}") from exc

    if response.status_code == 429:
        raise GooglePlacesServiceError("Limite de cuota de Google Places alcanzado")
    if response.status_code in (401, 403):
        raise GooglePlacesServiceError("API key de Google Places invalida o sin permisos")
    if response.status_code != 200:
        raise GooglePlacesServiceError(
            f"Google Places respondio con estado {response.status_code}: {response.text[:300]}"
        )

    _RECENT_QUERIES[cache_key] = now
    return response.json().get("places", [])


def _place_to_company_dict(place, zone, category):
    name = (place.get("displayName") or {}).get("text")
    if not name:
        return None

    location = place.get("location") or {}

    return {
        "name": name,
        "address": place.get("formattedAddress"),
        "city": zone,
        "department": ZONE_INFO[zone]["department"],
        "phone": None,
        "email": None,
        "website": place.get("websiteUri"),
        "category": category,
        "description": None,
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "source": "google_places",
        "source_id": place.get("id"),
    }
