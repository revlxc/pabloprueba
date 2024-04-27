# de construcción: Instalar dependencias
# Usaremos esta etapa sólo para construir y guardar nuestras dependencias
# Esto ayudará a reducir el tamaño final de la imagen

# Usamos python:3.9-slim-buster como base para minimizar el tamaño de la imagen
# También incluimos git y curl para descargar paquetes externos si es necesario
FROM python:3.9-slim-buster AS builder

# Actualizar pip y configurar variables de entorno
ENV PYTHONUNBUFFERED True
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev git curl \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --user --upgrade pip

# Configuramos el directorio de trabajo y copiamos los requisitos
WORKDIR /app
COPY requirements*.txt .

# Instala las dependencias utilizando pip
RUN pip install --user -r requirements.txt

# Etapa de producción: Crear la imagen ligera
# En esta etapa, creamos una imagen ligera únicamente con las dependencias reales del código fuente

# Basamos nuestra imagen en python:3.9-alpine para reducir el tamaño
FROM python:3.9-alpine

# Agregamos el usuario 'nouser' previamente removido
RUN addgroup -S nonuser \
&& adduser -S -G nonuser nonuser \
&& addgroup -S nouser \
&& adduser -S -G nouser nouser

# Configuramos el directorio de trabajo y copiamos el código fuente
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Instalamos los módulos Python globales
RUN export PATH="/root/.local/bin:$PATH"

# Finalmente, corremos nuestro script de inicialización
CMD ["python", "app.py"]

# Para evitar conflictos de permisos, cambiamos a un usuario menos privilegiado
USER nouser
