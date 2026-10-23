FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Build static assets into the image. collectstatic never touches the
# database, but production settings still need *some* DATABASE_URL to parse.
RUN DATABASE_URL=sqlite://:memory: SECRET_KEY=build-only \
    python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--log-file", "-"]
