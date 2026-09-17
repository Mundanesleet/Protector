from flask import Blueprint, jsonify

from models import CATEGORY_CHOICES, CATEGORY_LABELS, STATUS_LABELS
from services.company_service import get_stats
from services.data_sources.overpass_service import ZONES

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/stats")
def stats():
    return jsonify({"data": get_stats()})


@api_bp.route("/meta")
def meta():
    return jsonify(
        {
            "data": {
                "zones": list(ZONES.keys()),
                "categories": [
                    {"value": value, "label": CATEGORY_LABELS.get(value, value)}
                    for value in CATEGORY_CHOICES
                ],
                "statuses": [
                    {"value": value, "label": label}
                    for value, label in STATUS_LABELS.items()
                ],
            }
        }
    )
