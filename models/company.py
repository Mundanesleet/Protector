import json
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

OPPORTUNITY_LABELS = {
    "alta": "Alta oportunidad",
    "media": "Oportunidad media",
    "baja": "Baja oportunidad",
}


class Company(db.Model):
    """Datos de la empresa tal como se encontraron en la fuente (OSM, etc.).

    El puntaje de oportunidad vive aqui (no en Prospect) porque se calcula a
    partir de senales de la empresa (categoria, descripcion) y debe verse en
    toda empresa encontrada, la haya guardado el usuario como prospecto o no.
    """

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

    # Clasificacion de oportunidad (reglas en prospect_scoring_service.py, fase 11).
    # Por defecto queda en 0/baja hasta que ese servicio exista.
    score = db.Column(db.Integer, nullable=False, default=0)
    opportunity_level = db.Column(db.String(10), nullable=False, default="baja")
    score_reasons = db.Column(db.Text)  # JSON: lista de razones de la clasificacion

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
            "score": self.score,
            "opportunity_level": self.opportunity_level,
            "opportunity_label": OPPORTUNITY_LABELS.get(
                self.opportunity_level, self.opportunity_level
            ),
            "score_reasons": json.loads(self.score_reasons) if self.score_reasons else [],
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "prospect": self.prospect.to_dict() if self.prospect else None,
        }

    def __repr__(self):
        return f"<Company {self.id} {self.name!r}>"
