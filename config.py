"""
Конфигурация приложения TwoSigma
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Пути
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# База данных приложения (SQLite для хранения метаданных тестов)
APP_DATABASE_PATH = DATA_DIR / "twosigma.db"

# Настройки подключения к внешним БД (из env)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_TYPE = os.getenv("DB_TYPE", "postgresql")  # postgresql, mysql, sqlite

# Статистические настройки
SIGNIFICANCE_LEVEL = float(os.getenv("SIGNIFICANCE_LEVEL", "0.05"))  # alpha
MIN_SAMPLE_SIZE = int(os.getenv("MIN_SAMPLE_SIZE", "100"))

# Настройки Streamlit
PAGE_TITLE = "TwoSigma — Платформа A/B тестирования"
PAGE_LAYOUT = "wide"
