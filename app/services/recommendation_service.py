# app/services/recommendation_service.py
from app.api.v1.schemas.footprint import FootprintInputSchema
from app.api.v1.schemas.recommendation import (
    Recommendation,
    RecommendationsByCategory,
    RecommendationOutputSchema
)
from app.core.gemini_client import generate_text_from_gemini
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

def _create_prompt(data: FootprintInputSchema) -> str:
    """
    Crea un prompt detallado para la API de Gemini, solicitando explicaciones
    dentro de las sugerencias. (Versión en Español)
    """

    # (contextual_summary 
    contextual_summary = f"""
Huella de Carbono Anual Estimada del Usuario: {data.result} toneladas CO2e/año.

Desglose de Datos de Hábitos (basado en la entrada del usuario):
- Transporte:
    - Viaje Semanal en Coche: {data.transport.carKm} km (de una escala de 0-500 km)
    - Transporte Público Semanal: {data.transport.publicKm} km (de una escala de 0-500 km)
    - Vuelos Nacionales Anuales: {data.transport.domesticFlights} vuelos (de 0-20 vuelos)
    - Vuelos Internacionales Anuales: {data.transport.internationalFlights} vuelos (de 0-10 vuelos) - *Nota: Los vuelos suelen tener un impacto de CO2 muy alto por evento.*
- Alimentación:
    - Consumo Semanal de Carne Roja: {data.food.redMeat} veces (de 0-14 veces) - *Nota: La carne roja generalmente tiene una alta huella de carbono.*
    - Consumo Semanal de Carne Blanca: {data.food.whiteMeat} veces (de 0-14 veces)
    - Consumo Semanal de Lácteos: {data.food.dairy} veces (de 0-21 veces)
    - Comidas Semanales Completamente Vegetarianas: {data.food.vegetarian} veces (de 0-21 veces)
- Consumo Energético:
    - Uso Diario de Electrodomésticos/Luces en Casa: {data.energy.applianceHours} horas (de 0-24 hrs)
    - Promedio de Bombillas Encendidas Simultáneamente: {data.energy.lightBulbs} bombillas (de 0-20 bombillas)
    - Uso Mensual de Gas Envasado (GLP): {data.energy.gasTanks} tanques/garrafas (de 0-5)
    - Uso Diario de Calefacción/Aire Acondicionado: {data.energy.hvacHours} horas (de 0-24 hrs)
- Generación de Residuos:
    - Bolsas Semanales de Basura General: {data.waste.trashBags} bolsas (de 0-10 bolsas)
    - Bolsas Semanales de Residuos de Comida (Orgánicos): {data.waste.foodWaste} bolsas (de 0-10 bolsas)
    - Botellas/Envases de Plástico Desechados Semanalmente: {data.waste.plasticBottles} unidades (de 0-50)
    - Paquetes de Papel/Cartón Desechados Semanalmente: {data.waste.paperPackages} unidades (de 0-10)
"""

    prompt = f"""
Eres un asesor ambiental experto que proporciona consejos personalizados y detallados para la reducción de la huella de carbono.
Analiza los datos de hábitos del usuario y su huella de carbono *anual total* calculada ({data.result} toneladas CO2e/año) que se presentan a continuación.

Datos de Hábitos del Usuario y Contexto:
{contextual_summary}

Tu Tarea:
Genera un conjunto estructurado de recomendaciones para ayudar al usuario a reducir significativamente su huella de carbono *anual*. Debes proporcionar:
1.  Una (1) recomendación general de alto impacto. Esta recomendación debe ser categorizada como "General".
2.  Dos (2) recomendaciones específicas para cada una de las siguientes categorías principales: "Transporte", "Alimentacion", "Energia" y "Residuos".

**Importante: Para CADA recomendación (tanto la general como las específicas de categoría), incluye una breve explicación dentro del mismo texto de la sugerencia sobre *por qué* esa acción es importante o *cómo* ayuda a reducir la huella (ej., mencionando el alto impacto del área abordada).**

Instrucciones de Salida Estricta (JSON):
1.  La salida debe ser un único objeto JSON.
2.  El objeto JSON raíz debe tener dos claves principales: "global_recommendation" y "category_recommendations".
3.  El valor de "global_recommendation" debe ser un objeto con dos claves:
    - "category": Siempre debe ser la cadena "General".
    - "suggestion": El texto de la recomendación general, incluyendo su explicación.
4.  El valor de "category_recommendations" debe ser un objeto con cuatro claves, una por cada categoría principal: "transport", "food", "energy", "waste".
5.  El valor de cada una de estas claves de categoría (ej., "transport") debe ser una *lista* que contenga exactamente *dos (2)* objetos de recomendación.
6.  Cada objeto de recomendación dentro de estas listas debe tener dos claves:
    - "category": El nombre de la categoría a la que pertenece (ej., "Transporte", "Alimentacion", etc.).
    - "suggestion": El texto de la recomendación específica para esa categoría, incluyendo su explicación.

Formato JSON de Ejemplo Esperado:
{{
  "global_recommendation": {{
    "category": "General",
    "suggestion": "Considera invertir en compensaciones de carbono de alta calidad para neutralizar las emisiones que no puedes evitar de inmediato, especialmente las de actividades como vuelos, ya que esto ayuda a financiar proyectos que reducen emisiones en otros lugares."
  }},
  "category_recommendations": {{
    "transport": [
      {{
        "category": "Transporte",
        "suggestion": "Si es posible, reemplaza uno de tus viajes semanales en coche por bicicleta o caminar para distancias cortas, ya que esto no solo reduce emisiones directas sino que también mejora tu salud."
      }},
      {{
        "category": "Transporte",
        "suggestion": "Al renovar tu vehículo, considera seriamente un coche eléctrico o híbrido enchufable, dado que los {data.transport.carKm} km semanales en coche representan una fuente significativa de emisiones continuas."
      }}
    ],
    "food": [
      {{
        "category": "Alimentacion",
        "suggestion": "Reduce tu consumo semanal de carne roja ({data.food.redMeat} veces) a la mitad, optando por más comidas vegetarianas ({data.food.vegetarian} veces) o pollo, porque la producción de carne roja tiene una huella hídrica y de carbono muy elevada."
      }},
      {{
        "category": "Alimentacion",
        "suggestion": "Planifica tus comidas y compras para minimizar el desperdicio de alimentos (actualmente {data.waste.foodWaste} bolsas semanales), ya que la comida descompuesta en vertederos produce metano, un potente gas de efecto invernadero."
      }}
    ],
    "energy": [
      // ... dos recomendaciones para 'energy' aquí ...
    ],
    "waste": [
      // ... dos recomendaciones para 'waste' aquí ...
    ]
  }}
}}

CRÍTICO: NO incluyas ningún texto introductorio, explicaciones fuera de las sugerencias, disculpas, comentarios finales ni formato markdown (como ```json) antes o después del objeto JSON. Tu salida completa debe ser ÚNICAMENTE la estructura JSON como se describe y ejemplifica.

Genera las recomendaciones ahora.
"""
    return prompt.strip()


def _parse_gemini_response_structured(response_text: str | None) -> RecommendationOutputSchema | None:
    if not response_text or response_text.startswith("Error") or response_text.startswith("Blocked"):
        logger.warning(f"Received invalid or error response from Gemini: {response_text}")
        # Devolver un objeto con un mensaje de error en 'notes'
        error_rec = Recommendation(category="Error", suggestion=response_text or "Failed to get recommendations from AI model.")
        # Crear una estructura vacía o con errores para las recomendaciones por categoría
        empty_cat_recs = RecommendationsByCategory(transport=[], food=[], energy=[], waste=[])
        return RecommendationOutputSchema(
            global_recommendation=error_rec,
            category_recommendations=empty_cat_recs,
            notes=response_text or "Failed to get recommendations from AI model."
        )

    try:
        cleaned_text = response_text.strip().removeprefix("```json").removesuffix("```").strip()
        data = json.loads(cleaned_text)

        # Validación básica de la estructura principal
        if not isinstance(data, dict) or "global_recommendation" not in data or "category_recommendations" not in data:
            logger.error(f"Gemini response missing main keys. Response: {cleaned_text}")
            raise ValueError("Main keys 'global_recommendation' or 'category_recommendations' missing in AI response.")

        # Parsear recomendación global
        global_rec_data = data.get("global_recommendation", {})
        if not isinstance(global_rec_data, dict) or "category" not in global_rec_data or "suggestion" not in global_rec_data:
            logger.error(f"Invalid global_recommendation structure: {global_rec_data}")
            raise ValueError("Invalid structure for 'global_recommendation'.")
        global_recommendation = Recommendation(
            category=str(global_rec_data.get("category", "General")), # Forzar 'General' si se omite
            suggestion=str(global_rec_data.get("suggestion", "No global suggestion provided."))
        )

        # Parsear recomendaciones por categoría
        cat_recs_data = data.get("category_recommendations", {})
        parsed_category_recs = {}
        categories_to_check = ["transport", "food", "energy", "waste"]

        for cat_key in categories_to_check:
            specific_recs_list = []
            cat_specific_data = cat_recs_data.get(cat_key, [])
            if isinstance(cat_specific_data, list):
                for item_data in cat_specific_data:
                    if isinstance(item_data, dict) and "category" in item_data and "suggestion" in item_data:
                        specific_recs_list.append(Recommendation(
                            category=str(item_data.get("category", cat_key.capitalize())), # Usar cat_key si se omite
                            suggestion=str(item_data.get("suggestion", "No suggestion provided."))
                        ))
                    else:
                        logger.warning(f"Skipping invalid item in '{cat_key}' recommendations: {item_data}")
            else:
                logger.warning(f"Expected a list for '{cat_key}' recommendations, got: {type(cat_specific_data)}")
            
            # Asegurar que siempre haya algo (incluso si está vacío o con errores)
            # if not specific_recs_list:
            #     specific_recs_list.append(Recommendation(category=cat_key.capitalize(), suggestion=f"No specific suggestions provided for {cat_key}."))
            parsed_category_recs[cat_key] = specific_recs_list


        category_recommendations_obj = RecommendationsByCategory(**parsed_category_recs)

        return RecommendationOutputSchema(
            global_recommendation=global_recommendation,
            category_recommendations=category_recommendations_obj
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini JSON response: {e}. Response text was: {response_text}")
        error_rec = Recommendation(category="Error", suggestion=f"AI response format error (JSONDecodeError). Raw response: {response_text[:200]}...")
        empty_cat_recs = RecommendationsByCategory(transport=[], food=[], energy=[], waste=[])
        return RecommendationOutputSchema(
            global_recommendation=error_rec,
            category_recommendations=empty_cat_recs,
            notes=f"AI response format error (JSONDecodeError). Raw response: {response_text[:200]}..."
        )
    except ValueError as e: # Para nuestros errores de validación de estructura
        logger.error(f"Structural validation error parsing Gemini response: {e}. Response text: {response_text}")
        error_rec = Recommendation(category="Error", suggestion=f"AI response structure error: {e}. Raw response: {response_text[:200]}...")
        empty_cat_recs = RecommendationsByCategory(transport=[], food=[], energy=[], waste=[])
        return RecommendationOutputSchema(
            global_recommendation=error_rec,
            category_recommendations=empty_cat_recs,
            notes=f"AI response structure error: {e}. Raw response: {response_text[:200]}..."
        )
    except Exception as e:
        logger.error(f"Unexpected error parsing Gemini response: {e}. Response text: {response_text}")
        error_rec = Recommendation(category="Error", suggestion=f"Unexpected error processing AI response: {e}")
        empty_cat_recs = RecommendationsByCategory(transport=[], food=[], energy=[], waste=[])
        return RecommendationOutputSchema(
            global_recommendation=error_rec,
            category_recommendations=empty_cat_recs,
            notes=f"Unexpected error processing AI response: {e}"
        )


async def get_recommendations_for_footprint(data: FootprintInputSchema) -> RecommendationOutputSchema:
    logger.info(f"Generating structured recommendations for footprint date: {data.date}, Annual Result: {data.result} tCO2e")
    prompt = _create_prompt(data)
    logger.debug(f"Generated Gemini Prompt (Structured Output Request):\n{prompt}")

    gemini_response_text = await generate_text_from_gemini(prompt)
    logger.debug(f"Received Gemini Response Text (Structured):\n{gemini_response_text}")

    parsed_output = _parse_gemini_response_structured(gemini_response_text)

    if parsed_output is None: # Debería ser manejado dentro de _parse_gemini_response_structured ahora
        logger.error("Parsing returned None, creating default error response.")
        error_rec = Recommendation(category="Error", suggestion="Internal error: Failed to parse AI response.")
        empty_cat_recs = RecommendationsByCategory(transport=[], food=[], energy=[], waste=[])
        return RecommendationOutputSchema(
            global_recommendation=error_rec,
            category_recommendations=empty_cat_recs,
            notes="Internal error: Failed to parse AI response."
        )
    
    # Si hay notas de error desde el parser, ya están en parsed_output.notes
    if parsed_output.notes:
         logger.warning(f"Notes from parsing: {parsed_output.notes}")
         # El endpoint manejará si esto se convierte en un error HTTP o no

    logger.info("Successfully parsed structured recommendations.")
    return parsed_output