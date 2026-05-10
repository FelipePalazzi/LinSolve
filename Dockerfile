# Dockerfile - LinSolve Backend
# Imagen Python para despliegue en Render/Railway/Container platforms

FROM python:3.11-slim

LABEL maintainer="LinSolve <dev@linsolve.app>"
LABEL description="Motor matemático de Programación Lineal con análisis Primal-Dual"

# Variables de entorno para producción
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=1

WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias con cache
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY backend/ ./backend/
COPY app/ ./app/

# Crear directorio para logs
RUN mkdir -p /app/logs

# Exponer puerto de FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Comando de inicio con uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]