from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from config import Config
from database import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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
    app.run(debug=True)
