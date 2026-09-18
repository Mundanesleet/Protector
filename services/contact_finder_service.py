"""Busca datos de contacto (email, WhatsApp) en la propia pagina web de una
empresa. Es una consulta puntual bajo demanda del usuario para una sola
empresa a la vez -- no un rastreo masivo ni recurrente.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests

REQUEST_HEADERS = {
    "User-Agent": "ProspectorCD/0.1 (+https://github.com/Mundanesleet/Protector)"
}
REQUEST_TIMEOUT = 10
MAX_HTML_CHARS = 300_000

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
WHATSAPP_PATTERN = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\d{7,15})")

# Emails de plantillas/trackers/genericos que no sirven como contacto real.
EMAIL_IGNORE_SUBSTRINGS = (
    "example.com",
    "wixpress.com",
    "sentry.io",
    "godaddy.com",
    "yourdomain",
    "@2x",
    "@3x",
    "no-reply",
    "noreply",
    "wordpress.com",
)
EMAIL_IGNORE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


class ContactFinderError(Exception):
    """No se pudo consultar el sitio web de la empresa."""


def find_contact(url):
    """Devuelve {'email': str|None, 'whatsapp_phone': str|None}."""
    if not url:
        return {"email": None, "whatsapp_phone": None}

    normalized = url if url.startswith(("http://", "https://")) else f"https://{url}"

    if not _is_safe_url(normalized):
        raise ContactFinderError(f"URL no permitida: {url}")

    try:
        response = requests.get(normalized, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        raise ContactFinderError(f"No se pudo consultar {url}") from exc

    if response.status_code != 200:
        raise ContactFinderError(f"{url} respondio con estado {response.status_code}")

    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type and "text" not in content_type:
        return {"email": None, "whatsapp_phone": None}

    html = response.text[:MAX_HTML_CHARS]

    return {
        "email": _first_valid_email(html),
        "whatsapp_phone": _first_whatsapp_phone(html),
    }


def _is_safe_url(url):
    """Evita SSRF: solo http/https y solo IPs publicas (no localhost, red
    interna, link-local, etc.) para el host resuelto."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname:
        return False

    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return False

    for *_ignored, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False

    return True


def _first_valid_email(html):
    for match in EMAIL_PATTERN.finditer(html):
        candidate = match.group(0).lower()
        if any(bad in candidate for bad in EMAIL_IGNORE_SUBSTRINGS):
            continue
        if candidate.endswith(EMAIL_IGNORE_EXTENSIONS):
            continue
        return candidate
    return None


def _first_whatsapp_phone(html):
    match = WHATSAPP_PATTERN.search(html)
    return match.group(1) if match else None
