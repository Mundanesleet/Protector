"""Fuente de datos: OpenStreetMap via Overpass API.

Construye consultas Overpass QL dinamicas a partir de zonas y categorias,
las ejecuta y normaliza los resultados a diccionarios listos para poblar
el modelo Company. No escribe en la base de datos (eso es
responsabilidad de company_service.py en una fase posterior).
"""

import logging
import time

import requests

from config import Config
from models.company import CATEGORY_CHOICES

logger = logging.getLogger(__name__)

# IDs de relacion OSM fijos por zona (obtenidos una sola vez via Nominatim).
# No se buscan por nombre en cada consulta porque el filtro que desambigua
# por pais (area["name"="Colombia"]["admin_level"="2"]) satura el servidor
# publico de Overpass y siempre agota el tiempo de espera; y sin ese filtro,
# nombres como "Madrid" o "Cota" existen en muchos paises y la busqueda por
# nombre resulta ambigua, lenta o cae en rate-limit (429) al repetirse.
# area(id) con el id de relacion es instantaneo y sin ambiguedad.
ZONES = {
    "Bogotá": {"relation_id": 7426387, "department": "Bogotá D.C."},
    "Funza": {"relation_id": 1413037, "department": "Cundinamarca"},
    "Mosquera": {"relation_id": 1413051, "department": "Cundinamarca"},
    "Chía": {"relation_id": 10687625, "department": "Cundinamarca"},
    "Cajicá": {"relation_id": 11889894, "department": "Cundinamarca"},
    "Cota": {"relation_id": 7296967, "department": "Cundinamarca"},
    "Madrid": {"relation_id": 1413026, "department": "Cundinamarca"},
}

# Pausa entre consultas sucesivas cuando se buscan varias zonas en la misma
# solicitud, para no golpear el servidor publico con llamadas seguidas.
REQUEST_DELAY_SECONDS = 1.0

# El servidor publico de Overpass rechaza con 406 las solicitudes que traen
# el User-Agent por defecto de requests/urllib.
REQUEST_HEADERS = {"User-Agent": "ProspectorCD/0.1 (+https://github.com/Mundanesleet/Protector)"}

# No existe un tag unico de OSM por categoria de negocio: se aproxima cada
# categoria con las combinaciones key=value mas usadas en la practica.
# "otra" no tiene tags propios: si es la unica categoria seleccionada,
# build_overpass_query lo rechaza porque no hay criterio de busqueda.
CATEGORY_TAGS = {
    "bodega": [("building", "warehouse")],
    "almacenamiento": [
        ("building", "warehouse"),
        ("man_made", "storage_tank"),
        ("self_storage", "yes"),
    ],
    "logistica": [("office", "logistics")],
    "distribuidora": [("shop", "wholesale")],
    "mayorista": [("shop", "wholesale")],
    "alimentos": [
        ("shop", "food"),
        ("shop", "supermarket"),
        ("craft", "food"),
    ],
    "bebidas": [
        ("shop", "beverages"),
        ("shop", "alcohol"),
        ("craft", "brewery"),
    ],
    "industria": [("landuse", "industrial"), ("building", "industrial")],
    "importadora": [("office", "import_export")],
    "comercializadora": [("office", "company")],
    "transporte": [("office", "logistics"), ("building", "industrial")],
    "otra": [],
}


class OverpassServiceError(Exception):
    """Error base para fallos al consultar Overpass/OpenStreetMap."""


class OverpassUnavailableError(OverpassServiceError):
    """El servidor Overpass no respondio o devolvio un error."""


class OverpassTimeoutError(OverpassServiceError):
    """La consulta a Overpass tardo mas de lo permitido."""


class InvalidSearchError(OverpassServiceError):
    """Los parametros de busqueda (zonas/categorias) no son validos."""


def build_overpass_query(zones, categories, radius=None, timeout=None):
    """Construye una consulta Overpass QL a partir de zonas y categorias.

    `radius` queda reservado para una futura busqueda por cercania
    (around:radio,lat,lon); no se usa todavia.
    """
    if not zones:
        raise InvalidSearchError("Debes seleccionar al menos una zona")
    if not categories:
        raise InvalidSearchError("Debes seleccionar al menos una categoria")

    unknown_zones = [zone for zone in zones if zone not in ZONES]
    if unknown_zones:
        raise InvalidSearchError(f"Zona(s) no soportada(s): {', '.join(unknown_zones)}")

    unknown_categories = [cat for cat in categories if cat not in CATEGORY_CHOICES]
    if unknown_categories:
        raise InvalidSearchError(
            f"Categoria(s) no soportada(s): {', '.join(unknown_categories)}"
        )

    tags = _tags_for_categories(categories)
    if not tags:
        raise InvalidSearchError(
            "Las categorias seleccionadas no tienen un criterio de busqueda "
            "definido en OpenStreetMap"
        )

    timeout = timeout or Config.OVERPASS_TIMEOUT

    area_clauses = "\n".join(f"  area({_area_id(zone)});" for zone in zones)
    tag_clauses = "\n".join(
        f'  nwr(area.searchArea)["{key}"="{value}"];' for key, value in tags
    )

    return (
        f"[out:json][timeout:{timeout}];\n"
        "(\n"
        f"{area_clauses}\n"
        ")->.searchArea;\n"
        "(\n"
        f"{tag_clauses}\n"
        ");\n"
        "out center meta;"
    )


def fetch_raw_elements(query, api_url=None, timeout=None):
    """Ejecuta la consulta contra Overpass y devuelve la lista de elementos crudos."""
    api_url = api_url or Config.OVERPASS_API_URL
    timeout = timeout or Config.OVERPASS_TIMEOUT

    try:
        response = requests.post(
            api_url, data={"data": query}, headers=REQUEST_HEADERS, timeout=timeout
        )
    except requests.exceptions.Timeout as exc:
        raise OverpassTimeoutError("Overpass no respondio a tiempo") from exc
    except requests.exceptions.RequestException as exc:
        raise OverpassUnavailableError("No se pudo conectar con Overpass") from exc

    if response.status_code != 200:
        logger.warning(
            "Overpass respondio %s: %s", response.status_code, response.text[:300]
        )
        raise OverpassUnavailableError(
            f"Overpass respondio con estado {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise OverpassUnavailableError("Overpass devolvio una respuesta invalida") from exc

    return payload.get("elements", [])


def search(zones, categories, radius=None):
    """Busca empresas en Overpass y devuelve dicts normalizados (sin persistir).

    Consulta una zona a la vez (en vez de una sola query con todas las zonas
    unidas) para poder asignar con certeza la ciudad/departamento de cada
    resultado, y para no perder toda la busqueda si una sola zona falla.
    """
    if not zones:
        raise InvalidSearchError("Debes seleccionar al menos una zona")
    unknown_zones = [zone for zone in zones if zone not in ZONES]
    if unknown_zones:
        raise InvalidSearchError(f"Zona(s) no soportada(s): {', '.join(unknown_zones)}")

    companies = []
    successful_zones = 0

    for index, zone in enumerate(zones):
        if index > 0:
            time.sleep(REQUEST_DELAY_SECONDS)

        try:
            query = build_overpass_query([zone], categories, radius=radius)
            raw_elements = fetch_raw_elements(query)
        except OverpassServiceError as exc:
            logger.warning("Fallo la busqueda en la zona %s: %s", zone, exc)
            continue

        successful_zones += 1
        skipped = 0
        for element in raw_elements:
            company = _element_to_company_dict(element, zone)
            if company is None:
                skipped += 1
                continue
            companies.append(company)

        if skipped:
            logger.info("Zona %s: se omitieron %s elementos sin nombre", zone, skipped)

    if successful_zones == 0:
        raise OverpassUnavailableError(
            "No fue posible consultar la fuente de datos en ninguna de las zonas seleccionadas"
        )

    return companies


def _tags_for_categories(categories):
    seen = set()
    tags = []
    for category in categories:
        for tag in CATEGORY_TAGS.get(category, []):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


def _match_category(tags_dict):
    for category, tag_pairs in CATEGORY_TAGS.items():
        for key, value in tag_pairs:
            if tags_dict.get(key) == value:
                return category
    return "otra"


def _element_to_company_dict(element, zone):
    tags = element.get("tags", {}) or {}
    name = tags.get("name")
    if not name:
        return None

    if "center" in element:
        latitude = element["center"].get("lat")
        longitude = element["center"].get("lon")
    else:
        latitude = element.get("lat")
        longitude = element.get("lon")

    address_parts = [tags.get("addr:street"), tags.get("addr:housenumber")]
    address = " ".join(part for part in address_parts if part) or None

    return {
        "name": name,
        "address": address,
        # Si el dato no viene en OSM, se usa la zona consultada: el elemento
        # esta garantizado dentro de esa area administrativa.
        "city": tags.get("addr:city") or zone,
        "department": tags.get("addr:state") or ZONES[zone]["department"],
        "phone": tags.get("phone") or tags.get("contact:phone"),
        "email": tags.get("email") or tags.get("contact:email"),
        "website": tags.get("website") or tags.get("contact:website"),
        "category": _match_category(tags),
        "description": tags.get("description"),
        "latitude": latitude,
        "longitude": longitude,
        "source": "overpass",
        "source_id": f"{element.get('type')}/{element.get('id')}",
    }


def _area_id(zone):
    return 3_600_000_000 + ZONES[zone]["relation_id"]
