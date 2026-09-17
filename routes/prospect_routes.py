from flask import Blueprint, jsonify, request

from services import company_service

prospect_bp = Blueprint("prospect_api", __name__, url_prefix="/api")


@prospect_bp.route("/prospects/<int:prospect_id>", methods=["PUT"])
def update_prospect(prospect_id):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if not status:
        return jsonify({"error": "El campo 'status' es obligatorio"}), 400

    try:
        prospect = company_service.update_prospect_status(prospect_id, status)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if prospect is None:
        return jsonify({"error": "Prospecto no encontrado"}), 404

    return jsonify({"data": prospect.to_dict()})


@prospect_bp.route("/prospects/<int:prospect_id>/notes", methods=["POST"])
def add_note(prospect_id):
    payload = request.get_json(silent=True) or {}
    content = (payload.get("content") or "").strip()
    if not content:
        return jsonify({"error": "El campo 'content' es obligatorio"}), 400

    note = company_service.add_prospect_note(prospect_id, content)
    if note is None:
        return jsonify({"error": "Prospecto no encontrado"}), 404

    return jsonify({"data": note.to_dict()}), 201
