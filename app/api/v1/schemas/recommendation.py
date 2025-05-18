# app/api/v1/schemas/recommendation.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Recommendation(BaseModel):
    category: str = Field(..., description="La categoría de la recomendación, ej: Transporte, General.")
    suggestion: str = Field(..., description="El texto de la recomendación, incluyendo una breve explicación.")

class RecommendationsByCategory(BaseModel):
    transport: List[Recommendation] = Field(..., description="Recomendaciones para Transporte.")
    food: List[Recommendation] = Field(..., description="Recomendaciones para Alimentación.")
    energy: List[Recommendation] = Field(..., description="Recomendaciones para Consumo Energético.")
    waste: List[Recommendation] = Field(..., description="Recomendaciones para Generación de Residuos.")

class RecommendationOutputSchema(BaseModel):
    global_recommendation: Recommendation = Field(..., description="Una recomendación general de alto impacto.")
    category_recommendations: RecommendationsByCategory = Field(..., description="Dos recomendaciones específicas para cada categoría principal.")
    notes: Optional[str] = None # Para cualquier nota adicional o mensaje de error del proceso.