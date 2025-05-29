# app/core/http_client.py
import httpx
import logging
from app.api.v1.schemas.recommendation import RecommendationOutputSchema 

logger = logging.getLogger(__name__)

TARGET_SERVICE_URL = "https://fake-data-wvx9.onrender.com/enviar_calculos" # La URL del servicio destino

async def post_recommendations_to_external_service(recommendations_payload: RecommendationOutputSchema):
    """
    Envía el payload de recomendaciones a un servicio externo mediante una petición POST.
    """
    if not TARGET_SERVICE_URL:
        logger.warning("TARGET_SERVICE_URL no está configurada. No se enviará la petición externa.")
        return

    try:
        # Convertir el objeto Pydantic a un diccionario para enviarlo como JSON
        payload_dict = recommendations_payload.model_dump()

        async with httpx.AsyncClient(timeout=10.0) as client: # Timeout de 10 segundos
            logger.info(f"Enviando recomendaciones a {TARGET_SERVICE_URL}...")
            response = await client.post(TARGET_SERVICE_URL, json=payload_dict)
            response.raise_for_status()  # Lanza una excepción para códigos de error HTTP 
            logger.info(f"Recomendaciones enviadas exitosamente a {TARGET_SERVICE_URL}. Status: {response.status_code}")
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP al enviar recomendaciones a {TARGET_SERVICE_URL}: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e: # Errores de red, timeout, etc.
        logger.error(f"Error de red/petición al enviar recomendaciones a {TARGET_SERVICE_URL}: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado al enviar recomendaciones a {TARGET_SERVICE_URL}: {e}")
