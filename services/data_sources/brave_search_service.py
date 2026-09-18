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
)


class BraveSearchServiceError(Exception):
    """Error al consultar Brave Search."""


class BraveSearchNotConfiguredError(BraveSearchServiceError):
    """No hay BRAVE_SEARCH_API_KEY configurada."""


def is_configured():
    return bool(Config.BRAVE_SEARCH_API_KEY)


def find_official_website(name, city):
    """Busca el sitio oficial de una empresa. Si el primer resultado
    relevante es un directorio/red social, no devuelve nada en vez de
    adivinar cual es el sitio real."""
    results = _search(f"{name} {city or ''} Colombia sitio oficial".strip())
    for result in results:
        url = result.get("url", "")
        if url and not any(domain in url for domain in NON_OFFICIAL_DOMAINS):
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
    params = {"q": query, "count": count, "country": "co", "search_lang": "es"}

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
