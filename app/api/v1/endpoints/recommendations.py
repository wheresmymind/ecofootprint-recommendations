# app/api/v1/endpoints/recommendations.py
from fastapi import APIRouter, HTTPException, status, Body, Depends, Security # Añadido Depends y Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # Para manejar el esquema Bearer
from app.api.v1.schemas.footprint import FootprintInputSchema
from app.api.v1.schemas.recommendation import RecommendationOutputSchema # Asumo que este es tu schema actual
from app.services.recommendation_service import get_recommendations_for_footprint
import logging
import jwt 
from jose import jwt as jose_jwt 
from jose.exceptions import JWTError 

router = APIRouter()
logger = logging.getLogger(__name__)

oauth2_scheme = HTTPBearer(auto_error=True)


# Función simple para decodificar el token (SIN VALIDACIÓN DE FIRMA)
def decode_jwt_payload_insecure(token: str) -> dict | None:
    try:
        # Decodifica el token sin verificar la firma. Útil solo para extraer claims
        payload = jose_jwt.decode(
            token,
            key=None, 
            algorithms=["HS256", "RS256"], 
            options={
                "verify_signature": False,
                "verify_aud": False, 
                "verify_iat": False, 
                "verify_exp": False, 
                "verify_nbf": False, 
                "verify_iss": False, 
                "verify_sub": False, 
                "require_exp": False, 
                "require_iat": False,
                "require_nbf": False,
            }
        )
        return payload
    except jwt.ExpiredSignatureError: # De python-jwt
        logger.error("Token ha expirado (python-jwt).")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ha expirado")
    except jwt.InvalidTokenError as e: # De python-jwt
        logger.error(f"Token inválido (python-jwt): {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token inválido: {e}")
    except JWTError as e: # De python-jose
        logger.error(f"Error al decodificar token JWT con python-jose: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token inválido o malformado: {e}")
    except Exception as e:
        logger.error(f"Error inesperado al decodificar token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No se pudo procesar el token")



@router.post(
    "/",
    response_model=RecommendationOutputSchema, 
    status_code=status.HTTP_200_OK,
    summary="Generate Structured Carbon Footprint Recommendations & Save",
    description="Accepts user data, generates AI recommendations, saves them to DB, and returns them. Requires Bearer token.",
)
async def create_recommendations(
    footprint_data: FootprintInputSchema = Body(...),
    token_credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme)
) -> RecommendationOutputSchema:
    logger.info("Received request to generate and save structured recommendations.")

    # ... (lógica de obtención y decodificación del token) ...
    raw_token = token_credentials.credentials
    decoded_payload = decode_jwt_payload_insecure(raw_token)
    if not decoded_payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o no se pudo decodificar.")

    user_id_from_token = decoded_payload.get("sub") # o "user_id"
    if not user_id_from_token:
        logger.error("No se encontró 'sub' (user_id) en el payload del token.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Claim 'sub' (user_id) no encontrado en el token.")

    logger.info(f"Procesando recomendaciones para el usuario: {user_id_from_token}")

    try:
        # Pasar el user_id al servicio
        result = await get_recommendations_for_footprint(
            footprint_data=footprint_data,
            user_id_from_token=str(user_id_from_token)
        )

        # ... (lógica de manejo de errores devueltos por el servicio ) ...
        if result.notes and ("error" in result.notes.lower() or "fallo" in result.notes.lower()): # Ser más genérico
            logger.error(f"Recommendation service indicated an error via notes: {result.notes}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error al generar recomendaciones: {result.notes}"
            )
        if result.global_recommendation and result.global_recommendation.category.lower() == "error":
            logger.error(f"Recommendation service returned an error via global recommendation: {result.global_recommendation.suggestion}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error al generar recomendaciones: {result.global_recommendation.suggestion}"
            )


        logger.info("Successfully generated and processed structured recommendations.")
        return result
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception("An unexpected error occurred during recommendation generation/saving.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {str(e)}",
        )