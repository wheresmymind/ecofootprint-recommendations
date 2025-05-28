# app/api/v1/schemas/recommendation.py
from pydantic import BaseModel, Field
from typing import List, Optional

# Modelo para la recomendación global (y potencialmente para un error genérico)
class FullRecommendation(BaseModel):
    category: str = Field(..., description="La categoría de la recomendación, ej: Transporte, General.")
    suggestion: str = Field(..., description="El texto de la recomendación, incluyendo una breve explicación.")

# Nuevo modelo para las sugerencias específicas por categoría (solo 'suggestion')
class CategorySpecificSuggestion(BaseModel):
    suggestion: str = Field(..., description="El texto de la recomendación específica para la categoría, incluyendo su explicación.")

class RecommendationsByCategory(BaseModel):
    transport: List[CategorySpecificSuggestion] = Field(..., description="Sugerencias para Transporte.")
    food: List[CategorySpecificSuggestion] = Field(..., description="Sugerencias para Alimentación.")
    energy: List[CategorySpecificSuggestion] = Field(..., description="Sugerencias para Consumo Energético.")
    waste: List[CategorySpecificSuggestion] = Field(..., description="Sugerencias para Generación de Residuos.")

class RecommendationOutputSchema(BaseModel):
    global_recommendation: FullRecommendation = Field(..., description="Una recomendación general de alto impacto.")
    category_recommendations: RecommendationsByCategory = Field(..., description="Dos sugerencias específicas para cada categoría principal.")
    notes: Optional[str] = None