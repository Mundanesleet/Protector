from datetime import datetime, timezone

from database import db


class Location(db.Model):
    """Una sucursal/ubicacion fisica de una Company.

    Existe para que una empresa con varias sedes legitimas (ej. una
    distribuidora con 3 bodegas) se represente como UNA empresa con varias
    ubicaciones, en vez de como 3 empresas independientes -- distinto del
    caso de cadenas grandes (Carulla, UNO), que se excluyen por completo en
    company_service (no son buenos prospectos, no se agregan como sucursales).
    """

    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    google_place_id = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="locations")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "phone": self.phone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "google_place_id": self.google_place_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Location {self.id} company_id={self.company_id} {self.name!r}>"
