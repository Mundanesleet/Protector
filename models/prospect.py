from datetime import datetime, timezone

from database import db

STATUS_LABELS = {
    "new": "Sin contactar",
    "contacted": "Contactado",
    "responded": "Respondió",
    "interested": "Interesado",
    "quote_sent": "Cotización enviada",
    "customer": "Cliente",
    "not_interested": "No interesado",
}

OPPORTUNITY_LABELS = {
    "alta": "Alta oportunidad",
    "media": "Oportunidad media",
    "baja": "Baja oportunidad",
}


class Prospect(db.Model):
    __tablename__ = "prospects"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, unique=True
    )

    status = db.Column(db.String(20), nullable=False, default="new")

    score = db.Column(db.Integer, nullable=False, default=0)
    opportunity_level = db.Column(db.String(10), nullable=False, default="baja")
    score_reasons = db.Column(db.Text)  # JSON: lista de razones de la clasificación

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    company = db.relationship("Company", back_populates="prospect")
    notes = db.relationship(
        "Note",
        back_populates="prospect",
        cascade="all, delete-orphan",
        order_by="Note.created_at.desc()",
    )

    def __repr__(self):
        return f"<Prospect {self.id} company_id={self.company_id} status={self.status!r}>"
