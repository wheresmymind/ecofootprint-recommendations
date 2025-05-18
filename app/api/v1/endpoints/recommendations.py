# app/api/v1/endpoints/recommendations.py
from fastapi import APIRouter, HTTPException, status, Body
from app.api.v1.schemas.footprint import FootprintInputSchema
from app.api.v1.schemas.recommendation import (
    Recommendation,
    RecommendationsByCategory,
    RecommendationOutputSchema
)
from app.services.recommendation_service import get_recommendations_for_footprint
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/",
    response_model=RecommendationOutputSchema, # Ya está bien
    status_code=status.HTTP_200_OK,
    summary="Generate Structured Carbon Footprint Recommendations",
    description="Accepts user carbon footprint data and returns AI-generated recommendations (global and by category).",
)
async def create_recommendations(
    footprint_data: FootprintInputSchema = Body(...)
) -> RecommendationOutputSchema:
    logger.info("Received request to generate structured recommendations.")
    try:
        result = await get_recommendations_for_footprint(footprint_data)

        # Comprobar si hay un mensaje de error explícito en las notas o en la recomendación global
        if result.notes and "error" in result.notes.lower():
            logger.error(f"Recommendation service indicated an error via notes: {result.notes}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to generate recommendations: {result.notes}"
            )
        if result.global_recommendation and result.global_recommendation.category.lower() == "error":
            logger.error(f"Recommendation service returned an error via global recommendation: {result.global_recommendation.suggestion}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to generate recommendations: {result.global_recommendation.suggestion}"
            )

        logger.info("Successfully generated structured recommendations.")
        return result
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception("An unexpected error occurred during structured recommendation generation.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {str(e)}",
        )