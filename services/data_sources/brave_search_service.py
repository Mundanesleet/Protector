"""Fuente de investigacion: Brave Search API.

Se usa para completar datos que Google Places/Overpass no traen: sitio
web oficial cuando no aparece de otra forma, y perfiles publicos de
Facebook/LinkedIn. Requiere BRAVE_SEARCH_API_KEY; si no esta configurada,
is_configured() devuelve False y quien la use debe avisarlo (no se rompe
el resto de la app).

No se hace scraping de Facebook/LinkedIn: solo se guarda la URL publica
que aparece en los resultados de busqueda, nunca se intenta acceder al
contenido de esas paginas (punto 20 del alcance).
"""

import logging
from urllib.parse import urlparse

import requests

from config import Config

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
REQUEST_TIMEOUT = 10

# Dominios que nunca se guardan como "sitio web oficial" aunque aparezcan
# primero en la busqueda -- son directorios/redes sociales, no la pagina
# propia de la empresa.
NON_OFFICIAL_DOMAINS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "tiktok.com",
    "wikipedia.org",
    "paginasamarillas.com.co",
    "google.com",
    "maps.google.com",
    "yelp.com",
    "tripadvisor.com",
    # Directorios empresariales colombianos/regionales -- encontrado en
    # pruebas reales: Brave devolvia estos como si fueran "el sitio
    # oficial" de la empresa.
    "informacolombia.com",
    "guialocal.com.co",
    "sitios.com.co",
    "econtactos.com",
    "datosempresa.com",
    "einforma.co",
    "kompass.com",
    "cybo.com",
    "opencorporates.com",
    "guiaempresarial.com.co",
    "rues.org.co",
    "empresite.eleconomistaamerica.co",
)

# Ademas del dominio, un directorio suele delatarse por el patron de su
# propia URL de listado (ej. "/directorio-empresas/...", "/empresa/...").
DIRECTORY_PATH_HINTS = (
    "directorio-empresas",
    "directorio_empresas",
    "/directorio/",
    "informacion-empresa",
    "/empresa/",
    "/empresas/",
    "/company/",
    "/companies/",
    "guia-empresas",
    "/listing/",
    "/perfil-empresa",
    "ficha-empresa",
)


def _looks_like_directory(url):
    """Detecta paginas de directorio por dominio conocido o por pista en la
    ruta. Se prueban dominios de directorios reales encontrados en pruebas
    (informacolombia.com, colombiabz.com, mudanza.com.co...) y siguen
    apareciendo otros nuevos -- una lista de dominios nunca alcanza. Por
    eso ademas de esto, find_official_website() solo acepta la RAIZ del
    dominio (sin ruta), que es una señal mucho mas confiable: un sitio
    oficial casi siempre es 'empresa.com', un directorio casi siempre es
    'directorio.com/algo/nombre-empresa-123'. Mejor no adivinar (rechazar
    algo real de vez en cuando) que guardar un directorio como si fuera
    el sitio oficial."""
    lowered = url.lower()
    if any(domain in lowered for domain in NON_OFFICIAL_DOMAINS):
        return True
    return any(hint in lowered for hint in DIRECTORY_PATH_HINTS)


def _is_root_url(url):
    return urlparse(url.lower()).path.strip("/") == ""


class BraveSearchServiceError(Exception):
    """Error al consultar Brave Search."""


class BraveSearchNotConfiguredError(BraveSearchServiceError):
    """No hay BRAVE_SEARCH_API_KEY configurada."""


def is_configured():
    return bool(Config.BRAVE_SEARCH_API_KEY)


def find_official_website(name, city):
    """Busca el sitio oficial de una empresa. Solo acepta resultados que
    sean la raiz del dominio y no coincidan con un directorio conocido --
    si el primer resultado relevante no cumple eso, no devuelve nada en
    vez de adivinar cual es el sitio real."""
    results = _search(f"{name} {city or ''} Colombia sitio oficial".strip())
    for result in results:
        url = result.get("url", "")
        if url and _is_root_url(url) and not _looks_like_directory(url):
            return {"url": url, "title": result.get("title")}
    return None


def find_social_link(name, city, domain):
    """Busca un perfil publico (ej. facebook.com) para la empresa. Solo
    devuelve la URL publica -- nunca intenta acceder a su contenido."""
    results = _search(f"{name} {city or ''} Colombia {domain}".strip())
    for result in results:
        url = result.get("url", "")
        if domain in url:
            return {"url": url, "title": result.get("title")}
    return None


def _search(query, count=5):
    if not is_configured():
        raise BraveSearchNotConfiguredError(
            "Brave Search no esta configurado (falta BRAVE_SEARCH_API_KEY en .env)"
        )

    headers = {"Accept": "application/json", "X-Subscription-Token": Config.BRAVE_SEARCH_API_KEY}
    # Colombia ("CO") no esta en la lista de paises soportada por este
    # parametro (verificado contra la API real) -- se usa "ALL" (sin
    # restriccion) y se confia en que "Colombia" en la consulta ya guia
    # bien los resultados.
    params = {"q": query, "count": count, "country": "ALL", "search_lang": "es"}

    try:
        response = requests.get(
            SEARCH_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.RequestException as exc:
        raise BraveSearchServiceError(f"No se pudo conectar con Brave Search: {exc}") from exc

    if response.status_code == 429:
        raise BraveSearchServiceError("Limite de cuota de Brave Search alcanzado")
    if response.status_code == 401:
        raise BraveSearchServiceError("API key de Brave Search invalida")
    if response.status_code != 200:
        raise BraveSearchServiceError(
            f"Brave Search respondio con estado {response.status_code}: {response.text[:300]}"
        )

    return response.json().get("web", {}).get("results", [])
