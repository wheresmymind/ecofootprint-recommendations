# app/db/database.py
from typing import Optional
import psycopg # O import psycopg2
from psycopg.rows import dict_row # O from psycopg2.extras import RealDictCursor para psycopg2
from psycopg.conninfo import make_conninfo # Para psycopg
from app.core.config import settings
import logging
import json # Para convertir el payload de recomendaciones a JSON string para la BD
from app.api.v1.schemas.recommendation import CategorySpecificSuggestion, RecommendationOutputSchema # Asumiendo tu schema de salida
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
    calculation_date: date,
    recommendations: RecommendationOutputSchema # Usa el schema actualizado
) -> bool:
    """Inserta las recomendaciones (JSON completo y desglosado) para un usuario."""
    if not DATABASE_URL:
        logger.error("No se puede insertar en la BD: DATABASE_URL no está configurada.")
        return False

    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return False

        recommendations_json_str = recommendations.model_dump_json(indent=2)

        # Extraer las sugerencias individuales
        # La global_recommendation es del tipo FullRecommendation, así que tiene .suggestion
        global_suggestion = recommendations.global_recommendation.suggestion if recommendations.global_recommendation else None

        # Las recomendaciones por categoría ahora contienen objetos CategorySpecificSuggestion
        def get_specific_suggestion_or_none(sug_list: list[CategorySpecificSuggestion], index: int) -> Optional[str]:
            return sug_list[index].suggestion if len(sug_list) > index and sug_list[index] else None

        transport_sugs = recommendations.category_recommendations.transport
        transport_sug1 = get_specific_suggestion_or_none(transport_sugs, 0)
        transport_sug2 = get_specific_suggestion_or_none(transport_sugs, 1)

        food_sugs = recommendations.category_recommendations.food
        food_sug1 = get_specific_suggestion_or_none(food_sugs, 0)
        food_sug2 = get_specific_suggestion_or_none(food_sugs, 1)

        energy_sugs = recommendations.category_recommendations.energy
        energy_sug1 = get_specific_suggestion_or_none(energy_sugs, 0)
        energy_sug2 = get_specific_suggestion_or_none(energy_sugs, 1)

        waste_sugs = recommendations.category_recommendations.waste
        waste_sug1 = get_specific_suggestion_or_none(waste_sugs, 0)
        waste_sug2 = get_specific_suggestion_or_none(waste_sugs, 1)

        sql = """
            INSERT INTO user_recommendations (
                user_id,
                calculation_date,
                recommendations_payload,
                global_rec_suggestion,
                transport_rec1_suggestion,
                transport_rec2_suggestion,
                food_rec1_suggestion,
                food_rec2_suggestion,
                energy_rec1_suggestion,
                energy_rec2_suggestion,
                waste_rec1_suggestion,
                waste_rec2_suggestion
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        with conn.cursor() as cur:
            cur.execute(sql, (
                user_id,
                calculation_date,
                recommendations_json_str,
                global_suggestion,
                transport_sug1,
                transport_sug2,
                food_sug1,
                food_sug2,
                energy_sug1,
                energy_sug2,
                waste_sug1,
                waste_sug2
            ))
            conn.commit()
        logger.info(f"Recomendaciones (completo y desglosado) insertadas para el usuario {user_id} en la fecha {calculation_date}.")
        return True
    except Exception as e:
        logger.error(f"Error al insertar recomendaciones desglosadas en la base de datos para {user_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
            logger.info("Conexión a la base de datos cerrada.")


