# app/db/database.py
import psycopg # O import psycopg2
from psycopg.rows import dict_row # O from psycopg2.extras import RealDictCursor para psycopg2
from psycopg.conninfo import make_conninfo # Para psycopg
from app.core.config import settings
import logging
import json # Para convertir el payload de recomendaciones a JSON string para la BD
from app.api.v1.schemas.recommendation import RecommendationOutputSchema # Asumiendo tu schema de salida
from datetime import date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Usar el formato de URL estándar si está disponible, sino construirlo
if settings.AWS_RDS_URL:
    DATABASE_URL = settings.AWS_RDS_URL
elif settings.DB_HOST and settings.DB_USER and settings.DB_PASSWORD and settings.DB_NAME:
    # Para psycopg (v3)
    DATABASE_URL = make_conninfo(
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME,
        port=settings.DB_PORT,
        sslmode=settings.DB_SSLMODE
    )
    # Para psycopg2, la DSN string se vería así:
    # DATABASE_URL = f"host='{settings.DB_HOST}' dbname='{settings.DB_NAME}' user='{settings.DB_USER}' password='{settings.DB_PASSWORD}' port='{settings.DB_PORT}' sslmode='{settings.DB_SSLMODE}'"
else:
    DATABASE_URL = None
    logger.error("DATABASE_URL no se pudo construir. Verifica la configuración en .env.")

if DATABASE_URL: 
    logger.info(f"DATABASE_URL construida como: {DATABASE_URL[:DATABASE_URL.find('password=')+9]}********...") # Oculta la contraseña en el log

def get_db_connection():
    if not DATABASE_URL:
        logger.error("Intento de conexión a BD fallido: DATABASE_URL no está configurada.")
        return None
    try:
        logger.info(f"Intentando conectar a la base de datos con DSN (parcial): {DATABASE_URL[:DATABASE_URL.find('password=')+9]}********...")
        # Puedes añadir un connect_timeout si psycopg lo soporta directamente en la DSN o como parámetro
        # Para psycopg3, el timeout se puede pasar en la DSN: ?connect_timeout=10
        # O como parámetro: psycopg.connect(DATABASE_URL, connect_timeout=10, row_factory=dict_row)
        # Un timeout corto (ej. 10 segundos) ayudará a diagnosticar si es un problema de red/accesibilidad.
        conn = psycopg.connect(DATABASE_URL, connect_timeout=10, row_factory=dict_row)
        logger.info("¡Conexión a la base de datos establecida exitosamente!")
        return conn
    except psycopg.OperationalError as e: # Captura errores específicos de conexión
        logger.error(f"Error OPERACIONAL al conectar a la base de datos: {e}")
        logger.error(f"Detalles del error: {e.pgcode} - {e.pgerror}")
        logger.error(f"DSN usada (parcial): {DATABASE_URL[:DATABASE_URL.find('password=')+9]}********...")
        return None
    except Exception as e:
        logger.error(f"Error GENERAL al conectar a la base de datos: {e}")
        return None

def insert_recommendations(
    user_id: str,
    calculation_date: date, # Usar el tipo date de datetime
    recommendations: RecommendationOutputSchema
) -> bool:
    """Inserta las recomendaciones para un usuario en la base de datos."""
    if not DATABASE_URL:
        logger.error("No se puede insertar en la BD: DATABASE_URL no está configurada.")
        return False

    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return False # No se pudo obtener la conexión

        # Convertir el objeto Pydantic de recomendaciones a un diccionario y luego a JSON string
        # Usamos .model_dump() para Pydantic v2, o .dict() para Pydantic v1
        recommendations_json_str = recommendations.model_dump_json(indent=2) # o json.dumps(recommendations.dict())

        sql = """
            INSERT INTO user_recommendations (user_id, calculation_date, recommendations_payload)
            VALUES (%s, %s, %s);
        """
        with conn.cursor() as cur:
            # Para psycopg (v3)
            cur.execute(sql, (user_id, calculation_date, recommendations_json_str))
            # Para psycopg2
            # cur.execute(sql, (user_id, calculation_date, recommendations_json_str))
            conn.commit() # Asegurarse de hacer commit de la transacción
        logger.info(f"Recomendaciones insertadas para el usuario {user_id} en la fecha {calculation_date}.")
        return True
    except Exception as e:
        logger.error(f"Error al insertar recomendaciones en la base de datos para {user_id}: {e}")
        if conn:
            conn.rollback() # Revertir en caso de error
        return False
    finally:
        if conn:
            conn.close()
            logger.info("Conexión a la base de datos cerrada.")