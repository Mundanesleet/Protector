"""Logica de negocio sobre Company/Prospect/Note: deduplicacion, filtros,
exportacion a Excel y estadisticas.

No depende de Flask: recibe/devuelve modelos y dicts planos, para que las
rutas (routes/) se queden como controladores delgados.
"""

import io
import re
import unicodedata
from collections import Counter

from openpyxl import Workbook

from database import db
from models import Company, Note, Prospect
from models.company import CATEGORY_CHOICES, CATEGORY_LABELS
from models.prospect import STATUS_LABELS
from services import contact_finder_service

# Estados que cuentan como "contactados" en el dashboard: hay alguna
# interaccion registrada pero todavia no es cliente ni se descarto.
CONTACTED_STATUSES = ("contacted", "responded", "interested", "quote_sent")

# 3+ ubicaciones con el mismo nombre normalizado = cadena/franquicia (ej.
# Carulla, UNO): se excluyen por completo, no solo se deduplican, porque una
# cadena grande ya tiene su propia logistica y no es un buen prospecto.
CHAIN_MIN_LOCATIONS = 3

_CHAIN_SUFFIX_WORDS = (
    "sucursal",
    "sede",
    "local",
    "tienda",
    "punto de venta",
    "pdv",
    "no",
    "nro",
    "numero",
)

# Campos que el usuario puede corregir/enriquecer manualmente (accion "Editar").
# No incluye source/source_id/coordenadas: esos vienen de la fuente de datos.
EDITABLE_COMPANY_FIELDS = (
    "name",
    "address",
    "city",
    "department",
    "phone",
    "email",
    "website",
    "category",
    "description",
)


def save_companies(company_dicts):
    """Inserta o actualiza Companies evitando duplicados. Excluye cadenas o
    franquicias con muchas ubicaciones (ej. Carulla, UNO). Devuelve un resumen.
    """
    created = 0
    updated = 0
    skipped_chains = 0

    for data in company_dicts:
        data["chain_key"] = _normalize_chain_name(data["name"])
        if data.get("phone"):
            data["phone"] = normalize_phone(data["phone"])

    batch_counts = Counter(data["chain_key"] for data in company_dicts)
    existing_counts = dict(
        db.session.query(Company.chain_key, db.func.count(Company.id))
        .filter(Company.chain_key.in_(batch_counts.keys()))
        .group_by(Company.chain_key)
        .all()
    )

    chains_to_exclude = {
        chain_key
        for chain_key, count in batch_counts.items()
        if count + existing_counts.get(chain_key, 0) >= CHAIN_MIN_LOCATIONS
    }

    if chains_to_exclude:
        # Tambien se quitan las que ya se habian guardado de busquedas
        # anteriores, salvo que el usuario ya las haya guardado como
        # prospecto (eso se preserva, es trabajo del usuario).
        Company.query.filter(
            Company.chain_key.in_(chains_to_exclude), ~Company.prospect.has()
        ).delete(synchronize_session=False)

    for data in company_dicts:
        if data["chain_key"] in chains_to_exclude:
            skipped_chains += 1
            continue

        existing = _find_existing(data)
        if existing:
            _apply_updates(existing, data)
            updated += 1
        else:
            db.session.add(Company(**data))
            created += 1

    db.session.commit()
    return {
        "found": len(company_dicts),
        "created": created,
        "updated": updated,
        "skipped_chains": skipped_chains,
    }


def backfill_chain_keys():
    """Calcula chain_key para filas guardadas antes de que existiera esta
    columna. Se llama al arrancar la app; es barato y no hace nada si ya
    todas las filas la tienen."""
    pending = Company.query.filter(Company.chain_key.is_(None)).all()
    for company in pending:
        company.chain_key = _normalize_chain_name(company.name)
    if pending:
        db.session.commit()
    return len(pending)


def cleanup_chains():
    """Limpieza puntual (boton en el dashboard) de cadenas que ya estaban
    guardadas de busquedas anteriores a este cambio."""
    backfill_chain_keys()

    chain_keys = [
        chain_key
        for chain_key, count in (
            db.session.query(Company.chain_key, db.func.count(Company.id))
            .group_by(Company.chain_key)
            .all()
        )
        if chain_key and count >= CHAIN_MIN_LOCATIONS
    ]

    removed = 0
    for chain_key in chain_keys:
        removed += Company.query.filter(
            Company.chain_key == chain_key, ~Company.prospect.has()
        ).delete(synchronize_session=False)

    db.session.commit()
    return removed


def normalize_phone(phone):
    """Normaliza numeros colombianos a un formato consistente ('+57 XXXXXXXXXX')
    para que '+57 601 1234567', '6011234567' y '(601) 1234567' se guarden
    de forma comparable en vez de como strings distintos."""
    if not phone:
        return None

    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None

    if digits.startswith("57") and len(digits) == 12:
        digits = digits[2:]

    return f"+57 {digits}" if len(digits) == 10 else phone.strip()


def _normalize_chain_name(name):
    text = unicodedata.normalize("NFKD", name.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    for word in _CHAIN_SUFFIX_WORDS:
        text = re.sub(rf"\b{word}\b", " ", text)
    text = re.sub(r"\d+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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


def update_company(company_id, fields):
    """Edicion manual de una Company (accion 'Editar')."""
    company = Company.query.get(company_id)
    if company is None:
        return None

    if "category" in fields and fields["category"] not in CATEGORY_CHOICES:
        raise ValueError(f"Categoria no valida: {fields['category']}")

    for field in EDITABLE_COMPANY_FIELDS:
        if field in fields:
            value = fields[field]
            if field == "phone" and value:
                value = normalize_phone(value)
            setattr(company, field, value)

    db.session.commit()
    return company


def find_company_contact(company_id):
    """Busca email/WhatsApp en el sitio web de la empresa y completa los
    campos que estuvieran vacios (no sobreescribe datos ya confirmados)."""
    company = Company.query.get(company_id)
    if company is None:
        return None, None

    if not company.website:
        raise ValueError("Esta empresa no tiene sitio web registrado")

    result = contact_finder_service.find_contact(company.website)

    if result.get("email") and not company.email:
        company.email = result["email"]
    if result.get("whatsapp_phone") and not company.phone:
        company.phone = normalize_phone(result["whatsapp_phone"])
    db.session.commit()

    return company, result


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
    total_prospects = Prospect.query.count()
    pendientes = Prospect.query.filter_by(status="new").count()
    contactados = Prospect.query.filter(Prospect.status.in_(CONTACTED_STATUSES)).count()
    clientes = Prospect.query.filter_by(status="customer").count()

    con_email = Company.query.filter(Company.email.isnot(None), Company.email != "").count()
    con_website = Company.query.filter(Company.website.isnot(None), Company.website != "").count()
    con_telefono = Company.query.filter(Company.phone.isnot(None), Company.phone != "").count()
    enriquecidas = Company.query.filter(Company.enriched_at.isnot(None)).count()

    return {
        "total_companies": total_companies,
        "total_prospects": total_prospects,
        "pendientes": pendientes,
        "contactados": contactados,
        "clientes": clientes,
        "con_email": con_email,
        "con_website": con_website,
        "con_telefono": con_telefono,
        "enriquecidas": enriquecidas,
    }


def export_companies_workbook(filters=None):
    """Genera un .xlsx en memoria con las empresas (respeta los mismos filtros
    que list_companies), para que el usuario tenga siempre un respaldo
    portable de los datos fuera de la base de datos."""
    companies = list_companies(filters)

    wb = Workbook()
    ws = wb.active
    ws.title = "Prospectos"

    headers = [
        "Nombre",
        "Ciudad",
        "Departamento",
        "Categoría",
        "Dirección",
        "Teléfono",
        "Email",
        "Website",
        "Estado comercial",
        "Fuente",
        "Descubierta",
    ]
    ws.append(headers)

    for company in companies:
        status_label = "Sin guardar"
        if company.prospect:
            status_label = STATUS_LABELS.get(company.prospect.status, company.prospect.status)

        ws.append(
            [
                company.name,
                company.city or "",
                company.department or "",
                CATEGORY_LABELS.get(company.category, company.category or ""),
                company.address or "",
                company.phone or "",
                company.email or "",
                company.website or "",
                status_label,
                company.source,
                company.discovered_at.strftime("%Y-%m-%d %H:%M") if company.discovered_at else "",
            ]
        )

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 45)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
