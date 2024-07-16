FROM python:3.10-slim

WORKDIR /app

COPY . /app


# Instalar dependencias necesarias
RUN apt-get update \
    && apt-get install -y python3-dev  \
    && rm -rf /var/lib/apt/lists/*


# Actualizar pip e instalar dependencias del proyecto
RUN pip install --upgrade pip \
    && pip install -r requirements.txt python-multipart

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]