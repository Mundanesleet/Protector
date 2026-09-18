import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from config import Config
from database import db, ensure_schema_migrations


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # instance/ no se sube a git (ahi vive la base de datos SQLite); en un
    # clon nuevo (ej. un servidor de despliegue) esta carpeta no existe y
    # SQLite no puede crear el archivo dentro de una carpeta inexistente.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from routes.api_routes import api_bp
    from routes.company_routes import company_bp
    from routes.main_routes import main_bp
    from routes.prospect_routes import prospect_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(prospect_bp)
    app.register_blueprint(api_bp)

    from models import Company, Note, Prospect  # noqa: F401 registra los modelos en SQLAlchemy

    with app.app_context():
        db.create_all()
        ensure_schema_migrations()

        from services.company_service import backfill_chain_keys

        backfill_chain_keys()

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        return jsonify({"error": exc.description}), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        app.logger.exception("Error inesperado")
        return jsonify({"error": "Ocurrio un error inesperado. Intenta nuevamente."}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    # host 0.0.0.0: accesible desde otros dispositivos en la misma red local
    # (ej. probar desde el celular), no solo desde esta misma maquina.
    app.run(debug=True, host="0.0.0.0")
