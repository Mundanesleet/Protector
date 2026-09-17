"""Logica de negocio sobre Company/Prospect/Note: deduplicacion, filtros y stats.

No depende de Flask: recibe/devuelve modelos y dicts planos, para que las
rutas (routes/) se queden como controladores delgados.
"""

from database import db
from models import Company, Note, Prospect
from models.prospect import STATUS_LABELS

# Estados que cuentan como "contactados" en el dashboard: hay alguna
# interaccion registrada pero todavia no es cliente ni se descarto.
CONTACTED_STATUSES = ("contacted", "responded", "interested", "quote_sent")


def save_companies(company_dicts):
    """Inserta o actualiza Companies evitando duplicados. Devuelve un resumen."""
    created = 0
    updated = 0

    for data in company_dicts:
        existing = _find_existing(data)
        if existing:
            _apply_updates(existing, data)
            updated += 1
        else:
            db.session.add(Company(**data))
            created += 1

    db.session.commit()
    return {"found": len(company_dicts), "created": created, "updated": updated}


def _find_existing(data):
    source = data.get("source")
    source_id = data.get("source_id")
    if source and source_id:
        existing = Company.query.filter_by(source=source, source_id=source_id).first()
        if existing:
            return existing

    # Sin source_id utilizable: se identifica por nombre + direccion + coordenadas.
    if data.get("name") and data.get("latitude") is not None and data.get("longitude") is not None:
        return Company.query.filter_by(
            name=data["name"],
            address=data.get("address"),
            latitude=data["latitude"],
            longitude=data["longitude"],
        ).first()

    return None


def _apply_updates(company, data):
    for field in (
        "name",
        "address",
        "city",
        "department",
        "phone",
        "email",
        "website",
        "category",
        "description",
        "latitude",
        "longitude",
    ):
        value = data.get(field)
        if value:
            setattr(company, field, value)


def list_companies(filters=None):
    filters = filters or {}
    query = Company.query

    if filters.get("city"):
        query = query.filter(Company.city == filters["city"])
    if filters.get("category"):
        query = query.filter(Company.category == filters["category"])
    if filters.get("opportunity_level"):
        query = query.filter(Company.opportunity_level == filters["opportunity_level"])
    if filters.get("status"):
        query = query.join(Prospect).filter(Prospect.status == filters["status"])
    if filters.get("has_phone") is True:
        query = query.filter(Company.phone.isnot(None), Company.phone != "")
    elif filters.get("has_phone") is False:
        query = query.filter((Company.phone.is_(None)) | (Company.phone == ""))
    if filters.get("has_website") is True:
        query = query.filter(Company.website.isnot(None), Company.website != "")
    elif filters.get("has_website") is False:
        query = query.filter((Company.website.is_(None)) | (Company.website == ""))
    if filters.get("q"):
        query = query.filter(Company.name.ilike(f"%{filters['q']}%"))

    return query.order_by(Company.discovered_at.desc()).all()


def save_as_prospect(company_id):
    """Accion 'Guardar': crea el Prospect de una Company (idempotente)."""
    company = Company.query.get(company_id)
    if company is None:
        return None

    if company.prospect is not None:
        return company.prospect

    prospect = Prospect(company_id=company.id, status="new")
    db.session.add(prospect)
    db.session.commit()
    return prospect


def update_prospect_status(prospect_id, status):
    if status not in STATUS_LABELS:
        raise ValueError(f"Estado no valido: {status}")

    prospect = Prospect.query.get(prospect_id)
    if prospect is None:
        return None

    prospect.status = status
    db.session.commit()
    return prospect


def add_prospect_note(prospect_id, content):
    prospect = Prospect.query.get(prospect_id)
    if prospect is None:
        return None

    note = Note(prospect_id=prospect.id, content=content)
    db.session.add(note)
    db.session.commit()
    return note


def get_stats():
    total_companies = Company.query.count()
    alta = Company.query.filter_by(opportunity_level="alta").count()
    media = Company.query.filter_by(opportunity_level="media").count()
    baja = Company.query.filter_by(opportunity_level="baja").count()

    total_prospects = Prospect.query.count()
    pendientes = Prospect.query.filter_by(status="new").count()
    contactados = Prospect.query.filter(Prospect.status.in_(CONTACTED_STATUSES)).count()
    clientes = Prospect.query.filter_by(status="customer").count()

    return {
        "total_companies": total_companies,
        "alta_oportunidad": alta,
        "media_oportunidad": media,
        "baja_oportunidad": baja,
        "total_prospects": total_prospects,
        "pendientes": pendientes,
        "contactados": contactados,
        "clientes": clientes,
    }
