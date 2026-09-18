from datetime import datetime, timezone

from database import db

# De donde puede venir un dato (campo field_name en una Company).
SOURCE_TYPES = (
    "overpass",
    "google_places",
    "brave_search",
    "company_website",
    "manual",
)


class Source(db.Model):
    """Procedencia de un dato puntual de una Company (que campo, de donde,
    y cuando se obtuvo) -- para poder mostrar 'Telefono: fuente Google
    Places' en la ficha, en vez de solo el dato sin origen."""

    __tablename__ = "sources"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    field_name = db.Column(db.String(50), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(500))
    retrieved_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="sources")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "field_name": self.field_name,
            "source_type": self.source_type,
            "url": self.url,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
        }

    def __repr__(self):
        return f"<Source {self.id} company_id={self.company_id} {self.field_name}={self.source_type!r}>"
