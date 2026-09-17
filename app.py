from flask import Flask

from config import Config
from database import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from routes.main_routes import main_bp
    app.register_blueprint(main_bp)

    from models import Company, Note, Prospect  # noqa: F401 registra los modelos en SQLAlchemy

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
