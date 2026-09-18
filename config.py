import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'prospector.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OVERPASS_API_URL = os.environ.get(
        "OVERPASS_API_URL", "https://overpass-api.de/api/interpreter"
    )
    OVERPASS_TIMEOUT = int(os.environ.get("OVERPASS_TIMEOUT", "30"))

    # Ambas quedan vacias si no estan configuradas: los servicios que las
    # usan detectan eso y avisan con un error claro en vez de fallar raro.
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    BRAVE_SEARCH_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY", "")
