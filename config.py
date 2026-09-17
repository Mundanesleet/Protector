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
