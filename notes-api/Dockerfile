# Imagen base sobre la que se construye
FROM python:3.12-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero solo los requirements para aprovechar el cache de capas
COPY requirements.txt .

# Instalamos dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de la app
COPY . .

# volumen de datos
VOLUME ["/app/data"]


# Variable de entorno por ahora no tengo


# Comando que se ejecuta al levantar el contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]