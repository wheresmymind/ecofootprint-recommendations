# app/services/recommendation_service.py
from app.api.v1.schemas.footprint import FootprintInputSchema
from app.core.gemini_client import generate_text_from_gemini
from typing import List
from app.api.v1.schemas.recommendation import FullRecommendation, CategorySpecificSuggestion, RecommendationsByCategory, RecommendationOutputSchema
from app.db.database import insert_recommendations
from datetime import date, datetime
import json
import logging

logger = logging.getLogger(__name__)

def _create_prompt(data: FootprintInputSchema) -> str:
    """
    Crea un prompt detallado para la API de Gemini, solicitando una recomendación global
    y dos sugerencias por categoría (solo con 'suggestion'), con explicaciones. (Versión en Español)
    """

    # (contextual_summary se mantiene igual que en la versión anterior en español)
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
1.  Una (1) recomendación general de alto impacto.
2.  Dos (2) sugerencias específicas para cada una de las siguientes categorías principales: "Transporte", "Alimentacion", "Energia" y "Residuos".

**Importante: Para CADA recomendación/sugerencia (tanto la general como las específicas de categoría), incluye una breve explicación dentro del mismo texto sobre *por qué* esa acción es importante o *cómo* ayuda a reducir la huella.**

Instrucciones de Salida Estricta (JSON):
1.  La salida debe ser un único objeto JSON.
2.  El objeto JSON raíz debe tener dos claves principales: "global_recommendation" y "category_recommendations".
3.  El valor de "global_recommendation" debe ser un objeto con dos claves:
    - "category": Siempre debe ser la cadena "General".
    - "suggestion": El texto de la recomendación general, incluyendo su explicación.
4.  El valor de "category_recommendations" debe ser un objeto con cuatro claves, una por cada categoría principal: "transport", "food", "energy", "waste".
5.  El valor de cada una de estas claves de categoría (ej., "transport") debe ser una *lista* que contenga exactamente *dos (2)* objetos.
6.  Cada objeto dentro de estas listas (bajo "transport", "food", "energy", "waste") debe tener *SOLAMENTE UNA CLAVE*:
    - "suggestion": El texto de la sugerencia específica para esa categoría, incluyendo su explicación. (NO incluir la clave "category" aquí).

Formato JSON de Ejemplo Esperado:
{{
  "global_recommendation": {{
    "category": "General",
    "suggestion": "Considera invertir en compensaciones de carbono de alta calidad para neutralizar las emisiones que no puedes evitar de inmediato, especialmente las de actividades como vuelos, ya que esto ayuda a financiar proyectos que reducen emisiones en otros lugares."
  }},
  "category_recommendations": {{
    "transport": [
      {{
        "suggestion": "Si es posible, reemplaza uno de tus viajes semanales en coche por bicicleta o caminar para distancias cortas, ya que esto no solo reduce emisiones directas sino que también mejora tu salud."
      }},
      {{
        "suggestion": "Al renovar tu vehículo, considera seriamente un coche eléctrico o híbrido enchufable, dado que los {data.transport.carKm} km semanales en coche representan una fuente significativa de emisiones continuas."
      }}
    ],
    "food": [
      {{
        "suggestion": "Reduce tu consumo semanal de carne roja ({data.food.redMeat} veces) a la mitad, optando por más comidas vegetarianas ({data.food.vegetarian} veces) o pollo, porque la producción de carne roja tiene una huella hídrica y de carbono muy elevada."
      }},
      {{
        "suggestion": "Planifica tus comidas y compras para minimizar el desperdicio de alimentos (actualmente {data.waste.foodWaste} bolsas semanales), ya que la comida descompuesta en vertederos produce metano, un potente gas de efecto invernadero."
      }}
    ],
    "energy": [
      {{ "suggestion": "Sugerencia de energía 1 con explicación." }},
      {{ "suggestion": "Sugerencia de energía 2 con explicación." }}
    ],
    "waste": [
      {{ "suggestion": "Sugerencia de residuos 1 con explicación." }},
      {{ "suggestion": "Sugerencia de residuos 2 con explicación." }}
    ]
  }}
}}

CRÍTICO: NO incluyas ningún texto introductorio, explicaciones fuera de las sugerencias, disculpas, comentarios finales ni formato markdown (como ```json) antes o después del objeto JSON. Tu salida completa debe ser ÚNICAMENTE la estructura JSON como se describe y ejemplifica.

Genera las recomendaciones ahora.
"""
    return prompt.strip()


def _parse_gemini_response_structured(response_text: str | None) -> RecommendationOutputSchema | None:
    # Manejo de error inicial (si la respuesta de Gemini es vacía o un error conocido)
    if not response_text or response_text.startswith("Error") or response_text.startswith("Blocked"):
        logger.warning(f"Received invalid or error response from Gemini: {response_text}")
        error_global_rec = FullRecommendation(category="Error", suggestion=response_text or "Failed to get recommendations from AI model.")
        empty_cat_recs_data = {
            "transport": [], "food": [], "energy": [], "waste": []
        }
        # Rellenar con sugerencias de error si se desea, o dejarlas vacías.
        for cat in empty_cat_recs_data:
            empty_cat_recs_data[cat] = [
                CategorySpecificSuggestion(suggestion="No specific suggestion due to previous error."),
                CategorySpecificSuggestion(suggestion="No specific suggestion due to previous error.")
            ]

        empty_cat_recs = RecommendationsByCategory(**empty_cat_recs_data)
        return RecommendationOutputSchema(
            global_recommendation=error_global_rec,
            category_recommendations=empty_cat_recs,
            notes=response_text or "Failed to get recommendations from AI model."
        )

    try:
        cleaned_text = response_text.strip().removeprefix("```json").removesuffix("```").strip()
        data = json.loads(cleaned_text)

        # Validación de la estructura principal
        if not isinstance(data, dict) or "global_recommendation" not in data or "category_recommendations" not in data:
            logger.error(f"Gemini response missing main keys. Response: {cleaned_text}")
            raise ValueError("Main keys 'global_recommendation' or 'category_recommendations' missing in AI response.")

        # Parsear recomendación global
        global_rec_data = data.get("global_recommendation", {})
        if not isinstance(global_rec_data, dict) or "category" not in global_rec_data or "suggestion" not in global_rec_data:
            logger.error(f"Invalid global_recommendation structure: {global_rec_data}")
            raise ValueError("Invalid structure for 'global_recommendation'.")
        global_recommendation = FullRecommendation(
            category=str(global_rec_data.get("category", "General")),
            suggestion=str(global_rec_data.get("suggestion", "No global suggestion provided."))
        )

        # Parsear recomendaciones por categoría (ahora solo con 'suggestion')
        cat_recs_data = data.get("category_recommendations", {})
        parsed_category_suggestions = {}
        categories_to_check = ["transport", "food", "energy", "waste"]

        for cat_key in categories_to_check:
            specific_suggestions_list = []
            cat_specific_item_list = cat_recs_data.get(cat_key, []) # Lista de objetos {suggestion: "..."}
            if isinstance(cat_specific_item_list, list):
                for item_data in cat_specific_item_list:
                    # Ahora esperamos solo la clave 'suggestion'
                    if isinstance(item_data, dict) and "suggestion" in item_data:
                        specific_suggestions_list.append(CategorySpecificSuggestion(
                            suggestion=str(item_data.get("suggestion", "No suggestion provided."))
                        ))
                    else:
                        logger.warning(f"Skipping invalid item in '{cat_key}' suggestions (expected {{'suggestion': ...}}): {item_data}")
            else:
                logger.warning(f"Expected a list for '{cat_key}' recommendations, got: {type(cat_specific_item_list)}")
            
            # Rellenar si no hay suficientes sugerencias para cumplir con el "exactamente dos"
            # Esto es importante si Gemini no sigue las instrucciones al pie de la letra.
            while len(specific_suggestions_list) < 2:
                logger.warning(f"Not enough suggestions for '{cat_key}', padding with default.")
                specific_suggestions_list.append(CategorySpecificSuggestion(suggestion=f"No specific suggestion provided by AI for {cat_key} (slot {len(specific_suggestions_list)+1})."))
            
            # Truncar si hay demasiadas (aunque el prompt pide 2)
            parsed_category_suggestions[cat_key] = specific_suggestions_list[:2]


        category_recommendations_obj = RecommendationsByCategory(**parsed_category_suggestions)

        return RecommendationOutputSchema(
            global_recommendation=global_recommendation,
            category_recommendations=category_recommendations_obj
        )

    # Bloques catch para errores (JSONDecodeError, ValueError, Exception general)
    # Son similares a los de la respuesta anterior, pero asegúrate de que construyen
    # el RecommendationOutputSchema con el nuevo FullRecommendation y CategorySpecificSuggestion.
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini JSON response: {e}. Response text was: {response_text}")
        error_global_rec = FullRecommendation(category="Error", suggestion=f"AI response format error (JSONDecodeError).")
        notes = f"AI response format error (JSONDecodeError). Raw: {response_text[:200]}..."
        # Crear una estructura de error para category_recommendations
        error_cat_recs_data = {cat: [CategorySpecificSuggestion(suggestion="Error parsing data.")]*2 for cat in categories_to_check}
        error_cat_recs = RecommendationsByCategory(**error_cat_recs_data)
        return RecommendationOutputSchema(global_recommendation=error_global_rec, category_recommendations=error_cat_recs, notes=notes)

    except ValueError as e: # Para nuestros errores de validación de estructura
        logger.error(f"Structural validation error parsing Gemini response: {e}. Response text: {response_text}")
        error_global_rec = FullRecommendation(category="Error", suggestion=f"AI response structure error: {e}.")
        notes = f"AI response structure error: {e}. Raw: {response_text[:200]}..."
        error_cat_recs_data = {cat: [CategorySpecificSuggestion(suggestion="Error in data structure.")]*2 for cat in categories_to_check}
        error_cat_recs = RecommendationsByCategory(**error_cat_recs_data)
        return RecommendationOutputSchema(global_recommendation=error_global_rec, category_recommendations=error_cat_recs, notes=notes)

    except Exception as e:
        logger.error(f"Unexpected error parsing Gemini response: {e}. Response text: {response_text}")
        error_global_rec = FullRecommendation(category="Error", suggestion=f"Unexpected error processing AI response: {e}")
        notes = f"Unexpected error processing AI response: {e}"
        error_cat_recs_data = {cat: [CategorySpecificSuggestion(suggestion="Unexpected processing error.")]*2 for cat in categories_to_check}
        error_cat_recs = RecommendationsByCategory(**error_cat_recs_data)
        return RecommendationOutputSchema(global_recommendation=error_global_rec, category_recommendations=error_cat_recs, notes=notes)


async def get_recommendations_for_footprint(
    footprint_data: FootprintInputSchema,
    user_id_from_token: str # Añadimos el user_id aquí
) -> RecommendationOutputSchema:
    logger.info(f"Generando recomendaciones estructuradas para el usuario: {user_id_from_token}, fecha de huella: {footprint_data.date}")
    prompt = _create_prompt(footprint_data) # Asumiendo que _create_prompt toma FootprintInputSchema
    # ... (resto de la lógica de Gemini) ...

    gemini_response_text = await generate_text_from_gemini(prompt)
    parsed_output = _parse_gemini_response_structured(gemini_response_text) # Asumiendo que esta función ya está adaptada

    if parsed_output is None:
        logger.error("El parseo de la respuesta de Gemini devolvió None, creando respuesta de error por defecto.")
        # Definir una estructura de error para RecommendationOutputSchema
        error_global_rec = FullRecommendation(category="Error", suggestion="Error interno: Fallo al parsear la respuesta de la IA.")
        error_cat_recs_data = {cat: [CategorySpecificSuggestion(suggestion="Error interno al parsear.")]*2 for cat in ["transport", "food", "energy", "waste"]}
        error_cat_recs = RecommendationsByCategory(**error_cat_recs_data)
        parsed_output = RecommendationOutputSchema(
            global_recommendation=error_global_rec,
            category_recommendations=error_cat_recs,
            notes="Error interno: Fallo al parsear la respuesta de la IA."
        )
        # No intentar guardar en BD si el parseo falló críticamente
        return parsed_output

    # Intentar guardar en la base de datos ANTES de devolver la respuesta al usuario,
    # o después, dependiendo de si la escritura en BD es crítica para el flujo.
    # Por ahora, lo haremos antes.

    # Convertir la fecha string del input a un objeto date de Python
    try:
        calculation_dt_obj = datetime.strptime(footprint_data.date, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Formato de fecha inválido: {footprint_data.date}. No se guardará en BD.")
        # Decidir si añadir una nota al parsed_output o simplemente no guardar
        if parsed_output: # Asegurarse que parsed_output no es None
            parsed_output.notes = (parsed_output.notes + " | " if parsed_output.notes else "") + "Advertencia: Fecha de cálculo inválida, no se guardaron las recomendaciones."
        return parsed_output # Devolver sin intentar guardar

    # Solo intentar guardar si no hubo un error crítico en el parseo
    # (por ejemplo, si la categoría de la recomendación global no es "Error")
    save_to_db_successful = False
    if not (parsed_output.global_recommendation and parsed_output.global_recommendation.category.lower() == "error"):
        logger.info(f"Intentando guardar recomendaciones para el usuario {user_id_from_token} en la base de datos.")
        save_to_db_successful = insert_recommendations(
            user_id=user_id_from_token,
            calculation_date=calculation_dt_obj,
            recommendations=parsed_output # Pasamos el objeto Pydantic completo
        )
        if not save_to_db_successful:
            logger.warning(f"No se pudieron guardar las recomendaciones en la BD para el usuario {user_id_from_token}. La respuesta aún se enviará al usuario.")
            # Opcional: Añadir una nota al usuario
            if parsed_output: # Asegurarse que parsed_output no es None
                 parsed_output.notes = (parsed_output.notes + " | " if parsed_output.notes else "") + "Advertencia: No se pudieron guardar estas recomendaciones para su historial."
    else:
        logger.info("No se intentó guardar en BD debido a un error previo en la generación de recomendaciones.")


    if parsed_output.notes:
         logger.warning(f"Notas del proceso de recomendación: {parsed_output.notes}")

    logger.info("Recomendaciones generadas exitosamente (y guardadas en BD si fue posible).")
    return parsed_output