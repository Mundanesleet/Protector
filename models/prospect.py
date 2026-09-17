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


class Prospect(db.Model):
    """Gestion comercial de una Company que el usuario decidio guardar (accion 'Guardar')."""

    __tablename__ = "prospects"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, unique=True
    )

    status = db.Column(db.String(20), nullable=False, default="new")

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

    def to_dict(self, include_notes=False):
        data = {
            "id": self.id,
            "company_id": self.company_id,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_notes:
            data["notes"] = [note.to_dict() for note in self.notes]
        return data

    def __repr__(self):
        return f"<Prospect {self.id} company_id={self.company_id} status={self.status!r}>"
