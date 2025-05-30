# app/api/v1/endpoints/recommendations.py
from fastapi import APIRouter, HTTPException, status, Body, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.v1.schemas.footprint import FootprintInputSchema
from app.api.v1.schemas.recommendation import RecommendationOutputSchema
from app.services.recommendation_service import get_recommendations_for_footprint
import logging
import jwt 
from jose import jwt as jose_jwt
from jose.exceptions import JWTError
from typing import Optional # Importa Optional

router = APIRouter()
logger = logging.getLogger(__name__)

# Hacemos que el auto_error sea False para que no falle si no hay token
oauth2_scheme_optional = HTTPBearer(auto_error=False)


# Función simple para decodificar el token (SIN VALIDACIÓN DE FIRMA)
# (Esta función ya la tienes, la mantengo igual)
def decode_jwt_payload_insecure(token: str) -> dict | None:
    try:
        payload = jose_jwt.decode(
            token,
            key=None,
            algorithms=["HS256", "RS256"],
            options={
                "verify_signature": False, "verify_aud": False, "verify_iat": False,
                "verify_exp": False, "verify_nbf": False, "verify_iss": False,
                "verify_sub": False, "require_exp": False, "require_iat": False,
                "require_nbf": False,
            }
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token ha expirado (detectado por python-jwt, si se usara).")
        # No relanzar HTTPException aquí si el token es opcional, manejarlo en el endpoint
        return {"error": "token_expired"} # O alguna otra indicación
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token inválido (detectado por python-jwt, si se usara): {e}")
        return {"error": "invalid_token", "detail": str(e)}
    except JWTError as e:
        logger.warning(f"Error al decodificar token JWT con python-jose: {e}")
        return {"error": "jwt_decode_error", "detail": str(e)}
    except Exception as e:
        logger.error(f"Error inesperado al decodificar token: {e}")
        return {"error": "unexpected_decode_error", "detail": str(e)}


@router.post(
    "/",
    response_model=RecommendationOutputSchema,
    status_code=status.HTTP_200_OK,
    summary="Generate Structured Carbon Footprint Recommendations & Save (Optional Auth)",
    description="Accepts user data, generates AI recommendations. Token Bearer es opcional.",
)
async def create_recommendations(
    footprint_data: FootprintInputSchema = Body(...),
    token_credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme_optional)
) -> RecommendationOutputSchema:
    logger.info("Received request to generate structured recommendations (optional auth).")

    user_id_to_process: str = "No Login" # Valor por defecto

    if token_credentials and token_credentials.credentials:
        raw_token = token_credentials.credentials
        logger.info("Token Bearer encontrado, intentando decodificar.")
        decoded_payload = decode_jwt_payload_insecure(raw_token)

        if decoded_payload:
            if "error" in decoded_payload:

                logger.error(f"Error al procesar el token proporcionado: {decoded_payload.get('detail')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Token proporcionado inválido: {decoded_payload.get('detail', 'Error desconocido')}"
                )

            user_id_from_token = decoded_payload.get("sub") # o "user_id"
            if user_id_from_token:
                user_id_to_process = str(user_id_from_token)
                logger.info(f"Token decodificado. Procesando para el usuario: {user_id_to_process}")
            else:
                # Token presente pero sin 'sub', esto podría ser un error si se espera 'sub'
                logger.warning("Token presente pero sin claim 'sub' (user_id). Se procesará como 'No Login'.")
        else:

            logger.error("El token proporcionado no pudo ser decodificado (payload es None).")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El token proporcionado no pudo ser decodificado.")
    else:
        logger.info("No se proporcionó Token Bearer. Procesando como 'No Login'.")


    logger.info(f"ID de usuario final para el servicio: {user_id_to_process}")

    try:
        # Pasar el user_id al servicio
        result = await get_recommendations_for_footprint(
            footprint_data=footprint_data,
            user_id_from_token=user_id_to_process # Siempre pasamos el user_id_to_process
        )

        # (lógica de manejo de errores devueltos por el servicio - se mantiene igual)
        if result.notes and ("error" in result.notes.lower() or "fallo" in result.notes.lower()):
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