# database.py

"""
Capa de abstracción para conexiones a base de datos.
Soporta SQLite (desarrollo) y PostgreSQL (producción).
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN DE RUTA Y BASE DE DATOS
# ==========================================

# Obtiene la ruta absoluta de la carpeta donde está este archivo (app/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define la ruta de la carpeta de datos (un nivel arriba, luego 'data')
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
# Asegura que la carpeta data exista
os.makedirs(DATA_DIR, exist_ok=True)

# Tipo de BD (sqlite o postgresql)
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

# Configuración según tipo de BD
if DB_TYPE == "postgresql":
    # PostgreSQL en producción
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "jagi_mahalo")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Engine con pool de conexiones
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verifica conexiones antes de usarlas
        echo=False  # Cambiar a True para debug SQL
    )
    
    logger.info(f"🐘 Conectado a PostgreSQL: {DB_HOST}:{DB_PORT}/{DB_NAME}")

else:
    # SQLite en desarrollo (modo actual)
    DB_NAME = "jagi_mahalo.db"
    DB_PATH = os.path.join(DATA_DIR, DB_NAME)
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    # Engine con configuración especial para SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    logger.info(f"📦 Conectado a SQLite: {DB_PATH}")

# ==========================================
# SESIONES Y BASE DECLARATIVA
# ==========================================

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_db():
    """
    Generador de sesiones para dependency injection en FastAPI.
    
    Uso en endpoints:
    @app.get("/")
    def endpoint(db: Session = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_connection():
    """
    Obtiene una conexión raw para pandas.read_sql().
    Compatible con SQLite y PostgreSQL.
    
    Uso:
    with get_connection() as conn:
        df = pd.read_sql(query, conn)
    """
    return engine.connect()


def test_connection():
    """
    Prueba la conexión a la base de datos.
    Retorna True si exitoso, False si falla.
    """
    try:
        with engine.connect() as conn:
            if DB_TYPE == "postgresql":
                result = conn.execute(text("SELECT version()"))
            else:
                result = conn.execute(text("SELECT sqlite_version()"))
            
            logger.info(f"✅ Conexión exitosa: {result.fetchone()[0]}")
            return True
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return False

def get_db_info():
    """
    Retorna información sobre la base de datos actual.
    """
    return {"type": DB_TYPE, "url": DATABASE_URL, "engine": str(engine)}

# ==========================================
# HELPERS PARA QUERIES COMPATIBLES
# ==========================================

def date_subtract_days(days: int) -> str:
    """
    Genera SQL compatible para restar días de la fecha actual.
    
    Args:
        days: Número de días a restar
    
    Returns:
        String SQL compatible con SQLite y PostgreSQL
    """
    if DB_TYPE == "postgresql":
        return f"CURRENT_DATE - INTERVAL '{days} days'"
    else:
        return f"DATE('now', '-{days} days')"


def date_format_convert(column: str, sqlite_format: str = "DD/MM/YYYY") -> str:
    """
    Convierte formato de fecha según el tipo de BD.
    
    Args:
        column: Nombre de la columna de fecha
        sqlite_format: Formato en SQLite (ej: "DD/MM/YYYY")
    
    Returns:
        String SQL para conversión de fecha
    """
    if DB_TYPE == "postgresql":
        # PostgreSQL usa TO_DATE
        pg_format = sqlite_format.replace("YYYY", "YYYY").replace("MM", "MM").replace("DD", "DD")
        return f"TO_DATE({column}, '{pg_format}')"
    else:
        # SQLite usa substr + concatenación
        if sqlite_format == "DD/MM/YYYY":
            return f"DATE(substr({column},7,4)||'-'||substr({column},4,2)||'-'||substr({column},1,2))"
        else:
            return f"DATE({column})"

def current_date() -> str:
    """
    Retorna SQL para fecha actual según BD.
    """
    if DB_TYPE == "postgresql":
        return "CURRENT_DATE"
    else:
        return "DATE('now')"


# ==========================================
# INICIALIZACIÓN
# ==========================================

# Probar conexión al importar el módulo
if __name__ != "__main__":
    test_connection()