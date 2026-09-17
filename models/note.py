from datetime import datetime, timezone

from database import db


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    prospect_id = db.Column(db.Integer, db.ForeignKey("prospects.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    prospect = db.relationship("Prospect", back_populates="notes")

    def to_dict(self):
        return {
            "id": self.id,
            "prospect_id": self.prospect_id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Note {self.id} prospect_id={self.prospect_id}>"
