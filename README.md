# EcoFootprint: API de Recomendaciones de Huella de Carbono

Este proyecto es una API backend desarrollada con FastAPI (Python) que tiene como objetivo generar recomendaciones personalizadas para ayudar a los usuarios a reducir su huella de carbono. Utiliza la API de Google Gemini para generar dichas recomendaciones basándose en los datos de hábitos del usuario.

## Características Principales

*   **Cálculo y Contextualización:** Recibe datos detallados sobre los hábitos del usuario en áreas como transporte, alimentación, consumo energético y generación de residuos.
*   **Generación de Recomendaciones con IA:** Utiliza la API de Google Gemini para analizar los datos del usuario y generar de 3 a 5 recomendaciones prácticas y personalizadas.
*   **Explicaciones Detalladas:** Las recomendaciones incluyen una breve explicación de por qué son importantes o cómo ayudan a reducir el impacto ambiental.
*   **API RESTful:** Expone un endpoint `/api/v1/recommendations/` para recibir los datos del usuario (JSON) y devolver las recomendaciones (JSON).
*   **Documentación Interactiva:** Documentación automática de la API (Swagger UI y ReDoc) disponible al iniciar la aplicación.
*   **Dockerizado:** Incluye `Dockerfile` y `docker-compose.yml` para facilitar la ejecución y el despliegue en cualquier entorno.

## Estructura del Proyecto

```
ecofootprint-recommendations/
├── app/                     # Código fuente principal de la aplicación
│   ├── api/                 # Módulos relacionados con la API (endpoints, schemas)
│   ├── core/                # Lógica central (configuración, cliente Gemini)
│   ├── services/            # Lógica de negocio (servicio de recomendaciones)
│   └── main.py              # Instancia de la aplicación FastAPI
├── .env.example             # Ejemplo de archivo de variables de entorno (¡copiar a .env!)
├── .dockerignore            # Especifica archivos a ignorar por Docker
├── .gitignore               # Especifica archivos a ignorar por Git
├── Dockerfile               # Instrucciones para construir la imagen Docker
├── docker-compose.yml       # Define y ejecuta la aplicación con Docker Compose
├── requirements.txt         # Dependencias de Python
└── README.md                # Este archivo
```

## Prerrequisitos

### Para ejecución Nativa (Python):

*   Python 3.9 o superior.
*   `pip` (gestor de paquetes de Python).
*   Una clave API de Google Gemini (obtenida desde [Google AI Studio](https://aistudio.google.com/) o Google Cloud Console).

### Para ejecución con Docker:

*   Docker instalado.
*   Docker Compose instalado (recomendado).
*   Una clave API de Google Gemini.

## Configuración

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd ecofootprint-recommendations
    ```

2.  **Configurar la Clave API de Gemini:**
    Crea un archivo llamado `.env` en la raíz del proyecto. Puedes copiar el contenido de `.env.example` (si existe) y luego modificarlo, o crearlo directamente:
    ```ini
    # .env
    GEMINI_API_KEY=TU_CLAVE_API_DE_GEMINI_AQUI
    ```
    Reemplaza `TU_CLAVE_API_DE_GEMINI_AQUI` con tu clave API real. **Este archivo `.env` no debe ser subido al repositorio Git si es público.**

## Ejecución

Tienes dos formas de ejecutar la aplicación:

### Opción 1: Ejecución Nativa (Python)

1.  **Crear y activar un entorno virtual (recomendado):**
    ```bash
    python -m venv venv
    # En Windows:
    # .\venv\Scripts\activate
    # En macOS/Linux:
    # source venv/bin/activate
    ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar la aplicación FastAPI con Uvicorn:**
    ```bash
    uvicorn app.main:app --reload
    ```
    La opción `--reload` es útil para desarrollo, ya que reinicia el servidor automáticamente cuando detecta cambios en el código.

4.  **Acceder a la API:**
    *   La API estará disponible en `http://127.0.0.1:8000`.
    *   La documentación interactiva (Swagger UI) estará en `http://127.0.0.1:8000/docs`.
    *   La documentación alternativa (ReDoc) estará en `http://127.0.0.1:8000/redoc`.

### Opción 2: Ejecución con Docker y Docker Compose (Recomendado para facilidad y portabilidad)

1.  **Asegúrate de tener Docker y Docker Compose instalados.**
2.  **Verifica que el archivo `.env` (creado en el paso de Configuración) esté presente en la raíz del proyecto con tu `GEMINI_API_KEY`.**

3.  **Construir la imagen y ejecutar el contenedor:**
    Desde la raíz del proyecto, ejecuta:
    ```bash
    docker-compose up --build
    ```
    *   `--build`: Fuerza la reconstrucción de la imagen si es necesario.
    *   Para ejecutar en segundo plano (detached mode), usa `docker-compose up -d --build`. Si lo haces, para ver los logs usa `docker-compose logs -f web` (asumiendo que el servicio se llama `web` en `docker-compose.yml`).

4.  **Acceder a la API:**
    *   La API estará disponible en `http://localhost:8000` (nota: no `127.0.0.1` necesariamente, aunque suele funcionar igual).
    *   La documentación interactiva (Swagger UI) estará en `http://localhost:8000/docs`.
    *   La documentación alternativa (ReDoc) estará en `http://localhost:8000/redoc`.

5.  **Detener los contenedores (si usaste Docker Compose):**
    Si ejecutaste `docker-compose up` en primer plano, presiona `Ctrl+C` en la terminal.
    Si usaste `docker-compose up -d`, ejecuta:
    ```bash
    docker-compose down
    ```
    Esto detendrá y eliminará los contenedores definidos.

## Uso de la API

Para generar recomendaciones, envía una petición `POST` al endpoint `/api/v1/recommendations/` con un cuerpo JSON que contenga los datos de la huella de carbono del usuario.

**Ejemplo de cuerpo de la petición (Request Body):**
```json
{
  "date": "2025-04-29",
  "energy": {
    "applianceHours": 120,
    "lightBulbs": 80,
    "gasTanks": 10,
    "hvacHours": 10
  },
  "food": {
    "redMeat": 50,
    "whiteMeat": 30,
    "dairy": 20,
    "vegetarian": 5
  },
  "transport": {
    "carKm": 100,
    "publicKm": 200,
    "domesticFlights": 5,
    "internationalFlights": 10
  },
  "waste": {
    "trashBags": 15,
    "foodWaste": 10,
    "plasticBottles": 25,
    "paperPackages": 40
  },
  "result": 25.25
}
```

**Ejemplo de respuesta esperada (Response Body):**
```json
{
  "recommendations": [
    {
      "category": "Transporte",
      "suggestion": "Considera reducir tus vuelos internacionales anuales. Cada vuelo de larga distancia tiene una huella de carbono muy significativa debido al combustible quemado a gran altitud."
    },
    {
      "category": "Alimentacion",
      "suggestion": "Intenta disminuir el consumo de carne roja a la mitad. La producción de carne roja es intensiva en recursos y genera muchas más emisiones que otras proteínas como el pollo o las legumbres."
    },
    // ... más recomendaciones
  ],
  "notes": null
}
```

Puedes usar herramientas como Postman, `curl`, o la interfaz de Swagger UI (`/docs`) para probar el endpoint.
