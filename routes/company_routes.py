import logging

from flask import Blueprint, jsonify, request

from models import Company
from services import company_service
from services.data_sources.overpass_service import InvalidSearchError, OverpassServiceError
from services.data_sources.overpass_service import search as overpass_search

logger = logging.getLogger(__name__)

company_bp = Blueprint("company_api", __name__, url_prefix="/api")


@company_bp.route("/search", methods=["POST"])
def search_companies():
    payload = request.get_json(silent=True) or {}
    zones = payload.get("zones") or []
    categories = payload.get("categories") or []

    try:
        results = overpass_search(zones, categories)
    except InvalidSearchError as exc:
        return jsonify({"error": str(exc)}), 400
    except OverpassServiceError:
        logger.exception("Fallo la busqueda en Overpass")
        return (
            jsonify(
                {
                    "error": "No fue posible consultar la fuente de datos en este "
                    "momento. Intenta nuevamente."
                }
            ),
            503,
        )

    summary = company_service.save_companies(results)
    return jsonify({"data": summary})


@company_bp.route("/companies")
def list_companies():
    filters = {
        "city": request.args.get("city"),
        "category": request.args.get("category"),
        "opportunity_level": request.args.get("opportunity_level"),
        "status": request.args.get("status"),
        "q": request.args.get("q"),
    }
    if "has_phone" in request.args:
        filters["has_phone"] = request.args.get("has_phone") == "true"
    if "has_website" in request.args:
        filters["has_website"] = request.args.get("has_website") == "true"

    companies = company_service.list_companies(filters)
    return jsonify({"data": [company.to_dict() for company in companies]})


@company_bp.route("/companies/<int:company_id>")
def get_company(company_id):
    company = Company.query.get(company_id)
    if company is None:
        return jsonify({"error": "Empresa no encontrada"}), 404

    data = company.to_dict()
    if company.prospect:
        data["prospect"] = company.prospect.to_dict(include_notes=True)
    return jsonify({"data": data})


@company_bp.route("/companies/<int:company_id>/save", methods=["POST"])
def save_company_as_prospect(company_id):
    prospect = company_service.save_as_prospect(company_id)
    if prospect is None:
        return jsonify({"error": "Empresa no encontrada"}), 404
    return jsonify({"data": prospect.to_dict()})


@company_bp.route("/companies/<int:company_id>", methods=["PUT"])
def edit_company(company_id):
    payload = request.get_json(silent=True) or {}

    try:
        company = company_service.update_company(company_id, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if company is None:
        return jsonify({"error": "Empresa no encontrada"}), 404

    return jsonify({"data": company.to_dict()})
