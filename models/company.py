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


class Company(db.Model):
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

    def __repr__(self):
        return f"<Company {self.id} {self.name!r}>"
