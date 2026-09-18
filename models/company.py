from datetime import datetime, timezone

from database import db

CATEGORY_CHOICES = [
    "bodega",
    "logistica",
    "distribuidora",
    "alimentos",
    "bebidas",
    "mayorista",
    "industria",
    "importadora",
    "comercializadora",
    "transporte",
    "almacenamiento",
    "otra",
]

CATEGORY_LABELS = {
    "bodega": "Bodega",
    "logistica": "Logística",
    "distribuidora": "Distribuidora",
    "alimentos": "Alimentos",
    "bebidas": "Bebidas",
    "mayorista": "Mayorista",
    "industria": "Industria",
    "importadora": "Importadora",
    "comercializadora": "Comercializadora",
    "transporte": "Transporte",
    "almacenamiento": "Almacenamiento",
    "otra": "Otra",
}


class Company(db.Model):
    """Datos de la empresa tal como se encontraron en la fuente (OSM, etc.)."""

    __tablename__ = "companies"
    __table_args__ = (
        db.UniqueConstraint("source", "source_id", name="uq_company_source"),
    )

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    department = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    website = db.Column(db.String(255))
    category = db.Column(db.String(50))
    description = db.Column(db.Text)

    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    source = db.Column(db.String(50), nullable=False)
    source_id = db.Column(db.String(100))

    # Nombre normalizado (sin acentos/numeros/sufijos de sucursal) usado para
    # detectar cadenas/franquicias con muchas ubicaciones (ej. Carulla, UNO)
    # y excluirlas: no son buenos prospectos, ya tienen su propia logistica.
    chain_key = db.Column(db.String(255), index=True)

    # Enriquecimiento con IA (busqueda web), opcional y bajo demanda por
    # empresa desde la ficha -- ver services/enrichment_service.py.
    facebook_url = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(255))
    enrichment_notes = db.Column(db.Text)
    enriched_at = db.Column(db.DateTime)

    discovered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    prospect = db.relationship(
        "Prospect",
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "department": self.department,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "category": self.category,
            "description": self.description,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "source": self.source,
            "source_id": self.source_id,
            "facebook_url": self.facebook_url,
            "linkedin_url": self.linkedin_url,
            "enrichment_notes": self.enrichment_notes,
            "enriched_at": self.enriched_at.isoformat() if self.enriched_at else None,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "prospect": self.prospect.to_dict() if self.prospect else None,
        }

    def __repr__(self):
        return f"<Company {self.id} {self.name!r}>"
