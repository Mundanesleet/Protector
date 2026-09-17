from flask import Blueprint, jsonify

from services.company_service import get_stats

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/stats")
def stats():
    return jsonify({"data": get_stats()})
