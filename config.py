"""Configuración del sistema Tinka/Boliyapa."""
from pathlib import Path

# === BD (XAMPP por defecto) ===
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "database": "tinka_db",
    "user": "root",
    "password": "",
}

# Tabla con los resultados
TABLE_NAME = "resultados"

# === Snowflake ===
# Los valores se pueden sobreescribir utilizando ``streamlit.secrets["snowflake"]``
# cuando la aplicación se despliega dentro de Snowflake/Streamlit, o mediante
# variables de entorno en entornos locales. Los campos vacíos actúan como
# marcadores de posición.
SNOWFLAKE_CONFIG = {
    "account": "",
    "user": "",
    "password": "",
    "role": "",
    "warehouse": "",
    "database": "",
    "schema": "",
    # Campo opcional; si no se indica se utilizará ``SNOWFLAKE_TABLE``.
    "table": "",
}

# Nombre de la tabla principal en Snowflake.
SNOWFLAKE_TABLE = "RESULTADOS"

# === Carpetas ===
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Archivos de datos
CACHE_FILE = DATA_DIR / "cache_sorteos.json"
COMBOS_FILE = DATA_DIR / "combinaciones_generadas.json"

# Parámetros generales
TOTAL_NUMBERS = 45
COMBINATION_SIZE = 6

# Parámetros heurísticos
SUM_RANGE = (90, 180)
LAST_N_WINDOWS = [50, 100, 200]
