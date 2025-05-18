# Dockerfile

# 1. Usar una imagen base oficial de Python.
# Escoge una versión específica de Python que estés usando (ej. 3.11-slim)
# Las imágenes "-slim" son más pequeñas.
FROM python:3.11-slim AS builder

# 2. Establecer el directorio de trabajo dentro del contenedor.
WORKDIR /app

# 3. Copiar el archivo de requerimientos primero para aprovechar el cache de Docker.
COPY requirements.txt .

# 4. Instalar las dependencias.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar las dependencias instaladas desde la etapa de 'builder'
COPY --from=builder /install /usr/local

# Copiar el resto del código de la aplicación al directorio de trabajo.
COPY ./app /app/app

# 5. Exponer el puerto en el que FastAPI (Uvicorn) se ejecutará.
EXPOSE 8000

# 6. Comando para ejecutar la aplicación cuando el contenedor inicie.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]