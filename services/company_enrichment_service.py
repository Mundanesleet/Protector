"""Orquesta el enriquecimiento de una Company: busca en Brave Search lo
que falte (sitio oficial, Facebook, LinkedIn) y, si hay un sitio web,
intenta extraer email/telefono de ahi con contact_finder_service. Nunca
sobreescribe un dato ya confirmado -- solo completa lo que esta vacio.
Registra en Source de donde vino cada dato nuevo.

Un fallo en un paso (ej. Brave no encuentra Facebook) no detiene los
demas pasos -- se guarda lo que si se pudo conseguir.
"""

import logging
from datetime import datetime, timezone

from database import db
from models import Source
from services import contact_finder_service
from services.contact_finder_service import ContactFinderError
from services.data_sources import brave_search_service
from services.data_sources.brave_search_service import (
    BraveSearchNotConfiguredError,
    BraveSearchServiceError,
)

logger = logging.getLogger(__name__)


def enrich_company(company):
    """Completa los campos que falten en `company`. Devuelve la lista de
    nombres de campos que se completaron (puede estar vacia)."""
    if not brave_search_service.is_configured():
        raise BraveSearchNotConfiguredError(
            "Brave Search no esta configurado (falta BRAVE_SEARCH_API_KEY en .env)"
        )

    updated_fields = []

    if not company.website:
        try:
            result = brave_search_service.find_official_website(company.name, company.city)
        except BraveSearchServiceError:
            logger.warning("Fallo buscando sitio oficial de %s", company.name, exc_info=True)
            result = None
        if result:
            company.website = result["url"]
            _record_source(company, "website", "brave_search", result["url"])
            updated_fields.append("website")

    if not company.facebook_url:
        _try_social_link(company, "facebook.com", "facebook_url", updated_fields)

    if not company.linkedin_url:
        _try_social_link(company, "linkedin.com", "linkedin_url", updated_fields)

    if company.website and (not company.email or not company.phone):
        try:
            contact = contact_finder_service.find_contact(company.website)
        except ContactFinderError:
            logger.warning("Fallo consultando %s", company.website, exc_info=True)
            contact = {"email": None, "whatsapp_phone": None}

        if contact.get("email") and not company.email:
            company.email = contact["email"]
            _record_source(company, "email", "company_website", company.website)
            updated_fields.append("email")
        if contact.get("whatsapp_phone") and not company.phone:
            company.phone = contact["whatsapp_phone"]
            _record_source(company, "phone", "company_website", company.website)
            updated_fields.append("phone")

    company.enriched_at = datetime.now(timezone.utc)
    db.session.commit()

    return updated_fields


def _try_social_link(company, domain, field_name, updated_fields):
    try:
        result = brave_search_service.find_social_link(company.name, company.city, domain)
    except BraveSearchServiceError:
        logger.warning("Fallo buscando %s de %s", domain, company.name, exc_info=True)
        return

    if result:
        setattr(company, field_name, result["url"])
        _record_source(company, field_name, "brave_search", result["url"])
        updated_fields.append(field_name)


def _record_source(company, field_name, source_type, url):
    db.session.add(
        Source(company_id=company.id, field_name=field_name, source_type=source_type, url=url)
    )
