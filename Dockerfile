FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/

ENV DJANGO_SETTINGS_MODULE=ydcleaning.settings

RUN CLOUDINARY_CLOUD_NAME=build-placeholder \
    CLOUDINARY_API_KEY=build-placeholder \
    CLOUDINARY_API_SECRET=build-placeholder \
    python manage.py collectstatic --noinput

# Keep startup focused on binding the web port. Configure
# `python manage.py migrate --noinput` as Render's pre-deploy command on a
# paid web service before deploying schema changes.
CMD ["sh", "-c", "exec daphne -b 0.0.0.0 -p ${PORT:-8000} ydcleaning.asgi:application"]
