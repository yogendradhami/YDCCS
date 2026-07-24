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

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "ydcleaning.wsgi:application", "--bind", "0.0.0.0:8000"]